# src/evaluation/evaluation_manager.py

from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger

from src.evaluation.artifacts.evaluation_artifact import EvaluationArtifact
from src.evaluation.evaluation_loader import evaluation_loader
from src.evaluation.evaluation_result import EvaluationResult


class EvaluationManager:

    async def evaluate(
        self,
        artifact: EvaluationArtifact,
    ) -> list[EvaluationResult]:

        evaluation_config = config_loader.get(
            "evaluation.evaluators",
            {},
        )

        results: list[EvaluationResult] = []

        for evaluation_name, evaluator_config in evaluation_config.items():
            if evaluator_config.get("enabled", False):
                # Run the evaluator
                logger.info(f"Running evaluator: {evaluation_name}")
                evaluator = evaluation_loader.load(evaluation_name)
                result = await evaluator.evaluate(artifact=artifact, evaluation_name=evaluation_name)
                results.append(result)
                
            else:
                # Skip the evaluator
                logger.debug(f"Skipping evaluator: {evaluation_name}")
            
        logger.info("Evaluation pipeline completed.")
        return results