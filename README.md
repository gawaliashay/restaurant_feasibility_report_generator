# Restaurant Market Research AI System

A comprehensive AI-powered market research platform that generates professional investment-grade feasibility reports for restaurant businesses using multi-agent parallel research and LangGraph workflows.

## Overview

This system automates comprehensive market research for restaurant investments by leveraging specialized AI analysts that conduct parallel research across multiple data sources. It produces professional business feasibility reports with market analysis, financial projections, and risk assessment.

## Features

- **Dynamic Analyst Teams**: AI-generated specialized research analysts with unique roles and tool assignments
- **Parallel Research Engine**: Concurrent data gathering using multiple research tools and APIs
- **Professional Reporting**: Investment-grade business feasibility reports in multiple formats
- **LangGraph Workflows**: Robust state management with human-in-the-loop feedback
- **Multi-Tool Integration**: Tavily Search, Google Trends, OpenStreetMap, Google Maps APIs
- **Financial Modeling**: Complete financial projections and ROI analysis
- **Async Processing**: Non-blocking parallel research execution

## System Architecture

### Three-Graph Workflow

1. **Graph 1 - Analyst Team Creation**
   - Dynamic analyst generation based on business context
   - Human feedback integration
   - Tool assignment optimization

2. **Graph 2 - Parallel Research Engine** 
   - Concurrent tool execution using `Send()`
   - Data extraction and compression
   - Multi-source intelligence gathering

3. **Graph 3 - Report Compiler**
   - Professional report generation
   - Multiple export formats (Markdown, JSON)
   - Executive summaries and detailed analysis

## Project Structure

```
restaurant_research/
├── src/
│   ├── workflow/                 # Core LangGraph workflows
│   │   ├── analyst_team_creator.py    # Graph 1 - Team creation
│   │   ├── parallel_research_engine.py # Graph 2 - Parallel research
│   │   ├── report_compiler.py         # Graph 3 - Report generation
│   │   └── research_orchestrator.py   # Main orchestrator
│   ├── configuration/            # Configuration management
│   │   ├── configs.yaml          # Main configuration
│   │   ├── prompts.yaml          # AI prompts and templates
│   │   ├── config_loader.py      # Config loading utilities
│   │   └── prompts_loader.py     # Prompt management
│   ├── common/                   # Shared utilities
│   │   ├── model_loader.py       # LLM model initialization
│   │   └── tool_loader.py        # Research tool implementations
│   ├── graph_states/             # State definitions
│   │   └── states.py             # ResearchState and Analyst models
│   ├── utils/                    # Utility functions
│   │   ├── report_exporter.py    # Export functionality
│   │   └── create_unique_uuid.py # ID generation
│   └── logging_exception/        # Logging and error handling
│       ├── logging/logger.py     # Logging configuration
│       └── exception/custom_exception.py
├── notebook_experiments/         # Development notebooks
├── main.py                       # Entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables
└── configs.yaml                  # Application configuration
```


**Here are one-liners for all project files:**

## **ROOT LEVEL**
- `.env` → Environment variables for API keys and configurations
- `main.py` → Primary entry point for the restaurant research system
- `requirements.txt` → Python dependencies for the entire project
- `README.md` → Project documentation and setup instructions
- `api_tester.py` → Utility to test API endpoints and workflows

## **CONFIGURATION LAYER**
- `configs.yaml` → Central configuration defining business rules, tools, and LLM settings
- `prompts.yaml` → Expert knowledge base with specialized prompts for each workflow phase
- `config_loader.py` → Singleton service that loads and provides configuration access
- `prompts_loader.py` → Prompt template manager with versioning and validation

## **WORKFLOW ENGINE**
- `analyst_team_creator.py` → Generates specialized analyst teams using LLM with human feedback loop
- `parallel_research_engine.py` → Executes parallel research across multiple analysts with fault isolation
- `report_compiler.py` → Transforms research findings into professional multi-format business reports
- `research_orchestrator.py` → Master conductor coordinating the complete three-phase research pipeline

## **CORE INFRASTRUCTURE**
- `states.py` → Typed state definitions and custom reducers for LangGraph workflow management
- `model_loader.py` → Factory pattern for abstracting LLM provider selection and initialization
- `tool_loader.py` → Dynamic tool registry and execution manager for research operations
- `custom_exception.py` → Domain-specific exception hierarchy with structured error contexts
- `logger.py` → Structured logging implementation with different severity levels and formatting

## **UTILITIES & EXPORTS**
- `report_exporter.py` → Multi-format report exporter (JSON for machines, Markdown for humans)

## **DEPLOYMENT & OPERATIONS**
- `deploy.yml` → GitHub Actions workflow for automated deployment
- `infra.yml` → Infrastructure provisioning and management
- `eks-with-ecr.yaml` → EKS cluster configuration with ECR integration
- `deployment.yaml` → Kubernetes deployment manifests for container orchestration
- `service.yaml` → Kubernetes service definitions for network exposure

## **FRONTEND & UI**
- `index.html` → Web interface for user interaction and report visualization
- `style.css` → Styling for the web application interface

## **EXPERIMENTS & TESTING**
- Notebook files → Jupyter notebooks for prototyping and experimentation
- `test_model.py` → Unit tests for model loading and LLM interactions

## **LOGS & OUTPUTS**
- Log files → Timestamped execution logs for monitoring and debugging
- `execution_explanation/` → Detailed documentation of each workflow's execution sequence

## **THE COMPLETE STORY IN 4 LINES:**
```
configs.yaml → Defines WHAT to research (business rules & tools)
prompts.yaml → Defines HOW to research (expert knowledge encoded)
Three workflow files → Execute the research (team → research → report)
Orchestrator.py → Coordinates everything into a single API call
```

## **`1. analyst_team_creator.py` - Specialist Team Factory**

### **Class Level**
- `AnalystTeamCreator` → Orchestrates dynamic analyst team generation with human feedback loops

### **Initialization & Setup**
- `__init__()` → Loads configuration, models, prompts, and builds the LangGraph workflow
- `_build_graph()` → Constructs the state machine with three nodes and conditional feedback loop

### **Core Processing Functions**
- `_extract_json_array()` → Safely extracts JSON from LLM's messy output using multiple regex patterns
- `_validate_analyst_data()` → Validates and sanitizes individual analyst definitions against schema
- `load_dynamic_analysts()` → LangGraph node: Generates analyst team via LLM with context-aware prompting
- `human_feedback()` → LangGraph node: Presents team for human approval and collects improvement instructions
- `final_research_team()` → LangGraph node: Finalizes team composition with analytics and logging

### **Control Flow Functions**
- `route_feedback()` → Conditional router: Decides next step based on user acceptance and retry limits
- `create_team()` → Public API: Executes the complete team creation workflow with error handling

---

## **`2. parallel_research_engine.py` - Parallel Research Execution Engine**

### **Class Level**
- `ParallelResearchEngine` → Executes parallel research across multiple analysts with fault isolation

### **Initialization & Setup**
- `__init__()` → Configures research tools, loads LLM models, and builds parallel execution graph
- `_build_graph()` → Creates workflow with parallel Send operations for concurrent analyst research

### **Context & Parameter Builders**
- `_extract_location()` → Safely extracts location data from state with defensive validation
- `_build_tool_context()` → Constructs execution context with guaranteed field availability for each analyst
- `_build_tool_parameters()` → Generates tool-specific parameters from templates with error handling

### **Core Execution Functions**
- `_execute_single_tool()` → Executes individual tool with comprehensive error detection and status tracking
- `_process_research_findings()` → Aggregates successful tool outputs into concise summary without LLM calls
- `_build_analysis_context()` → Prepares context for LLM-based analysis generation with research data
- `_parse_analysis_output()` → Cleans and extracts insights from LLM analysis with robust pattern matching

### **Workflow Nodes**
- `create_research_tasks()` → LangGraph node: Transforms analyst team into executable research tasks
- `initiate_parallel_research()` → Conditional router: Creates parallel Send operations for each analyst
- `execute_single_analyst_research()` → LangGraph node: Executes complete research cycle for one analyst
- `compile_research_summary()` → LangGraph node: Aggregates all parallel results into comprehensive summary

### **Public API**
- `execute_research()` → Main entry point: Orchestrates complete parallel research execution

---

## **`3. report_compiler.py` - Professional Report Generation System**

### **Class Level**
- `ReportCompiler` → Transforms research findings into polished business reports with multi-format export

### **Initialization & Setup**
- `__init__()` → Loads report templates, section prompts, and builds linear compilation pipeline
- `_build_graph()` → Constructs sequential workflow for section-by-section report generation

### **Context Builders**
- `_get_location_context()` → Extracts location data with configuration fallbacks
- `_get_business_context()` → Gathers business parameters and research quality metrics
- `_build_research_context()` → Creates research confidence indicators and data quality scores

### **Content Processing**
- `_validate_section_content()` → Cleans and validates generated content for length and formatting
- `_compile_section_with_fallback()` → Core engine: Generates report sections with graceful degradation
- `_create_fallback_report()` → Creates minimal viable report when primary generation fails

### **Section Generators (Workflow Nodes)**
- `compile_executive_summary()` → Creates the high-level business case overview and recommendation
- `compile_market_analysis()` → Generates detailed market opportunity and competitive landscape
- `compile_financial_recommendations()` → Produces investment analysis and financial projections
- `compile_risk_assessment()` → Identifies and mitigates business risks with location-specific factors
- `compile_implementation_roadmap()` → Creates step-by-step launch plan with timelines and responsibilities
- `compile_conclusion()` → Provides final strategic recommendation and next steps
- `compile_final_report()` → Assembles all sections into professionally formatted final report

### **Export & Delivery**
- `save_all_reports()` → Exports reports in configured formats (JSON for machines, Markdown for humans)
- `display_export_summary()` → Presents export results and research metrics to user

### **Public API**
- `compile_reports()` → Main entry point: Executes complete report compilation and export pipeline

---

## **`4. research_orchestrator.py` - Master Pipeline Orchestrator**

### **Class Level**
- `RestaurantResearchSystem` → Top-level coordinator managing the complete three-phase research pipeline

### **Initialization & Setup**
- `__init__()` → Initializes all three workflow components with shared configuration
- `_build_initial_state()` → Creates initial ResearchState with user inputs and configuration defaults

### **Validation & Logging**
- `_validate_critical_parameters()` → Validates minimum viable inputs (concept, location) before execution
- `_log_research_parameters()` → Logs key research parameters for monitoring and debugging

### **Pipeline Execution**
- `run_research()` → Main public API: Executes complete three-phase pipeline with comprehensive error handling
- `run_default_research()` → Convenience method: Executes research using only configuration defaults

### **Standalone Execution**
- `main()` → Command-line entry point: Runs complete system with console output and result display


## Installation

### Prerequisites

- Python 3.9+
- API keys for:
  - Groq API
  - Tavily AI
  - SerpAPI (Google Trends & Maps)

### Quick Start

1. **Clone and setup environment:**
```bash
git clone https://github.com/gawaliashay/restaurant_market_research.git
cd restaurant_market_research
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Run the system:**
```bash
python main.py
```

## Configuration

### Environment Variables

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key  
SERPAPI_API_KEY=your_serpapi_api_key
REPORTS_DIRECTORY=./reports
```

### Core Configuration (configs.yaml)

```yaml
llm:
  primary_llm: groq             
  team_creator_llm: Mistral  
  research_llm: openai
  report_compiler_llm: groq

research:
  max_analysts: 4
  max_retries: 2
  tavily_max_results: 3

tools:
  tavily_search:
    name: "Tavily Search"
    description: "Web search for market research"
  google_trends:
    name: "Google Trends" 
    description: "Trend analysis and popularity data"
  google_maps:
    name: "Google Maps"
    description: "Nearby places and businesses"
```

## Usage

### Basic Execution

```python
from src.workflow.research_orchestrator import RestaurantResearchSystem
from src.graph_states.states import ResearchState

# Initialize the system
system = RestaurantResearchSystem()

# Create research state
research_state = ResearchState(
    restaurant_concept="Momo Specialty Restaurant",
    target_location="Warje, Pune, Maharashtra - 411058",
    investment="₹350,000",
    target_demographic="Professionals 25-45, health-conscious",
    max_analysts=4
)

# Execute complete research pipeline
result = system.run_research(research_state)
```

### Custom Business Case

```python
custom_state = ResearchState(
    restaurant_concept="Artisanal Coffee Shop",
    target_location="Koregaon Park, Pune",
    investment="₹500,000", 
    target_demographic="Young professionals, students, remote workers",
    special_note="Premium coffee experience, workspace-friendly",
    max_analysts=4
)
```

## Output Formats

### Generated Reports Include:

- **Executive Summary** - Investment overview and key recommendations
- **Market Analysis** - TAM/SAM analysis, competitive landscape, consumer insights
- **Financial Projections** - Revenue forecasts, ROI calculations, break-even analysis
- **Risk Assessment** - Strategic, operational, financial, and compliance risks
- **Implementation Roadmap** - Phased launch plan with timelines

### Export Formats:

- **Markdown** (`report.md`) - Professional formatted document
- **JSON** (`report.json`) - Structured data for integration

## API Integration

### Research Tools Available:

- **Tavily Search**: Web search and market intelligence
- **Google Trends**: Popularity and demand analysis  
- **Google Maps**: Competitor mapping and local business data


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Built with ❤️ for restaurant entrepreneurs and investors**