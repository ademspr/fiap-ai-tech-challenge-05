import base64
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from hackathon_contracts import AnalyzeDiagramJobV1, JobCompletionV1, JobPatchV1

from hackathon_worker.application.execute_diagram_job import execute_diagram_job
from hackathon_worker.application.ports import (
    WorkerInternalApiPort,
    WorkerObjectStoragePort,
    WorkerPipelineMetricsPort,
)
from hackathon_worker.domain.exceptions import MissingDiagramPathError
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


class FakeObjectStorage(WorkerObjectStoragePort):
    def __init__(self) -> None:
        self.writes: list[tuple[str, bytes]] = []
        self._read_error: Exception | None = None

    def read_diagram_bytes(self, relative_path: str) -> bytes:
        if self._read_error is not None:
            raise self._read_error
        return MINI_PNG

    def write_report_bytes(self, relative_path: str, data: bytes) -> None:
        self.writes.append((relative_path, data))


@pytest.mark.asyncio
async def test_execute_diagram_job_success():
    rel = "in/diagram.png"
    storage = FakeObjectStorage()
    job_id = uuid4()
    body = AnalyzeDiagramJobV1(
        job_id=str(job_id),
        schema_version=1,
        diagram_storage_path=rel,
    ).model_dump_json()

    api = FakeInternalApi()
    metrics = FakePipelineMetrics()

    await execute_diagram_job(body.encode("utf-8"), api, metrics, storage)

    assert len(api.completions) == 1
    assert api.completions[0][0] == job_id
    assert api.completions[0][1].tokens_used == 42

    assert len(api.patches) == 1
    assert api.patches[0][1].status == "PROCESSING"

    assert len(storage.writes) == 1
    assert storage.writes[0][0] == f"{job_id}.json"

    assert WorkerJobPhase.PROCESSING.value in metrics.transitions
    assert WorkerJobPhase.COMPLETED.value in metrics.transitions
    assert metrics.processed == ["success"]


@pytest.mark.asyncio
async def test_execute_diagram_job_invalid_json_records_failure_without_patch():
    api = FakeInternalApi()
    metrics = FakePipelineMetrics()
    storage = FakeObjectStorage()

    with pytest.raises(ValidationError):
        await execute_diagram_job(b"not-json{", api, metrics, storage)

    assert api.patches == []
    assert api.completions == []
    assert metrics.processed == ["error"]
    assert WorkerJobPhase.FAILED.value in metrics.transitions


@pytest.mark.asyncio
async def test_execute_diagram_job_missing_path_patches_error():
    job_id = uuid4()
    body = AnalyzeDiagramJobV1(
        job_id=str(job_id),
        schema_version=1,
        diagram_storage_path=None,
    ).model_dump_json()

    api = FakeInternalApi()
    metrics = FakePipelineMetrics()
    storage = FakeObjectStorage()

    with pytest.raises(MissingDiagramPathError):
        await execute_diagram_job(body.encode("utf-8"), api, metrics, storage)

    assert len(api.patches) == 2
    assert api.patches[0][1].status == "PROCESSING"
    assert api.patches[1][1].status == "ERROR"
    assert api.completions == []
    assert metrics.processed == ["error"]


@pytest.mark.asyncio
async def test_execute_diagram_job_missing_file_patches_error():
    storage = FakeObjectStorage()
    storage._read_error = FileNotFoundError()

    job_id = uuid4()
    body = AnalyzeDiagramJobV1(
        job_id=str(job_id),
        schema_version=1,
        diagram_storage_path="nope/missing.png",
    ).model_dump_json()

    api = FakeInternalApi()
    metrics = FakePipelineMetrics()

    with pytest.raises(FileNotFoundError):
        await execute_diagram_job(body.encode("utf-8"), api, metrics, storage)

    assert len(api.patches) == 2
    assert api.patches[1][1].status == "ERROR"
    assert api.completions == []
