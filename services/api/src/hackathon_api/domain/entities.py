"""Core domain types (independent of persistence and frameworks)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hackathon_api.domain.exceptions import InsufficientTokensError


@dataclass(frozen=True, slots=True)
class Client:
    id: UUID
    token_balance: int

    def require_minimum_balance_for_upload(self, min_tokens_estimate: int) -> None:
        """Reserve rule before creating a job (estimate must fit current balance)."""
        if self.token_balance < min_tokens_estimate:
            raise InsufficientTokensError

    def debited(self, tokens_used: int) -> "Client":
        """Return a new client state after paying for a completed analysis (immutable)."""
        if self.token_balance < tokens_used:
            raise InsufficientTokensError
        return Client(id=self.id, token_balance=self.token_balance - tokens_used)


@dataclass(slots=True)
class AnalysisJob:
    id: UUID
    client_id: UUID
    status: str
    diagram_storage_path: str
    report_storage_path: str | None
    report_schema_version: int | None
    content_type: str
    size_bytes: int
    diagram_checksum: str | None
    report_checksum: str | None
    tokens_used: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
