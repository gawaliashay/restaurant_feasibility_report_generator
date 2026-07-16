# src\evaluation\artifacts\llm_artifact.py

from pydantic import BaseModel, Field


class LLMExecution(BaseModel):

    provider: str | None = None

    model: str | None = None

    latency_ms: float | None = None

    prompt_tokens: int | None = None

    completion_tokens: int | None = None

    total_tokens: int | None = None

    cost: float | None = None

    metadata: dict = Field(default_factory=dict)


class LLMArtifact(BaseModel):

    executions: list[LLMExecution] = Field(default_factory=list)