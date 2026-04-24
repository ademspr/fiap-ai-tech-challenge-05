from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from hackathon_contracts import JobCompletionV1, JobPatchV1

from hackathon_api.application.jobs import (
    get_job_by_id,
    internal_apply_job_patch,
    internal_complete_job,
)
from hackathon_api.application.persistence import UnitOfWork
from hackathon_api.application.ports import JobMetricsPort
from hackathon_api.domain.enums import JobStatus
from hackathon_api.domain.exceptions import InsufficientTokensError
from hackathon_api.presentation.deps import (
    get_job_metrics,
    get_job_persistence,
    verify_internal_token,
)

router = APIRouter(tags=["internal"], dependencies=[Depends(verify_internal_token)])


@router.patch("/analysis-jobs/{job_id}")
async def patch_analysis_job(
    job_id: UUID,
    body: JobPatchV1,
    job_persistence: Annotated[UnitOfWork, Depends(get_job_persistence)],
    job_metrics: Annotated[JobMetricsPort, Depends(get_job_metrics)],
):
    job = await get_job_by_id(job_persistence, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    if body.status not in (JobStatus.PROCESSING.value, JobStatus.ERROR.value):
        raise HTTPException(400, "Invalid status for patch")

    await internal_apply_job_patch(
        job_persistence,
        job_id,
        status=body.status,
        error_message=body.error_message,
    )

    if body.status == JobStatus.PROCESSING.value:
        job_metrics.increment_status_label(JobStatus.PROCESSING.value)
    elif body.status == JobStatus.ERROR.value:
        job_metrics.increment_status_label(JobStatus.ERROR.value)

    await job_persistence.commit()

    return {"ok": True}


@router.post("/analysis-jobs/{job_id}/completion")
async def complete_analysis_job(
    job_id: UUID,
    body: JobCompletionV1,
    job_persistence: Annotated[UnitOfWork, Depends(get_job_persistence)],
    job_metrics: Annotated[JobMetricsPort, Depends(get_job_metrics)],
):
    job = await get_job_by_id(job_persistence, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    try:
        await internal_complete_job(
            job_persistence,
            job_id,
            report_storage_path=body.report_storage_path,
            tokens_used=body.tokens_used,
            report_checksum=body.report_checksum,
            report_schema_version=body.report_schema_version,
        )
        await job_persistence.commit()
    except InsufficientTokensError:
        await job_persistence.rollback()
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Insufficient token balance",
        )

    job_metrics.add_tokens_consumed(str(job.client_id), body.tokens_used)
    job_metrics.increment_status_label(JobStatus.ANALYZED.value)

    return {"ok": True}
