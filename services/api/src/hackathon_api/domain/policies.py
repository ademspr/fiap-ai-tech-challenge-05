"""Domain policies and limits (no I/O)."""

from dataclasses import dataclass
from typing import Final

from hackathon_api.domain.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError

# Allowed media types for diagram upload (MVP set).
ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "application/pdf",
    }
)


@dataclass(frozen=True, slots=True)
class UploadPolicy:
    """Content policy and size limits for new analysis jobs (from config at runtime)."""

    allowed_content_types: frozenset[str]
    max_upload_bytes: int
    min_tokens_estimate: int

    def validate_new_upload(self, content_type: str, payload_size: int) -> None:
        """Domain rules for accepting a new diagram upload (before persistence)."""
        if content_type not in self.allowed_content_types:
            raise UnsupportedMediaTypeError
        if payload_size > self.max_upload_bytes:
            raise PayloadTooLargeError
