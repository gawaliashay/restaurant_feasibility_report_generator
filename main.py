#!/usr/bin/env python3
"""
Simple entry point for Restaurant Research System.
Run with: python main.py
"""

import sys
from src.workflow.research_orchestrator import RestaurantResearchSystem
from src.logging_exception.logging.logger import logger

def main():
    """Run the restaurant research system."""
    try:
        logger.info("🚀 Starting Restaurant Research System")
        
        # Create and run the research system
        system = RestaurantResearchSystem()
        
        # You can provide custom parameters like this:
        # custom_params = {
        #     "restaurant_concept": "Italian Fine Dining",
        #     "location": {
        #         "local_area": "Downtown",
        #         "city": "San Francisco",
        #         "state": "CA"
        #     },
        #     "investment": "2 million USD",
        #     "target_demographic": "Affluent professionals aged 30-50"
        # }
        
        # Run with default config values
        logger.info("🔍 Running research with default parameters...")
        result = system.run_research()
        
        # Or use custom parameters:
        # result = system.run_research(custom_params)
        
        # Check and display results
        if "error" in result:
            logger.error(f"❌ Research failed: {result['error']}")
            return 1
        
        # Display summary
        print("\n" + "="*50)
        print("RESEARCH COMPLETED SUCCESSFULLY!")
        print("="*50)
        
        # Show generated reports
        export_paths = result.get("export_paths", {})
        if export_paths:
            print("\n📄 Generated Reports:")
            for fmt, path in export_paths.items():
                print(f"  • {fmt.upper()}: {path}")
        else:
            print("\n⚠️  No reports were generated")
        
        # Show key insights if available
        if result.get("executive_summary"):
            print("\n📋 Executive Summary Preview:")
            summary = result["executive_summary"]
            preview = summary[:200] + "..." if len(summary) > 200 else summary
            print(f"  {preview}")
        
        logger.info("✅ Research completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Research cancelled by user")
        logger.warning("Research interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ System error: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())