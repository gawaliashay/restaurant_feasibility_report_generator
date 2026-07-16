# src\evaluation\artifacts\workflow_artifact.py

from pydantic import BaseModel, Field


class WorkflowArtifact(BaseModel):

    workflow_name: str | None = None

    workflow_status: str | None = None

    execution_time: float | None = None

    completed_nodes: list[str] = Field(default_factory=list)

    failed_nodes: list[str] = Field(default_factory=list)

    metadata: dict = Field(default_factory=dict)