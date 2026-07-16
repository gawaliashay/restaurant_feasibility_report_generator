# src\evaluation\artifacts\tool_artifact.py

from pydantic import BaseModel, Field


class ToolExecution(BaseModel):

    tool_name: str

    provider: str | None = None

    status: str | None = None

    latency_ms: float | None = None

    result_count: int | None = None

    retry_count: int = 0

    metadata: dict = Field(default_factory=dict)


class ToolArtifact(BaseModel):

    executions: list[ToolExecution] = Field(default_factory=list)