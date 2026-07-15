from pydantic import BaseModel
from datetime import datetime


class MetadataArtifact(BaseModel):

    workflow_id: str | None = None

    trace_id: str | None = None

    project_name: str | None = None

    created_at: datetime | None = None