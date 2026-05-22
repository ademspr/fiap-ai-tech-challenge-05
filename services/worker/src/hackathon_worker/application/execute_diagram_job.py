import hashlib
from uuid import UUID

import structlog
from hackathon_contracts import AnalyzeDiagramJobV1, JobCompletionV1, JobPatchV1

from hackathon_worker.application.ai_analyzer import run_real_analysis
from hackathon_worker.application.ports import (
    WorkerInternalApiPort,
    WorkerObjectStoragePort,
    WorkerPipelineMetricsPort,
)
from hackathon_worker.config import settings
from hackathon_worker.domain.exceptions import MissingDiagramPathError, StateMachineError
from hackathon_worker.domain.fsm import JobStateMachine, WorkerJobPhase

log = structlog.get_logger(__name__)


async def execute_diagram_job(
    body: bytes,
    api: WorkerInternalApiPort,
    pipeline_metrics: WorkerPipelineMetricsPort,
    storage: WorkerObjectStoragePort,
) -> None:
    job_id: UUID | None = None
    job_state_machine: JobStateMachine | None = None

    try:
        diagram_message = AnalyzeDiagramJobV1.model_validate_json(body.decode("utf-8"))
        job_id = UUID(diagram_message.job_id)
        job_state_machine = JobStateMachine()

        log.info("job_received", job_id=str(job_id))

        job_state_machine.start_processing()
        pipeline_metrics.record_state_transition(WorkerJobPhase.PROCESSING.value)

        await api.patch_job(job_id, JobPatchV1(status="PROCESSING"))

        if not diagram_message.diagram_storage_path:
            raise MissingDiagramPathError

        diagram_bytes = storage.read_diagram_bytes(diagram_message.diagram_storage_path)
        report, tokens_used = run_real_analysis(
            diagram_bytes,
            diagram_message.content_type,
            base_url=settings.ai_base_url,
            model=settings.ai_model,
            api_key=settings.ai_api_key,
            timeout=6000000,
            max_retries=settings.ai_max_retries,
        )

        report_relative_name = f"{job_id}.json"

        raw = report.model_dump_json().encode("utf-8")
        storage.write_report_bytes(report_relative_name, raw)
        digest = hashlib.sha256(raw).hexdigest()

        await api.complete_job(
            job_id,
            JobCompletionV1(
                report_storage_path=report_relative_name,
                tokens_used=tokens_used,
                report_checksum=digest,
                report_schema_version=1,
            ),
        )

        job_state_machine.complete()
        pipeline_metrics.record_state_transition(WorkerJobPhase.COMPLETED.value)
        pipeline_metrics.record_diagram_processed("success")
        log.info("job_completed", job_id=str(job_id), tokens_used=tokens_used)

    except Exception as error:  # noqa: BLE001
        log.exception(
            "job_failed",
            job_id=str(job_id) if job_id is not None else None,
            error=str(error),
        )

        if job_state_machine is not None:
            try:
                job_state_machine.fail()
            except StateMachineError:
                pass

        pipeline_metrics.record_state_transition(WorkerJobPhase.FAILED.value)
        pipeline_metrics.record_diagram_processed("error")

        if job_id is not None:
            try:
                await api.patch_job(
                    job_id, JobPatchV1(status="ERROR", error_message=str(error)[:2000])
                )
            except Exception as patch_error:  # noqa: BLE001
                log.exception("patch_error_failed", error=str(patch_error))
        raise
