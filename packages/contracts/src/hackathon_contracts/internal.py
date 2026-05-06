from pydantic import BaseModel, Field


class JobPatchV1(BaseModel):
    status: str = Field(..., description="PROCESSING or ERROR")
    error_message: str | None = None


class JobCompletionV1(BaseModel):
    report_storage_path: str = Field(
        ...,
        description="Path relative to reports root on shared volume",
    )
    tokens_used: int = Field(ge=0)
    report_checksum: str | None = None
    report_schema_version: int = 1
    idempotency_key: str | None = None
