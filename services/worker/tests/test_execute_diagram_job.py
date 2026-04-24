import base64
from uuid import UUID, uuid4

import pytest
from hackathon_contracts import AnalyzeDiagramJobV1, JobCompletionV1, JobPatchV1

from hackathon_worker.application.execute_diagram_job import execute_diagram_job
from hackathon_worker.application.ports import WorkerInternalApiPort, WorkerPipelineMetricsPort
from hackathon_worker.config import settings
from hackathon_worker.domain.fsm import WorkerJobPhase

MINI_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class FakeInternalApi(WorkerInternalApiPort):
    def __init__(self) -> None:
        self.patches: list[tuple[UUID, JobPatchV1]] = []
        self.completions: list[tuple[UUID, JobCompletionV1]] = []

    async def patch_job(self, job_id: UUID, body: JobPatchV1) -> None:
        self.patches.append((job_id, body))

    async def complete_job(self, job_id: UUID, body: JobCompletionV1) -> None:
        self.completions.append((job_id, body))


class FakePipelineMetrics(WorkerPipelineMetricsPort):
    def __init__(self) -> None:
        self.transitions: list[str] = []
        self.processed: list[str] = []

    def record_state_transition(self, to_phase: str) -> None:
        self.transitions.append(to_phase)

    def record_diagram_processed(self, outcome: str) -> None:
        self.processed.append(outcome)


@pytest.mark.asyncio
async def test_execute_diagram_job_success(monkeypatch, tmp_path):
    uploads = tmp_path / "uploads"
    reports = tmp_path / "reports"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    job_id = uuid4()
    rel = "in/diagram.png"
    diagram_file = uploads / rel
    diagram_file.parent.mkdir(parents=True, exist_ok=True)
    diagram_file.write_bytes(MINI_PNG)

    body = AnalyzeDiagramJobV1(
        job_id=str(job_id),
        schema_version=1,
        diagram_storage_path=rel,
    ).model_dump_json()

    api = FakeInternalApi()
    metrics = FakePipelineMetrics()

    await execute_diagram_job(body.encode("utf-8"), api, metrics)

    assert len(api.completions) == 1
    assert api.completions[0][0] == job_id
    assert api.completions[0][1].tokens_used == 42

    assert len(api.patches) == 1
    assert api.patches[0][1].status == "PROCESSING"

    out = reports / f"{job_id}.json"
    assert out.is_file()

    assert WorkerJobPhase.PROCESSING.value in metrics.transitions
    assert WorkerJobPhase.COMPLETED.value in metrics.transitions
    assert metrics.processed == ["success"]


@pytest.mark.asyncio
async def test_execute_diagram_job_invalid_json_records_failure_without_patch(
    monkeypatch, tmp_path
):
    uploads = tmp_path / "u"
    reports = tmp_path / "r"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    api = FakeInternalApi()
    metrics = FakePipelineMetrics()

    await execute_diagram_job(b"not-json{", api, metrics)

    assert api.patches == []
    assert api.completions == []
    assert metrics.processed == ["error"]
    assert WorkerJobPhase.FAILED.value in metrics.transitions


@pytest.mark.asyncio
async def test_execute_diagram_job_missing_path_patches_error(monkeypatch, tmp_path):
    uploads = tmp_path / "u2"
    reports = tmp_path / "r2"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    job_id = uuid4()
    body = AnalyzeDiagramJobV1(
        job_id=str(job_id),
        schema_version=1,
        diagram_storage_path=None,
    ).model_dump_json()

    api = FakeInternalApi()
    metrics = FakePipelineMetrics()

    await execute_diagram_job(body.encode("utf-8"), api, metrics)

    assert len(api.patches) == 2
    assert api.patches[0][1].status == "PROCESSING"
    assert api.patches[1][1].status == "ERROR"
    assert api.completions == []
    assert metrics.processed == ["error"]


@pytest.mark.asyncio
async def test_execute_diagram_job_missing_file_patches_error(monkeypatch, tmp_path):
    uploads = tmp_path / "u3"
    reports = tmp_path / "r3"
    uploads.mkdir()
    reports.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "reports_dir", reports)

    job_id = uuid4()
    body = AnalyzeDiagramJobV1(
        job_id=str(job_id),
        schema_version=1,
        diagram_storage_path="nope/missing.png",
    ).model_dump_json()

    api = FakeInternalApi()
    metrics = FakePipelineMetrics()

    await execute_diagram_job(body.encode("utf-8"), api, metrics)

    assert len(api.patches) == 2
    assert api.patches[1][1].status == "ERROR"
    assert api.completions == []
