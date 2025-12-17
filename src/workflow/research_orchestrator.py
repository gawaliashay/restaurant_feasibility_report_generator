# src\workflow\research_orchestrator.py

from src.workflow.analyst_team_creator import AnalystTeamCreator
from src.workflow.parallel_research_engine import ParallelResearchEngine
from src.workflow.report_compiler import ReportCompiler
from src.configuration.config_loader import config_loader
from src.graph_states.states import ResearchState

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException


class RestaurantResearchSystem:
    """Top-Level Orchestrator - Executes Three Graphs in Fixed Order."""

    def __init__(self):
        self.config = config_loader.get()
        self.business_config = self.config['business_case']['default']
        self.research_config = self.config['research']
        
        # Initialize workflow components
        self.team_creator = AnalystTeamCreator()
        self.research_engine = ParallelResearchEngine()
        self.report_compiler = ReportCompiler()
        
        logger.info("Restaurant Research System initialized")

    def _build_initial_state(self, custom_params: dict = None) -> ResearchState:
        """Build initial research state from config with optional custom overrides."""
        params = custom_params or {}
        location_config = self.business_config['location']
        
        # Build the state dictionary with all required fields
        state_data = {
            # Business context - custom or config default
            "restaurant_concept": params.get('restaurant_concept', self.business_config['restaurant_concept']),
            "investment": params.get('investment', self.business_config['investment']),
            "target_demographic": params.get('target_demographic', self.business_config['target_demographic']),
            "special_note": params.get('special_note', self.business_config['special_note']),
            "max_analysts": params.get('max_analysts', self.research_config['max_analysts']),
            
            # Location context - structured approach with proper defaults
            "location": {
                "society": params.get('society', location_config.get('society', '')),
                "local_area": params.get('local_area', location_config['local_area']),
                "city": params.get('city', location_config['city']),
                "state": params.get('state', location_config['state']),
                "pincode": params.get('pincode', location_config['pincode'])
            },
            
            # Research state initialization
            "dynamic_analysts": [],
            "analysts_team": [],
            "research_tasks": [],
            "research_results": {},
            "research_summary": {},
            
            # Report state initialization
            "executive_summary": "",
            "market_analysis": "",
            "financial_recommendations": "",
            "risk_assessment": "",
            "implementation_roadmap": "",
            "conclusion": "",
            "final_report": "",
            "export_paths": {},
            
            # Control state
            "accept": False,
            "extra_instructions": "",
            "retry_count": 0,
            "current_task": None,
            "current_analyst": None
        }
        
        # Ensure all location fields are properly set
        if not isinstance(state_data["location"], dict):
            state_data["location"] = {}
        
        # Log the initial state for debugging
        logger.debug(f"Initial state location: {state_data['location']}")
        logger.debug(f"Initial state concept: {state_data['restaurant_concept']}")
        
        return ResearchState(**state_data)

    def _validate_critical_parameters(self, state: ResearchState) -> bool:
        """Validate that critical parameters are present and reasonable."""
        # Check restaurant concept
        concept = state.get("restaurant_concept", "").strip()
        if not concept or len(concept) < 3:
            logger.error("Restaurant concept is missing or too short")
            return False
        
        # Check location data
        location = state.get("location", {})
        if not isinstance(location, dict):
            logger.error("Location data is not properly structured")
            return False
            
        if not location.get("city") or not location.get("state"):
            logger.error("City and state are required for research")
            return False
        
        return True

    def _log_research_parameters(self, state: ResearchState):
        """Log key research parameters."""
        location = state.get("location", {})
        
        logger.info("Research Parameters:")
        logger.info(f"  Concept: {state['restaurant_concept']}")
        logger.info(f"  Location: {location.get('local_area', '')}, {location.get('city', '')}")
        logger.info(f"  Investment: {state['investment']}")
        logger.info(f"  Target Demographic: {state['target_demographic']}")
        logger.info(f"  Max Analysts: {state['max_analysts']}")

    def run_research(self, custom_params: dict = None) -> dict:
        """
        Execute complete research pipeline.
        
        Args:
            custom_params: Optional parameters to override config defaults
            
        Returns:
            Final research results with compiled reports
        """
        try:
            # Build and validate initial state
            initial_state = self._build_initial_state(custom_params)
            
            if not self._validate_critical_parameters(initial_state):
                return {"error": "Critical parameter validation failed"}
            
            logger.info("Starting Restaurant Research Pipeline")
            self._log_research_parameters(initial_state)
            
            # Phase 1: Analyst Team Creation
            logger.info("Phase 1: Analyst Team Creation")
            team_result = self.team_creator.create_team(initial_state)
            
            # Phase 2: Parallel Research Execution
            logger.info("Phase 2: Parallel Research Execution")
            research_result = self.research_engine.execute_research(team_result)
            
            # Phase 3: Report Compilation
            logger.info("Phase 3: Report Compilation")
            final_result = self.report_compiler.compile_reports(research_result)
            
            logger.info("Research pipeline completed successfully")
            return final_result
            
        except Exception as e:
            logger.error(f"Research pipeline failed: {str(e)}")
            return {"error": str(e)}

    def run_default_research(self) -> dict:
        """Execute research with config-defined defaults only."""
        return self.run_research()


def main():
    """Standalone execution."""
    
    try:
        system = RestaurantResearchSystem()
        logger.info("Restaurant Research System - Starting Execution")
        
        result = system.run_research()
        
        # Display export summary if available
        export_paths = result.get("export_paths", {})
        if export_paths:
            logger.info("Generated Reports:")
            for fmt, path in export_paths.items():
                logger.info(f"  {fmt.upper()}: {path}")
        else:
            logger.warning("No reports were generated")
            
        return result
        
    except Exception as e:
        logger.error(f"System execution failed: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    main()