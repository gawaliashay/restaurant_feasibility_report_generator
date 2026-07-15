from pydantic import BaseModel, Field


class ReportArtifact(BaseModel):

    report: dict = Field(default_factory=dict)

    report_size: int | None = None

    metadata: dict = Field(default_factory=dict)