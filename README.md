# Restaurant Market Research AI System

A comprehensive AI-powered market research platform that generates professional investment-grade feasibility reports for restaurant businesses using multi-agent parallel research and LangGraph workflows.

## 🚀 Overview

This system automates comprehensive market research for restaurant investments by leveraging specialized AI analysts that conduct parallel research across multiple data sources. It produces professional business feasibility reports with market analysis, financial projections, and risk assessment.

## ✨ Features

- **🤖 Dynamic Analyst Teams**: AI-generated specialized research analysts with unique roles and tool assignments
- **🔍 Parallel Research Engine**: Concurrent data gathering using multiple research tools and APIs
- **📊 Professional Reporting**: Investment-grade business feasibility reports in multiple formats
- **🔄 LangGraph Workflows**: Robust state management with human-in-the-loop feedback
- **🔧 Multi-Tool Integration**: Tavily Search, Google Trends, OpenStreetMap, Google Maps APIs
- **📈 Financial Modeling**: Complete financial projections and ROI analysis
- **⚡ Async Processing**: Non-blocking parallel research execution

## 🏗️ System Architecture

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

## 📁 Project Structure

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

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- API keys for:
  - Groq API
  - Tavily AI
  - SerpAPI (Google Trends & Maps)
  - OpenStreetMap (free)

### Quick Start

1. **Clone and setup environment:**
```bash
git clone <repository-url>
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

## ⚙️ Configuration

### Environment Variables

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key  
SERPAPI_API_KEY=your_serpapi_api_key
DATA_PATH=./data/analysis
REPORTS_DIRECTORY=./reports
```

### Core Configuration (configs.yaml)

```yaml
llm:
  main_provider: "groq"
  main_model: "llama-3.3-70b-versatile"
  fast_model: "llama-3.1-8b-instant"

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
  openstreetmap:
    name: "OpenStreetMap"
    description: "Location data and coordinates"
  google_maps:
    name: "Google Maps"
    description: "Nearby places and businesses"
```

## 🚀 Usage

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

## 📊 Output Formats

### Generated Reports Include:

- **Executive Summary** - Investment overview and key recommendations
- **Market Analysis** - TAM/SAM analysis, competitive landscape, consumer insights
- **Financial Projections** - Revenue forecasts, ROI calculations, break-even analysis
- **Risk Assessment** - Strategic, operational, financial, and compliance risks
- **Implementation Roadmap** - Phased launch plan with timelines

### Export Formats:

- **Markdown** (`report.md`) - Professional formatted document
- **JSON** (`report.json`) - Structured data for integration

## 🔧 API Integration

### Research Tools Available:

- **Tavily Search**: Web search and market intelligence
- **Google Trends**: Popularity and demand analysis  
- **OpenStreetMap**: Location and geographic data
- **Google Maps**: Competitor mapping and local business data

### Adding Custom Tools:

```python
# In src/common/tool_loader.py
def use_custom_tool(state: Dict) -> Dict:
    """Custom research tool implementation"""
    return {
        "tool": "custom_tool",
        "data": custom_data,
        "status": "success"
    }

# Register in tool_loader
tool_loader["custom_tool"] = use_custom_tool
```

## 🎯 Example Output

The system generates comprehensive reports including:

```markdown
# RESTAURANT BUSINESS FEASIBILITY REPORT

## Executive Summary
Market analysis reveals 70% demand for healthy food options in target area...
Competitive landscape shows limited momo specialty restaurants...
Financial projections indicate 180% ROI with 7-month payback...

## Market Analysis  
- TAM: ₹1.2B, SAM: ₹60M
- 15% CAGR projected growth
- Direct competitors: Momos Junction (5% share), Momo Point (20% share)

## Financial Projections
- Year 1 Revenue: ₹4.2M
- EBITDA Margin: 15%
- Break-even: 7 months
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black src/ tests/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- 📧 Email: support@restaurantresearch.ai
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 📚 Documentation: [Project Wiki](https://github.com/your-repo/wiki)

## 🙏 Acknowledgments

- LangGraph team for the workflow framework
- Groq for high-performance LLM inference
- Tavily AI for web search capabilities
- OpenStreetMap community for geographic data

---

**Built with ❤️ for restaurant entrepreneurs and investors**