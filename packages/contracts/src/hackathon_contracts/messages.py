from pydantic import BaseModel, Field


class AnalyzeDiagramJobV1(BaseModel):
    job_id: str
    schema_version: int = 1
    diagram_storage_path: str | None = Field(
        default=None,
        description="Relative path under shared volume; optional if convention-based",
    )
