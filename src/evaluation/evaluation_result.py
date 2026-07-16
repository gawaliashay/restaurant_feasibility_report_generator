# src\evaluation\evaluation_result.py
from pydantic import BaseModel, Field
from typing import Any, Literal

class EvaluationResult(BaseModel):
    """
    Standard output returned by every evaluator.
    """
    evaluation_name: str
    provider: str
    score: float | None = None
    evaluation_status: Literal["success", "failed", "skip"]
    feedback: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)