from typing import Protocol
from uuid import UUID

from hackathon_contracts import JobCompletionV1, JobPatchV1


class WorkerInternalApiPort(Protocol):
    """Patch job lifecycle and submit completion to the internal API."""

    async def patch_job(self, job_id: UUID, body: JobPatchV1) -> None: ...

    async def complete_job(self, job_id: UUID, body: JobCompletionV1) -> None: ...


class WorkerPipelineMetricsPort(Protocol):
    def record_state_transition(self, to_phase: str) -> None: ...
    def record_diagram_processed(self, outcome: str) -> None: ...


class WorkerObjectStoragePort(Protocol):
    """Reads diagrams and writes reports via object storage (MinIO/S3)."""

    def read_diagram_bytes(self, relative_path: str) -> bytes: ...

    def write_report_bytes(self, relative_path: str, data: bytes) -> None: ...
