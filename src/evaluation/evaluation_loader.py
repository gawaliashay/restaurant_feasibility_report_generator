# src/evaluation/evaluation_loader.py


import importlib

from src.configuration.config_loader import config_loader
from src.logging_exception.exception.custom_exception import CustomException
from src.logging_exception.logging.logger import logger
from evaluation.base_evaluator import BaseEvaluator


class EvaluationLoader:
    """Dynamically loads evaluator instances from configuration."""

    def _import_evaluator_class(self, import_path: str) -> type[BaseEvaluator]:
        """
        Dynamically import an evaluator class.
        Args:
            import_path: Full dotted path to the class (e.g., "src.evaluation.quality.CodeQualityEvaluator")
        Returns:
            The imported class (not an instance)
        Raises:
            CustomException: If import fails
        """
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            evaluator_class = getattr(module, class_name)
            logger.info(f"Imported evaluator class: {class_name}")
            return evaluator_class

        except Exception as e:
            raise CustomException(f"Failed to import evaluator: {import_path}", e)

    def load(self, evaluation_name: str) -> BaseEvaluator:
        """
        Load evaluator instance from configuration.
        Args:
            evaluation_name: Name of the evaluator to load (matches config key)
        Returns:
            Instantiated evaluator object ready for use
        Raises:
            CustomException: If configuration is missing or invalid
        """
        logger.info(f"Loading evaluator: {evaluation_name}")

        # Get configuration for this evaluator
        evaluator_config = config_loader.get(f"evaluation.evaluators.{evaluation_name}")

        # Validate configuration exists
        if evaluator_config is None:
            raise CustomException(
                f"Evaluation '{evaluation_name}' not found in configuration.",
                None,
            )

        # Get import path from config
        import_path = evaluator_config.get("import_path")
        if not import_path:
            raise CustomException(
                f"'import_path' missing for evaluator '{evaluation_name}'.",
                None,
            )

        # Dynamically import the class and instantiate it
        evaluator_class = self._import_evaluator_class(import_path)
        evaluator = evaluator_class(config=evaluator_config)

        logger.info(f"Evaluator loaded successfully: {evaluation_name}")
        return evaluator


# Singleton instance for global use
evaluation_loader = EvaluationLoader()