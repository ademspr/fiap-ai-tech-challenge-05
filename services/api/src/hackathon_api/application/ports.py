"""Application ports (depend only on domain types)."""

from typing import Any, Protocol
from uuid import UUID

from hackathon_api.domain.entities import AnalysisJob, Client


class FileStoragePort(Protocol):
    def save_uploaded_diagram(
        self, job_id: UUID, filename: str, data: bytes
    ) -> tuple[str, str]: ...

    def read_report_bytes(self, report_relative_path: str) -> bytes: ...


class AnalyzeJobPublisherPort(Protocol):
    async def publish(self, job_id: UUID, diagram_storage_path: str, content_type: str) -> None: ...


class ClientAuthenticatorPort(Protocol):
    async def authenticate_bearer(self, bearer_plain: str) -> Client | None: ...


class TechnicalReportReaderPort(Protocol):
    """Return validated, JSON-serializable report payload for a stored file path."""

    def read_public_json(self, report_relative_path: str) -> dict[str, Any]: ...


class JobRepositoryPort(Protocol):
    async def get_by_id(self, job_id: UUID) -> AnalysisJob | None: ...

    async def get_for_client(self, client_id: UUID, job_id: UUID) -> AnalysisJob: ...

    async def create_received(
        self,
        *,
        client_id: UUID,
        content_type: str,
        size_bytes: int,
    ) -> AnalysisJob: ...

    async def set_diagram(
        self,
        job_id: UUID,
        diagram_storage_path: str,
        diagram_checksum: str,
    ) -> AnalysisJob: ...

    async def apply_status_patch(
        self,
        job_id: UUID,
        status: str,
        error_message: str | None,
    ) -> None: ...

    async def complete_with_report(
        self,
        job_id: UUID,
        *,
        report_storage_path: str,
        tokens_used: int,
        report_checksum: str | None,
        report_schema_version: int,
    ) -> None: ...


class JobMetricsPort(Protocol):
    def increment_status_label(self, status: str) -> None: ...
    def add_upload_bytes(self, byte_count: int) -> None: ...
    def add_tokens_consumed(self, client_id: str, token_count: int) -> None: ...


class HttpRequestMetricsPort(Protocol):
    def record_http_request(
        self,
        method: str,
        path_group: str,
        endpoint: str,
        status_code: int,
        elapsed_seconds: float,
    ) -> None: ...
