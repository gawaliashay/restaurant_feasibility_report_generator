"""Research only (tools + RAG). Saves evidence JSON for report_pipeline_runner."""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.pipeline_runners.pipeline import build_state, save_research_results
from src.workflow.research.research_workflow import ResearchWorkflow


def main() -> None:
    state = ResearchWorkflow().run(build_state())
    results = state.get("research_results", {})
    for name, section in results.items():
        print(f"{name}: {len(section.get('evidence', []))} evidence items ({section.get('status')})")
    print("Wrote", save_research_results(results))


if __name__ == "__main__":
    main()
