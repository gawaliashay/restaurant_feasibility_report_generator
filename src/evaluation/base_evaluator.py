# src\evaluation\base_evaluator.py

from abc import ABC, abstractmethod
from typing import Any

from src.evaluation.artifacts.evaluation_artifact import EvaluationArtifact
from src.evaluation.evaluation_result import EvaluationResult


class BaseEvaluator(ABC):
    """
    Base class for all evaluators.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    async def evaluate(
        self,
        artifact: EvaluationArtifact,
        evaluation_name: str,
    ) -> EvaluationResult:
        """
        Execute evaluation and return standardized result.
        """
        raise NotImplementedError