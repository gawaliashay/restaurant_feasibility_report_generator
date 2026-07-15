# playground\test_evaluation.py

import asyncio

from evaluation.evaluation_artifact import EvaluationArtifact, ReportContext, WorkflowContext
from evaluation.evaluation_manager import EvaluationManager


async def main():

    context = EvaluationArtifact(

        workflow=WorkflowContext(
            execution_time=18.4,
            workflow_status="success",
        ),

        report=ReportContext(
            report="""
            # Restaurant Market Report

            Pune has experienced significant growth in premium dining...
            """
        ),
    )

    manager = EvaluationManager()

    results = await manager.evaluate(context)

    for result in results:
        print(result.model_dump_json(indent=4))


if __name__ == "__main__":
    asyncio.run(main())