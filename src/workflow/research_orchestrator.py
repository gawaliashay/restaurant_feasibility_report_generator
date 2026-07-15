# src\workflow\research_orchestrator.py

"""
Orchestrates restaurant research pipeline using LangGraph workflows.
Phase 1: Parallel research | Phase 2: Report compilation & export
"""

from typing import Any, Dict, Optional, cast

from dotenv import load_dotenv
from langsmith import traceable

from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.graph_states.workflow_states import WorkflowState
from src.workflow.section_research_engine import SectionResearchEngine
from src.workflow.report_compiler import ReportCompiler


class RestaurantResearchOrchestrator:
    """Orchestrates research pipeline: research → report."""

    def __init__(self):
        config = config_loader.get_all()
        
        # Business config
        self.business = config.get("business_case", {}).get("default", {})
        
        # Engines
        self.research_engine = SectionResearchEngine()
        self.report_compiler = ReportCompiler()
        
        # Validate
        if not self.business:
            raise ValueError("Missing business_case.default in configs.yaml")
        if not self.business.get("location"):
            raise ValueError("Missing business_case.default.location")
        
        # Setup LangSmith
        load_dotenv()
        tracing_enabled = config.get("monitoring", {}).get("langsmith", {}).get("tracing", False)
        logger.info("LangSmith tracing %s", "enabled" if tracing_enabled else "disabled")
        
        logger.info("Orchestrator initialized")

    def _build_state(self, params: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """Build initial workflow state from config and custom params."""
        params = params or {}
        location = self.business.get("location", {})
        
        # Required fields
        concept = params.get("restaurant_concept") or self.business.get("restaurant_concept", "")
        if not concept:
            raise ValueError("restaurant_concept is required")
        
        city = params.get("city") or location.get("city", "")
        state = params.get("state") or location.get("state", "")
        if not city or not state:
            raise ValueError("city and state are required")
        
        return cast(WorkflowState, {
            # Business
            "restaurant_concept": concept,
            "investment": params.get("investment") or self.business.get("investment", ""),
            "target_demographic": params.get("target_demographic") or self.business.get("target_demographic", ""),
            "special_note": params.get("special_note") or self.business.get("special_note", ""),
            
            # Location
            "society": params.get("society") or location.get("society", ""),
            "local_area": params.get("local_area") or location.get("local_area", ""),
            "city": city,
            "state": state,
            "pincode": params.get("pincode") or location.get("pincode", ""),
            
            # Runtime (empty)
            "research_results": {},
            "completed_sections": [],
            "research_tasks": [],
            "final_report": {},
            "export_paths": {},
            
            # Control
            "accept": False,
            "extra_instructions": "",
            "workflow_id": "",
            "report_timestamp": "",
        })

    @traceable(name="Restaurant Market Research System")
    def run_pipeline(self, params: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """Run complete pipeline: research → report."""
        logger.info("Starting research pipeline")
        
        state = self._build_state(params)
        
        # Phase 1: Research (parallel LangGraph)
        logger.info("Executing research sections")
        research_result = self.research_engine.execute_research(state)
        state = cast(WorkflowState, {**state, **research_result})
        
        # Phase 2: Report (linear LangGraph)
        logger.info("Compiling and exporting report")
        report_result = self.report_compiler.compile_report(state)
        state = cast(WorkflowState, {**state, **report_result})
        
        # Summary
        completed = state.get("completed_sections", [])
        exports = state.get("export_paths", {})
        
        logger.info("=" * 60)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info(f"   Sections Completed: {len(completed)}")
        logger.info(f"   Reports Exported: {len(exports)}")
        logger.info("=" * 60)
        
        return state


# ==========================================================
# CLI ENTRY POINT
# ==========================================================

def main() -> Dict[str, Any]:
    """CLI entry point with argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Restaurant Market Research System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.workflow.research_orchestrator
  python -m src.workflow.research_orchestrator --concept "Pizza" --city "Mumbai"
        """
    )
    
    # CLI args mapping: arg_name -> state_key
    arg_mapping = {
        "concept": "restaurant_concept",
        "investment": "investment",
        "demographic": "target_demographic",
        "special_note": "special_note",
        "society": "society",
        "local_area": "local_area",
        "city": "city",
        "state": "state",
        "pincode": "pincode",
    }
    
    for arg, key in arg_mapping.items():
        parser.add_argument(f"--{arg}", type=str, help=f"{key.replace('_', ' ').title()}")
    
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    
    args = parser.parse_args()
    
    try:
        # Build params from CLI args
        params = {}
        for arg, key in arg_mapping.items():
            value = getattr(args, arg.replace("-", "_"), None)
            if value:
                params[key] = value
        
        # Run pipeline
        orchestrator = RestaurantResearchOrchestrator()
        result = orchestrator.run_pipeline(params if params else None)
        
        # Display results
        if not args.quiet:
            print("\n" + "="*60)
            print("✅ RESEARCH PIPELINE COMPLETED")
            print("="*60)
            
            completed = result.get('completed_sections', [])
            print(f"\n📊 Sections Completed: {len(completed)}")
            for section in completed:
                print(f"   • {section.replace('_', ' ').title()}")
            
            exports = result.get('export_paths', {})
            if exports:
                print(f"\n💾 Reports Exported:")
                for fmt, path in exports.items():
                    print(f"   • {fmt.upper()}: {path}")
            
            print("\n" + "="*60 + "\n")
        
        return dict(result)
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted")
        return {}
    except Exception as e:
        logger.error("Pipeline failed: %s", str(e), exc_info=True)
        raise


if __name__ == "__main__":
    main()