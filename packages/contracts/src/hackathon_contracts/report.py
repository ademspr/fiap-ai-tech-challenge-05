from pydantic import BaseModel, Field


class IdentifiedComponent(BaseModel):
    id: str = Field(..., examples=["c-1"])
    name: str
    description: str


class ArchitecturalRisk(BaseModel):
    id: str = Field(..., examples=["r-1"])
    title: str
    description: str
    severity: str | None = Field(
        default=None,
        description="Optional severity label, e.g. low|medium|high",
    )


class BasicRecommendation(BaseModel):
    id: str = Field(..., examples=["rec-1"])
    title: str
    description: str


class TechnicalReportV1(BaseModel):
    """Structured technical report (not a PDF export)."""

    schema_version: int = 1
    identified_components: list[IdentifiedComponent] = Field(default_factory=list)
    architectural_risks: list[ArchitecturalRisk] = Field(default_factory=list)
    basic_recommendations: list[BasicRecommendation] = Field(default_factory=list)
    tokens_used: int = Field(ge=0, default=0)
    model_metadata: dict[str, str] | None = None
