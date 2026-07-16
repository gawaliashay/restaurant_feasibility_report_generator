# from src.workflow.research_orchestrator import RestaurantResearchOrchestrator
from src.evaluation.evaluation_pipeline import evaluation_pipeline
from src.graph_states.workflow_states import WorkflowState

import asyncio


async def main():

    # orchestrator = RestaurantResearchOrchestrator()

    # state = orchestrator.run_pipeline()
    # results = await evaluation_pipeline.evaluate(state)

    state = WorkflowState()
    results = await evaluation_pipeline.evaluate(state)

    print("\nEvaluation Results")
    print("=" * 50)

    for result in results:
        print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())