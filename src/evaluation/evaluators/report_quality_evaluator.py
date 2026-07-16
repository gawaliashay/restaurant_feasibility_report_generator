# src\evaluation\evaluators\report_quality_evaluator.py
from src.logging_exception.logging.logger import logger
from src.evaluation.base_evaluator import BaseEvaluator
from src.evaluation.artifacts.evaluation_artifact import EvaluationArtifact
from src.evaluation.evaluation_result import EvaluationResult

class ReportQualityEvaluator(BaseEvaluator):

    async def evaluate(
        self,
        artifact: EvaluationArtifact,
        evaluation_name: str,
    ) -> EvaluationResult:

        report = artifact.report.report

        if report:
            score = 10.0
            evaluation_status = "success"

            feedback = {
                "report_present": True,
                "report_length": artifact.report.report_size,
            }
        else:
            score = 0.0
            evaluation_status = "failed"

            feedback = {
                "report_present": False,
                "report_length": 0,
            }

        result = EvaluationResult(
            evaluation_name=evaluation_name,
            provider=self.config["provider"],
            score=score,
            evaluation_status=evaluation_status,
            feedback=feedback
        )

        logger.info(
            f"Report evaluation completed. Status=%s", evaluation_status)

        return result