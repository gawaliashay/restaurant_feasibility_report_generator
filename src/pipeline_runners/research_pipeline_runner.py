"""
Stage check: research only (tools, including RAG retrieve). Saves JSON for the report runner.

From the repo root:
    python -m src.pipeline_runners.research_pipeline_runner
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.pipeline_runners.pipeline import build_state, save_research_results
from src.workflow.research.research_workflow import ResearchWorkflow


def main() -> None:
    state = build_state()
    state = ResearchWorkflow().run(state)
    results = state.get("research_results", {})

    path = save_research_results(results)

    for name, section in results.items():
        n = len(section.get("evidence", []))
        print(f"{name}: {n} evidence items ({section.get('status')})")
    print("Wrote", path)


if __name__ == "__main__":
    main()
