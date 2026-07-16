# src\evaluation\evaluation_pipeline.py

"""
Entry point for the evaluation pipeline.

Builds evaluation artifacts from the workflow state and
executes all enabled evaluators.
"""

from src.graph_states.workflow_states import WorkflowState
from src.evaluation.builders.artifact_builder import ArtifactBuilder
from src.evaluation.evaluation_manager import EvaluationManager
from src.evaluation.evaluation_result import EvaluationResult
from src.logging_exception.logging.logger import logger


class EvaluationPipeline:
    """
    Executes the complete evaluation pipeline.

    WorkflowState
        ↓
    EvaluationArtifact
        ↓
    Enabled Evaluators
        ↓
    Evaluation Results
    """

    def __init__(self):
        self.artifact_builder = ArtifactBuilder()
        self.evaluation_manager = EvaluationManager()

    async def evaluate(
        self,
        state: WorkflowState,
    ) -> list[EvaluationResult]:
        """
        Execute all enabled evaluators.

        Args:
            state:
                Final workflow state.

        Returns:
            List of evaluation results.
        """

        logger.info("Starting evaluation pipeline.")

        artifact = self.artifact_builder.build(state)

        results = await self.evaluation_manager.evaluate(
            artifact=artifact
        )

        logger.info(
            "Evaluation pipeline completed. %s evaluator(s) executed.",
            len(results),
        )

        return results


evaluation_pipeline = EvaluationPipeline()