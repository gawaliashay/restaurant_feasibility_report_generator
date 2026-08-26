"""
Stage check: research only (tools, including RAG retrieve). Saves JSON for the report runner.

From the repo root:
    python -m src.pipeline_runners.research_pipeline_runner
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.pipeline_runners.pipeline import build_state
from src.workflow.research.research_workflow import ResearchWorkflow


def main() -> None:
    state = build_state()
    state = ResearchWorkflow().run(state)
    results = state.get("research_results", {})

    os.makedirs("processed_evidence", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"processed_evidence/research_results_{stamp}.json"
    payload = {
        "timestamp": datetime.now().isoformat(),
        "total_sections": len(results),
        "results": results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    for name, section in results.items():
        n = len(section.get("evidence", []))
        print(f"{name}: {n} evidence items ({section.get('status')})")
    print("Wrote", path)


if __name__ == "__main__":
    main()
