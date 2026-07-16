# src/evaluation/evaluators/workflow_evaluator.py

from src.logging_exception.logging.logger import logger
from src.evaluation.base_evaluator import BaseEvaluator
from src.evaluation.artifacts.evaluation_artifact import EvaluationArtifact
from src.evaluation.evaluation_result import EvaluationResult


class WorkflowEvaluator(BaseEvaluator):
    """Evaluates workflow performance based on execution time."""

    async def evaluate(
        self,
        artifact: EvaluationArtifact,
        evaluation_name: str,
    ) -> EvaluationResult:
        """Evaluate workflow execution time against thresholds."""
        logger.info("Workflow evaluation started.")

        execution_time = artifact.workflow.execution_time

        # Check if execution time is available
        if execution_time is None:
            logger.warning("Execution time not available.")
            return EvaluationResult(
                evaluation_name=evaluation_name,
                provider=self.config["provider"],
                score=None,
                evaluation_status="skip",
                feedback={"message": "Execution time not available."},
            )

        # Determine score based on execution time
        threshold = self.config.get("thresholds",{},).get("execution_time_seconds",30)

        if execution_time <= threshold:
            score = 10.0
            status = "success"
        else:
            score = 5.0
            status = "failed"

        logger.info("Workflow evaluation completed. Status=%s", status)

        result =  EvaluationResult(
                evaluation_name=evaluation_name,
                provider=self.config["provider"],
                score=score,
                evaluation_status=status,
                feedback={
                            "execution_time": execution_time,
                            "execution_threshold": threshold,
                        }
                    )
        
        return result