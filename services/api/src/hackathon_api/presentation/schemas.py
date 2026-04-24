from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from hackathon_api.domain.enums import JobStatus


class AnalysisJobCreateResponse(BaseModel):
    id: UUID
    status: JobStatus


class AnalysisJobPublicView(BaseModel):
    id: UUID
    status: JobStatus
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class TokenBalanceResponse(BaseModel):
    token_balance: int = Field(..., description="Remaining AI token credits")
    unit: str = Field(default="tokens")
