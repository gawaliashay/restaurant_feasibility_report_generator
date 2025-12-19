"""
Research Orchestrator Module

This module orchestrates the complete restaurant research pipeline, coordinating
three main phases: analyst team creation, parallel research execution, and report
compilation. It serves as the top-level controller for the research system.
"""

from src.workflow.analyst_team_creator import AnalystTeamCreator
from src.workflow.parallel_research_engine import ParallelResearchEngine
from src.workflow.report_compiler import ReportCompiler
from src.configuration.config_loader import config_loader
from src.graph_states.states import ResearchState

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException


class RestaurantResearchSystem:
    """
    Top-Level Orchestrator for Restaurant Research Pipeline.
    
    Executes three sequential workflows:
    1. Analyst Team Creation - Generates specialized research analysts
    2. Parallel Research Execution - Conducts research using multiple tools
    3. Report Compilation - Generates comprehensive business reports
    
    Attributes:
        config (dict): Loaded configuration
        business_config (dict): Business case configuration
        research_config (dict): Research-specific configuration
        team_creator (AnalystTeamCreator): Analyst team creation component
        research_engine (ParallelResearchEngine): Research execution component
        report_compiler (ReportCompiler): Report generation component
    """
    
    def __init__(self):
        """Initialize the research system with all workflow components."""
        try:
            logger.info("Initializing Restaurant Research System")
            
            # Load configuration
            self.config = config_loader.get()
            self.business_config = self.config['business_case']['default']
            self.research_config = self.config['research']
            
            # Initialize workflow components
            self.team_creator = AnalystTeamCreator()
            self.research_engine = ParallelResearchEngine()
            self.report_compiler = ReportCompiler()
            
            logger.info("Restaurant Research System initialized successfully")
            
        except KeyError as e:
            logger.error(f"Missing configuration section: {e}")
            raise CustomException(
                f"Configuration error: Missing section {e}",
                "CONFIGURATION_ERROR",
                {"missing_section": str(e)}
            )
        except Exception as e:
            logger.error(f"Failed to initialize RestaurantResearchSystem: {e}")
            raise CustomException(
                f"System initialization error: {str(e)}",
                "SYSTEM_INITIALIZATION_ERROR",
                {"component": "RestaurantResearchSystem"}
            )

    def _build_initial_state(self, custom_params: dict = None) -> ResearchState:
        """
        Build initial research state with defaults and custom overrides.
        
        Args:
            custom_params (dict, optional): Parameters to override defaults.
                Supports: restaurant_concept, investment, target_demographic,
                special_note, max_analysts, and location fields.
        
        Returns:
            ResearchState: Initialized research state object
        
        Raises:
            CustomException: If state building fails
        """
        try:
            logger.debug("Building initial research state")
            
            params = custom_params or {}
            location_config = self.business_config['location']
            
            # Build comprehensive state dictionary
            state_data = {
                # Business context
                "restaurant_concept": params.get('restaurant_concept', 
                                                self.business_config['restaurant_concept']),
                "investment": params.get('investment', 
                                        self.business_config['investment']),
                "target_demographic": params.get('target_demographic', 
                                                self.business_config['target_demographic']),
                "special_note": params.get('special_note', 
                                          self.business_config['special_note']),
                "max_analysts": params.get('max_analysts', 
                                          self.research_config['max_analysts']),
                
                # Location context
                "location": {
                    "society": params.get('society', 
                                         location_config.get('society', '')),
                    "local_area": params.get('local_area', 
                                            location_config['local_area']),
                    "city": params.get('city', location_config['city']),
                    "state": params.get('state', location_config['state']),
                    "pincode": params.get('pincode', location_config['pincode'])
                },
                
                # Research workflow state
                "dynamic_analysts": [],
                "analysts_team": [],
                "research_tasks": [],
                "research_results": {},
                "research_summary": {},
                
                # Report compilation state
                "executive_summary": "",
                "market_analysis": "",
                "financial_recommendations": "",
                "risk_assessment": "",
                "implementation_roadmap": "",
                "conclusion": "",
                "final_report": "",
                "export_paths": {},
                
                # Control and flow state
                "accept": False,
                "extra_instructions": "",
                "retry_count": 0,
                "current_task": None,
                "current_analyst": None
            }
            
            # Validate location structure
            if not isinstance(state_data["location"], dict):
                logger.warning("Location data invalid, resetting to empty dict")
                state_data["location"] = {}
            
            # Log key initialization details
            logger.debug(f"Initial concept: {state_data['restaurant_concept']}")
            logger.debug(f"Initial location: {state_data['location']}")
            logger.debug(f"Max analysts: {state_data['max_analysts']}")
            
            return ResearchState(**state_data)
            
        except Exception as e:
            logger.error(f"Failed to build initial state: {e}")
            raise CustomException(
                f"State building error: {str(e)}",
                "STATE_BUILDING_ERROR",
                {"custom_params": custom_params}
            )

    def _validate_critical_parameters(self, state: ResearchState) -> bool:
        """
        Validate critical research parameters for minimum viability.
        
        Args:
            state (ResearchState): Research state to validate
        
        Returns:
            bool: True if parameters are valid, False otherwise
        
        Raises:
            CustomException: If validation fails critically
        """
        try:
            logger.debug("Validating critical research parameters")
            
            # Validate restaurant concept
            concept = state.get("restaurant_concept", "").strip()
            if not concept or len(concept) < 3:
                logger.error(f"Invalid restaurant concept: '{concept}'")
                return False
            
            # Validate location structure
            location = state.get("location", {})
            if not isinstance(location, dict):
                logger.error("Location is not a dictionary")
                return False
            
            # Validate required location fields
            city = location.get("city", "").strip()
            state_name = location.get("state", "").strip()
            
            if not city:
                logger.error("City is required for research")
                return False
            if not state_name:
                logger.error("State is required for research")
                return False
            
            # Validate investment format
            investment = state.get("investment", "")
            if not investment:
                logger.warning("Investment amount not specified")
            
            logger.debug("Critical parameters validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            raise CustomException(
                f"Parameter validation error: {str(e)}",
                "PARAMETER_VALIDATION_ERROR",
                {"state_keys": list(state.keys()) if hasattr(state, 'keys') else []}
            )

    def _log_research_parameters(self, state: ResearchState):
        """
        Log key research parameters for monitoring and debugging.
        
        Args:
            state (ResearchState): Research state containing parameters
        
        Raises:
            CustomException: If logging fails
        """
        try:
            logger.info("Research Parameters:")
            logger.info(f"  Concept: {state.get('restaurant_concept', 'N/A')}")
            
            location = state.get("location", {})
            if isinstance(location, dict):
                area = location.get('local_area', '')
                city = location.get('city', '')
                logger.info(f"  Location: {area}, {city}".strip(', '))
            
            logger.info(f"  Investment: {state.get('investment', 'N/A')}")
            logger.info(f"  Target Demographic: {state.get('target_demographic', 'N/A')}")
            logger.info(f"  Max Analysts: {state.get('max_analysts', 'N/A')}")
            
        except Exception as e:
            logger.error(f"Failed to log research parameters: {e}")
            raise CustomException(
                f"Parameter logging error: {str(e)}",
                "PARAMETER_LOGGING_ERROR"
            )

    def run_research(self, custom_params: dict = None) -> dict:
        """
        Execute the complete restaurant research pipeline.
        
        Args:
            custom_params (dict, optional): Custom parameters to override defaults.
                Example:
                {
                    "restaurant_concept": "Sushi Bar",
                    "investment": "₹500,000",
                    "location": {"city": "Mumbai", "state": "Maharashtra"}
                }
        
        Returns:
            dict: Final research results including compiled reports and export paths
        
        Raises:
            CustomException: If any pipeline phase fails
        """
        try:
            logger.info("🚀 Starting Restaurant Research Pipeline")
            
            # Phase 0: Initialization and Validation
            initial_state = self._build_initial_state(custom_params)
            
            if not self._validate_critical_parameters(initial_state):
                error_msg = "Critical parameter validation failed"
                logger.error(error_msg)
                raise CustomException(
                    error_msg,
                    "PARAMETER_VALIDATION_FAILED",
                    {"concept": initial_state.get("restaurant_concept", "")}
                )
            
            self._log_research_parameters(initial_state)
            
            # Phase 1: Analyst Team Creation
            logger.info("Phase 1: Analyst Team Creation")
            team_result = self.team_creator.create_team(initial_state)
            logger.debug("Analyst team creation completed")
            
            # Phase 2: Parallel Research Execution
            logger.info("Phase 2: Parallel Research Execution")
            research_result = self.research_engine.execute_research(team_result)
            logger.debug("Parallel research execution completed")
            
            # Phase 3: Report Compilation
            logger.info("Phase 3: Report Compilation")
            final_result = self.report_compiler.compile_reports(research_result)
            logger.debug("Report compilation completed")
            
            logger.info("✅ Research pipeline completed successfully")
            return final_result
            
        except CustomException as e:
            logger.error(f"Research pipeline failed with CustomException: {e}")
            # Re-raise to preserve error context
            raise
        except Exception as e:
            logger.error(f"Research pipeline failed: {e}")
            raise CustomException(
                f"Research pipeline error: {str(e)}",
                "PIPELINE_EXECUTION_ERROR",
                {"custom_params": custom_params}
            )

    def run_default_research(self) -> dict:
        """
        Execute research with configuration-defined defaults only.
        
        Returns:
            dict: Research results using default parameters
        
        Raises:
            CustomException: If default research execution fails
        """
        try:
            logger.info("Starting default research with configuration parameters")
            return self.run_research()
        except Exception as e:
            logger.error(f"Default research failed: {e}")
            raise CustomException(
                f"Default research error: {str(e)}",
                "DEFAULT_RESEARCH_ERROR"
            )


def main() -> dict:
    """
    Standalone execution entry point for the research system.
    
    Returns:
        dict: Research results or error information
    
    Raises:
        CustomException: If standalone execution fails
    """
    try:
        logger.info("=" * 60)
        logger.info("Restaurant Research System - Standalone Execution")
        logger.info("=" * 60)
        
        # Initialize and execute research system
        system = RestaurantResearchSystem()
        result = system.run_research()
        
        # Display export summary
        export_paths = result.get("export_paths", {})
        if export_paths:
            logger.info("📄 Generated Reports:")
            for fmt, path in export_paths.items():
                logger.info(f"  • {fmt.upper()}: {path}")
            
            # Show preview of executive summary if available
            exec_summary = result.get("executive_summary", "")
            if exec_summary:
                preview = exec_summary[:200] + "..." if len(exec_summary) > 200 else exec_summary
                logger.info(f"📋 Executive Summary Preview: {preview}")
        else:
            logger.warning("⚠️ No reports were generated")
            
        logger.info("=" * 60)
        logger.info("✅ System execution completed")
        logger.info("=" * 60)
        
        return result
        
    except CustomException as e:
        logger.error(f"System execution failed with CustomException: {e}")
        return {
            "error": str(e),
            "error_type": e.error_type,
            "error_context": e.context
        }
    except Exception as e:
        logger.error(f"System execution failed: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    """
    Entry point for standalone script execution.
    
    Usage:
        python research_orchestrator.py
    """
    main()