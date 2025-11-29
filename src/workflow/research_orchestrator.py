# src/workflow/research_orchestrator.py

from src.workflow.analyst_team_creator import AnalystTeamCreator
from src.workflow.parallel_research_engine import ParallelResearchEngine  
from src.workflow.report_compiler import ReportCompiler
from src.configuration.config_loader import config_loader
from src.graph_states.states import ResearchState
from src.logging_exception.logging.logger import logger


class RestaurantResearchSystem:
    """Main system that orchestrates all three graphs."""
    
    def __init__(self):
        self.config = config_loader.get()
        self.team_creator = AnalystTeamCreator()
        self.research_engine = ParallelResearchEngine()
        self.report_compiler = ReportCompiler()
        logger.info("🏗️  Restaurant Research System initialized with 3 graphs")
    
    def run_research(self, initial_state):
        """Execute the complete research pipeline."""
        logger.info("🚀 Starting complete research pipeline")
        
        # Graph 1: Create analyst team
        logger.info("📋 Executing Graph 1: Analyst Team Creation")
        graph_1_result = self.team_creator.create_team(initial_state)
        
        # Graph 2: Conduct parallel research
        logger.info("🔍 Executing Graph 2: Parallel Research")
        graph_2_result = self.research_engine.execute_research(graph_1_result)
        
        # Graph 3: Compile reports
        logger.info("📄 Executing Graph 3: Report Compilation")
        graph_3_result = self.report_compiler.compile_reports(graph_2_result)
        
        logger.info("🎉 Research pipeline completed successfully")
        return graph_3_result


def main():
    """Standalone execution with config-driven test state."""
    system = RestaurantResearchSystem()
    
    # Get configuration values
    business_config = config_loader.get('business_case.default', {})
    research_config = config_loader.get('research', {})
    
    # Create test state from configuration
    test_state = ResearchState(
        restaurant_concept=business_config.get('restaurant_concept', 'Quick Service Restaurant'),
        target_location=business_config.get('target_location', 'Beside Dmart, Baner, pune'),
        investment=business_config.get('investment', '₹ 2 Lakhs'),
        target_demographic=business_config.get('target_demographic', 'Professionals 25-45, health-conscious'),
        special_note=business_config.get('special_note', 'fastfood demand, spending power, competition density'),
        max_analysts=research_config.get('max_analysts', 1),
        # Initialize other required fields with empty values
        dynamic_analysts=[],
        analysts_team=[],
        research_tasks=[],
        research_results={},
        research_summary={},
        executive_summary="",
        market_analysis="",
        financial_recommendations="",
        risk_assessment="",
        final_report="",
        export_paths={},
        accept=False,
        extra_instructions="",
        retry_count=0,
        current_task=None,
        current_analyst=None
    )
    
    logger.info("🧪 Running research system with configuration:")
    logger.info(f"🏪 Concept: {test_state['restaurant_concept']}")
    logger.info(f"📍 Location: {test_state['target_location']}")
    logger.info(f"💰 Investment: {test_state['investment']}")
    logger.info(f"👥 Demographic: {test_state['target_demographic']}")
    logger.info(f"🔬 Max Analysts: {test_state['max_analysts']}")
    if test_state.get('special_note'):
        logger.info(f"📝 Special Note: {test_state['special_note']}")
    
    return system.run_research(test_state)


if __name__ == "__main__":
    main()