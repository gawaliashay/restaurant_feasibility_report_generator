import os, sys
from datetime import datetime
import uuid
from typing import TypedDict, Dict, Any, List, Optional
from pydantic import Field, BaseModel
import operator
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
import requests
import json
import re
from dotenv import load_dotenv
from langgraph.types import Send
from typing_extensions import Annotated

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException

from common.tool_loader import tool_loader
from src.common.model_loader import model_loader
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader


from src.utils.report_exporter import (
    save_json_generic,
    save_markdown_generic,
    save_docx_generic
)

load_dotenv()

# LLM clients - use smaller model for summarization tasks
llm = ChatGroq(model="openai/gpt-oss-safeguard-20b", temperature=1)
llm_fast = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)  # For summarization

# Models
class Analyst(BaseModel):
    role: str = Field(description="Role in the context of the restaurant_concept")
    affiliation: str = Field(description="Organisation the analyst belongs to")
    tools: List[str] = Field(description="Tools this analyst can use")
    description: str = Field(description="Responsibilities and focus areas")

class ResearchState(TypedDict, total=False):
    # Business Context Inputs
    restaurant_concept: str
    target_location: str
    investment: str
    target_demographic: str
    special_note: str
    
    # Analyst Generation Control
    max_analysts: int
    retry_count: int
    
    # Analyst Team Management
    dynamic_analysts: List[Analyst]
    analysts_team: List[Analyst]
    
    # Human Feedback System
    accept: bool
    extra_instructions: str
    
    # Research Execution State
    research_tasks: List[Dict]
    research_results: Dict[str, Any]
    research_summary: Dict[str, Any]
    current_task: Dict[str, Any]
    current_analyst: str
    
    # Report Compilation State
    executive_summary: str
    market_analysis: str
    financial_recommendations: str
    risk_assessment: str
    final_report: Dict[str, Any]
    export_paths: Dict[str, str]
    
    # NEW: Optimized data storage
    research_data_compressed: Dict[str, Any]

# Tools
tavily_search = TavilySearch(max_results=5)

def use_tavily_search(state: Dict) -> Dict:
    query = state.get("search_query", "")
    if not query: return {"error": "no search query"}
    try:
        results = tavily_search.invoke({"query": query})
        return {"tool": "tavily_search", "results": results, "sources_count": len(results)}
    except Exception as e:
        return {"error": f"tavily failed: {str(e)}"}

def use_google_trends(state: Dict) -> Dict:
    query = state.get("trend_query", "")
    if not query: return {"error": "no trend query"}
    return use_tavily_search({"search_query": f"trends popularity analysis {query} 2024"})

def use_openstreetmap(state: Dict) -> Dict:
    location = state.get("location", "").strip()
    if not location: return {"error": "no location"}
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": 1, "countrycodes": "in"},
            headers={"User-Agent": "ResearchApp/1.0"}, timeout=10
        )
        if response.status_code == 200 and response.json():
            place = response.json()[0]
            return {
                "tool": "openstreetmap", "location": location,
                "latitude": place.get("lat"), "longitude": place.get("lon"),
                "display_name": place.get("display_name"), "sources_count": 1
            }
        return use_tavily_search({"search_query": f"location information {location}"})
    except Exception:
        return use_tavily_search({"search_query": f"location {location}"})

def use_google_maps(state: Dict) -> Dict:
    location = state.get("location", "")
    query = state.get("query", "")
    search_term = location or query
    return use_tavily_search({"search_query": f"{search_term} nearby places restaurants businesses"})

# Analyst Generation (UNCHANGED)
DYNAMIC_ANALYSTS_PROMPT = ChatPromptTemplate.from_template(
"""
Generate EXACTLY {max_analysts} analysts for a restaurant research team.

BUSINESS CONTEXT:
- Restaurant Concept: {restaurant_concept}
- Location: {target_location}
- Investment: {investment}
- Target Demographic: {target_demographic}
- Special Note: {special_note}

RULES:
- Generate exactly {max_analysts} analysts.
- Each analyst must have a unique role.
- Tools allowed: ["tavily_search", "google_trends", "openstreetmap", "google_maps"].
- List 0–3 tools depending on necessity.
- Roles involving market research, location intelligence, competition analysis, or consumer insights MUST include at least ONE tool.
- Only roles that are strictly financial-modeling or qualitative reasoning MAY have an empty tool list.
- Do not add tools that are unnecessary for the role.
- No redundancy in roles.
- Keep roles practical for real-world market research.
- Output must be strict JSON only. No commentary.

OUTPUT FORMAT — return ONLY valid JSON array:
[
  {{
    "role": "Specific Role Name",
    "affiliation": "Credible Organization",
    "tools": ["optional_tool_1", "optional_tool_2"],
    "description": "Clear responsibilities"
  }}
]
"""
)

def _extract_json_array(text: str) -> Optional[str]:
    text = text.strip()
    code_block = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if code_block:
        return code_block.group(1).strip()
    json_match = re.search(r"(\[.*\])", text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    return None

def load_dynamic_analysts(state: ResearchState) -> Dict[str, List[Analyst]]:
    extra_note = state.get("extra_instructions", "") or ""
    prompt_text = DYNAMIC_ANALYSTS_PROMPT.format(
        max_analysts=state["max_analysts"],
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        investment=state["investment"],
        target_demographic=state["target_demographic"],
        special_note=(state.get("special_note", "") + " " + extra_note).strip(),
    )
    
    print(f"🤖 Generating {state['max_analysts']} analysts...")
    result = llm.invoke(prompt_text)
    raw = getattr(result, "content", "") or ""
    
    parsed_items = []
    json_candidate = _extract_json_array(raw)
    
    if json_candidate:
        try:
            parsed_items = json.loads(json_candidate)
        except json.JSONDecodeError:
            try:
                cleaned = json_candidate.replace("'", '"').replace("\\n", "").strip()
                parsed_items = json.loads(cleaned)
            except json.JSONDecodeError:
                parsed_items = []
    
    dynamic_analysts = []
    for item in parsed_items:
        if isinstance(item, dict):
            try:
                if all(k in item for k in ["role", "affiliation", "tools", "description"]):
                    analyst = Analyst(**item)
                    dynamic_analysts.append(analyst)
                    print(f"✅ Added analyst: {analyst.role}")
            except Exception as e:
                print(f"❌ Failed to create analyst from {item}: {e}")
    
    print(f"🎯 Total analysts created: {len(dynamic_analysts)}")
    return {"dynamic_analysts": dynamic_analysts}

def human_feedback(state: ResearchState) -> Dict[str, Any]:
    print("\nGenerated Dynamic Analysts:")
    for idx, analyst in enumerate(state.get("dynamic_analysts", []), 1):
        print(f"\n{idx}. {analyst.role}")
        print(f"   Affiliation: {analyst.affiliation}")
        print(f"   Tools: {', '.join(analyst.tools)}")
        print(f"   Description: {analyst.description}")
    
    try: user_input = input("\nAccept these Analysts? Enter 'y' for Yes or 'n' for No:  ").strip().lower()
    except: user_input = "n"
    
    if user_input == 'y': return {"accept": True}
    
    try: extra = input("Give Extra Instructions (or press Enter to skip): ").strip()
    except: extra = ""
    return {"accept": False, "extra_instructions": extra}

def final_research_team(state: ResearchState) -> Dict[str, List[Analyst]]:
    return {"analysts_team": list(state.get("dynamic_analysts", []))}

def route_feedback(state: ResearchState) -> str:
    if state.get("accept"): return "final_research_team"
    count = state.get("retry_count", 0) + 1
    state["retry_count"] = count
    return "final_research_team" if count >= 3 else "load_dynamic_analysts"

# Graph 1 Setup - Analyst Team Creation (UNCHANGED)
graph_1 = StateGraph(ResearchState)
graph_1.add_node("load_dynamic_analysts", load_dynamic_analysts)
graph_1.add_node("human_feedback", human_feedback)
graph_1.add_node("final_research_team", final_research_team)
graph_1.add_edge(START, "load_dynamic_analysts")
graph_1.add_edge("load_dynamic_analysts", "human_feedback")
graph_1.add_conditional_edges("human_feedback", route_feedback, {
    "final_research_team": "final_research_team",
    "load_dynamic_analysts": "load_dynamic_analysts",
})
graph_1.add_edge("final_research_team", END)
memory_1 = MemorySaver()
app_1 = graph_1.compile(checkpointer=memory_1)

# NEW: Research Data Compression Functions
def compress_research_data(research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only key insights, numbers, and actionable data from research"""
    compressed = {
        "key_numbers": [],
        "market_insights": [],
        "competitor_data": [],
        "financial_data": [],
        "risk_factors": [],
        "demographics": [],
        "timestamp": datetime.now().isoformat()
    }
    
    for analyst_role, findings in research_data.items():
        analysis = findings.get('expert_analysis', '')
        
        # Extract key numbers (prices, percentages, counts)
        numbers = re.findall(r'₹\s*[\d,]+|\d+\s*%|\d+\s*(?:L|Cr|months|years|km)', analysis)
        compressed["key_numbers"].extend(numbers)
        
        # Extract market insights
        if any(word in analysis.lower() for word in ['demand', 'trend', 'growth', 'opportunity']):
            market_points = re.findall(r'[^.]*demand[^.]*\.|[^.]*trend[^.]*\.|[^.]*growth[^.]*\.', analysis, re.IGNORECASE)
            compressed["market_insights"].extend(market_points)
        
        # Extract competitor data
        if any(word in analysis.lower() for word in ['competitor', 'competition', 'rival']):
            comp_points = re.findall(r'[^.]*competitor[^.]*\.|[^.]*competition[^.]*\.', analysis, re.IGNORECASE)
            compressed["competitor_data"].extend(comp_points)
        
        # Extract financial data
        if any(word in analysis.lower() for word in ['revenue', 'profit', 'investment', 'roi', 'margin']):
            financial_points = re.findall(r'[^.]*revenue[^.]*\.|[^.]*profit[^.]*\.|[^.]*investment[^.]*\.', analysis, re.IGNORECASE)
            compressed["financial_data"].extend(financial_points)
        
        # Extract risk factors
        if any(word in analysis.lower() for word in ['risk', 'challenge', 'threat']):
            risk_points = re.findall(r'[^.]*risk[^.]*\.|[^.]*challenge[^.]*\.|[^.]*threat[^.]*\.', analysis, re.IGNORECASE)
            compressed["risk_factors"].extend(risk_points)
        
        # Extract demographics
        if any(word in analysis.lower() for word in ['demographic', 'age', 'income', 'professional']):
            demo_points = re.findall(r'[^.]*demographic[^.]*\.|[^.]*age[^.]*\.|[^.]*income[^.]*\.', analysis, re.IGNORECASE)
            compressed["demographics"].extend(demo_points)
    
    # Remove duplicates and limit length
    for key in compressed:
        if isinstance(compressed[key], list):
            compressed[key] = list(set(compressed[key]))[:10]  # Keep top 10 unique items
    
    return compressed

def summarize_research_for_reports(compressed_data: Dict[str, Any]) -> str:
    """Create a concise summary for report generation"""
    summary_parts = []
    
    if compressed_data.get("key_numbers"):
        summary_parts.append(f"Key Numbers: {', '.join(compressed_data['key_numbers'][:5])}")
    
    if compressed_data.get("market_insights"):
        summary_parts.append(f"Market Insights: {'; '.join(compressed_data['market_insights'][:3])}")
    
    if compressed_data.get("competitor_data"):
        summary_parts.append(f"Competition: {'; '.join(compressed_data['competitor_data'][:2])}")
    
    if compressed_data.get("financial_data"):
        summary_parts.append(f"Financial: {'; '.join(compressed_data['financial_data'][:3])}")
    
    if compressed_data.get("risk_factors"):
        summary_parts.append(f"Risks: {'; '.join(compressed_data['risk_factors'][:3])}")
    
    return " | ".join(summary_parts)

# Graph 2 - OPTIMIZED Parallel Research
RESEARCH_PROMPT = ChatPromptTemplate.from_template("""
You are {analyst_role}, a {affiliation} analyst specializing in {description}.
Analyze: {restaurant_concept} in {target_location}, Investment: {investment}, Target: {target_demographic}, Note: {special_note}
Provide concrete, data-driven recommendations.
""")

def create_research_tasks(state: ResearchState) -> Dict[str, Any]:
    research_tasks = []
    for analyst in state.get("analysts_team", []):
        task = {
            "analyst_role": analyst.role, "affiliation": analyst.affiliation,
            "description": analyst.description, "tools": analyst.tools,
            "prompt": RESEARCH_PROMPT.format(
                analyst_role=analyst.role, affiliation=analyst.affiliation,
                description=analyst.description, restaurant_concept=state["restaurant_concept"],
                target_location=state["target_location"], investment=state["investment"],
                target_demographic=state["target_demographic"], special_note=state.get("special_note", "")
            )
        }
        research_tasks.append(task)
        print(f"📋 Created research task for: {analyst.role}")
    return {"research_tasks": research_tasks, "research_results": {}}

def initiate_parallel_research(state: ResearchState):
    """🔥 Dynamic Send() to launch all analysts in parallel"""
    research_tasks = state.get("research_tasks", [])
    
    if not research_tasks:
        return END
    
    print(f"🚀 Launching parallel research for {len(research_tasks)} analysts...")
    
    return [
        Send(
            "execute_single_analyst_research",
            {
                "current_task": task,
                "current_analyst": task["analyst_role"],
                "restaurant_concept": state["restaurant_concept"],
                "target_location": state["target_location"],
                "investment": state["investment"],
                "target_demographic": state["target_demographic"],
                "special_note": state.get("special_note", "")
            }
        )
        for task in research_tasks
    ]

def execute_single_analyst_research(state: ResearchState) -> Dict[str, Any]:
    """Process ONE analyst with OPTIMIZED analysis + insights in one call"""
    current_task = state.get("current_task")
    
    if not current_task:
        return {}
    
    analyst_role, tools = current_task["analyst_role"], current_task["tools"]
    print(f"\n🔍 Conducting research for: {analyst_role}")
    print(f"   Tools: {', '.join(tools)}")
    
    research_query = f"{analyst_role} analysis: {state['restaurant_concept']} in {state['target_location']}"
    
    research_findings = []
    
    for tool_name in tools:
        try:
            if tool_name == "tavily_search":
                result = use_tavily_search({"search_query": research_query})
            elif tool_name == "google_trends":
                result = use_google_trends({"trend_query": f"{state['restaurant_concept']} {state['target_location']}"})
            elif tool_name == "openstreetmap":
                result = use_openstreetmap({"location": state["target_location"]})
            elif tool_name == "google_maps":
                result = use_google_maps({"location": state["target_location"], "query": f"{state['restaurant_concept']} restaurants"})
            else:
                result = use_tavily_search({"search_query": research_query})
            
            status = "success" if "error" not in result else "error"
            research_findings.append({"tool": tool_name, "data": result, "status": status})
        except Exception as e:
            research_findings.append({"tool": tool_name, "data": {"error": str(e)}, "status": "failed"})
    
    # OPTIMIZED: Combine analysis + insights in one prompt
    analysis_prompt = f"""As {analyst_role} from {current_task['affiliation']}, provide expert analysis with key insights:

SPECIALIZATION: {current_task['description']}
BUSINESS: {state['restaurant_concept']} in {state['target_location']}, Investment: {state['investment']}, Target: {state['target_demographic']}
RESEARCH FINDINGS: {research_findings}

Provide:
1. Specific, actionable recommendations with concrete numbers and data
2. Top 3 key insights from your analysis
3. Most important market data points

Format your response as:
ANALYSIS: [your detailed analysis]
KEY_INSIGHTS: [3 bullet points with specific numbers]
DATA_POINTS: [key statistics and figures]"""
    
    try:
        analysis_result = llm.invoke(analysis_prompt)
        analysis_content = getattr(analysis_result, "content", "Analysis unavailable")
        
        # Parse the structured response
        analysis_text = ""
        key_insights = []
        data_points = []
        
        if "ANALYSIS:" in analysis_content:
            parts = analysis_content.split("KEY_INSIGHTS:")
            analysis_text = parts[0].replace("ANALYSIS:", "").strip()
            if len(parts) > 1:
                insights_part = parts[1].split("DATA_POINTS:")[0] if "DATA_POINTS:" in parts[1] else parts[1]
                key_insights = [insight.strip() for insight in insights_part.split('\n') if insight.strip() and insight.strip().startswith('-')]
        else:
            analysis_text = analysis_content
        
    except Exception as e:
        analysis_text = f"Analysis generation failed: {str(e)}"
        key_insights = ["Analysis generation failed"]
    
    research_result = {
        "analyst_role": analyst_role, "affiliation": current_task["affiliation"],
        "specialization": current_task["description"], "tools_used": [f["tool"] for f in research_findings],
        "research_data": research_findings, "expert_analysis": analysis_text,
        "key_insights": key_insights[:3],  # Store insights directly
        "timestamp": datetime.now().isoformat(),
        "successful_tools": len([f for f in research_findings if f["status"] == "success"])
    }
    
    print(f"✅ Completed research for: {analyst_role}")
    print(f"   Successful tools: {research_result['successful_tools']}/{len(tools)}")
    
    return {
        "research_results": {analyst_role: research_result},
        "current_analyst": analyst_role
    }

def compile_research_summary(state: ResearchState) -> Dict[str, Any]:
    research_results = state.get("research_results", {})
    print("\n" + "="*60)
    print("📊 PARALLEL RESEARCH COMPLETED - SUMMARY")
    print("="*60)
    
    # NEW: Compress research data for report generation
    compressed_data = compress_research_data(research_results)
    research_summary_text = summarize_research_for_reports(compressed_data)
    
    # Collect insights from individual analyses (already generated)
    all_insights = []
    for analyst_role, findings in research_results.items():
        all_insights.extend(findings.get('key_insights', []))
    
    summary = {
        "total_analysts": len(research_results),
        "research_completed": datetime.now().isoformat(),
        "business_context": {
            "concept": state["restaurant_concept"], "location": state["target_location"],
            "investment": state["investment"], "target_demographic": state["target_demographic"]
        },
        "analyst_findings": research_results, 
        "key_insights": all_insights[:5],  # Use pre-generated insights
        "compressed_data": compressed_data,  # NEW: Store compressed data
        "research_summary_text": research_summary_text  # NEW: Store summary text
    }
    
    print(f"\n🏆 RESEARCH SUMMARY")
    print(f"Total Analysts: {len(research_results)}")
    for analyst_role, findings in research_results.items():
        print(f"\n🎯 {analyst_role}")
        print(f"   Tools Used: {', '.join(findings['tools_used'])}")
        print(f"   Analysis: {findings['expert_analysis'][:150]}...")
    print(f"\n🔑 KEY INSIGHTS:")
    for i, insight in enumerate(summary["key_insights"][:5], 1):
        print(f"   {i}. {insight}")
    
    return {"research_summary": summary}

# Graph 2 Setup with Dynamic Send()
graph_2 = StateGraph(ResearchState)
graph_2.add_node("create_research_tasks", create_research_tasks)
graph_2.add_node("execute_single_analyst_research", execute_single_analyst_research)
graph_2.add_node("compile_research_summary", compile_research_summary)

graph_2.add_edge(START, "create_research_tasks")
graph_2.add_conditional_edges("create_research_tasks", initiate_parallel_research, {
    "execute_single_analyst_research": "execute_single_analyst_research",
    END: END
})
graph_2.add_edge("execute_single_analyst_research", "compile_research_summary")
graph_2.add_edge("compile_research_summary", END)

memory_2 = MemorySaver()
app_2 = graph_2.compile(checkpointer=memory_2)

# Graph 3 - OPTIMIZED Report Compilation & Export
PROMPTS = {
    "executive_summary": ChatPromptTemplate.from_template("""
Create investor-ready executive summary for {restaurant_concept} in {target_location}.

Investment: {investment}, Target: {target_demographic}
Research Summary: {research_summary}

Include: Market opportunity, competitive advantage, financial potential, 3 key success factors, and immediate next steps. Use professional tone with specific numbers.

IMPORTANT: Be concise and focus on key data points. Use tables and bullet points for clarity."""),
    
    "market_analysis": ChatPromptTemplate.from_template("""
Market analysis for {restaurant_concept} in {target_location}. Target: {target_demographic}

Research Summary: {research_summary}

Sections:
1. Target Market - demographics, spending power
2. Competition - direct competitors, market gaps  
3. Trends - consumer behavior, local opportunities
4. Strategy - positioning and differentiation

Provide data-driven insights with specific numbers. Use tables where appropriate."""),
    
    "financial": ChatPromptTemplate.from_template("""
Financial plan for {investment} investment.

Research Summary: {research_summary}

Cover:
- Budget allocation (setup, operations, marketing, contingency)
- Revenue projections (realistic sales forecasts)
- Key metrics (ROI, break-even, payback period)
- Cost management strategies

Use conservative estimates with specific numbers in tables."""),
    
    "risk": ChatPromptTemplate.from_template("""
Risk assessment for {restaurant_concept} in {target_location}.

Research Summary: {research_summary}

Categories:
- Market risks (competition, demand)
- Operational risks (staffing, supply chain) 
- Financial risks (cash flow, costs)
- Location risks (visibility, regulations)

Include practical mitigation strategies in table format."""),
}

def compile_executive_summary(state: ResearchState) -> Dict[str, Any]:
    print("📝 Compiling Executive Summary...")
    
    # Use compressed research data instead of full research data
    research_summary = state.get("research_summary", {})
    compressed_data = research_summary.get("research_summary_text", "No research data available")
    
    prompt = PROMPTS["executive_summary"].format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        investment=state["investment"],
        target_demographic=state["target_demographic"],
        research_summary=compressed_data  # Use compressed data
    )
    
    try:
        result = llm.invoke(prompt)
        return {"executive_summary": getattr(result, "content", "Executive summary unavailable")}
    except Exception as e:
        print(f"⚠️  Executive summary failed, using fallback: {e}")
        return {"executive_summary": f"Executive Summary for {state['restaurant_concept']} in {state['target_location']}. Investment: {state['investment']}. Target: {state['target_demographic']}."}

def compile_market_analysis(state: ResearchState) -> Dict[str, Any]:
    print("📊 Compiling Market Analysis...")
    
    research_summary = state.get("research_summary", {})
    compressed_data = research_summary.get("research_summary_text", "No research data available")
    
    prompt = PROMPTS["market_analysis"].format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        target_demographic=state["target_demographic"],
        research_summary=compressed_data  # Use compressed data
    )
    
    try:
        result = llm.invoke(prompt)
        return {"market_analysis": getattr(result, "content", "Market analysis unavailable")}
    except Exception as e:
        print(f"⚠️  Market analysis failed, using fallback: {e}")
        return {"market_analysis": "Market analysis unavailable due to technical issues."}

def compile_financial_recommendations(state: ResearchState) -> Dict[str, Any]:
    print("💰 Compiling Financial Recommendations...")
    
    research_summary = state.get("research_summary", {})
    compressed_data = research_summary.get("research_summary_text", "No research data available")
    
    prompt = PROMPTS["financial"].format(
        investment=state["investment"],
        research_summary=compressed_data  # Use compressed data
    )
    
    try:
        result = llm.invoke(prompt)
        return {"financial_recommendations": getattr(result, "content", "Financial recommendations unavailable")}
    except Exception as e:
        print(f"⚠️  Financial recommendations failed, using fallback: {e}")
        return {"financial_recommendations": "Financial recommendations unavailable due to technical issues."}

def compile_risk_assessment(state: ResearchState) -> Dict[str, Any]:
    print("⚠️  Compiling Risk Assessment...")
    
    research_summary = state.get("research_summary", {})
    compressed_data = research_summary.get("research_summary_text", "No research data available")
    
    prompt = PROMPTS["risk"].format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        research_summary=compressed_data  # Use compressed data
    )
    
    try:
        result = llm.invoke(prompt)
        return {"risk_assessment": getattr(result, "content", "Risk assessment unavailable")}
    except Exception as e:
        print(f"⚠️  Risk assessment failed, using fallback: {e}")
        return {"risk_assessment": "Risk assessment unavailable due to technical issues."}

# NEW: Template-based final report assembly (replaces LLM call)
def compile_final_report(state: ResearchState) -> Dict[str, Any]:
    print("📄 Compiling Final Report...")
    
    # Template-based assembly instead of LLM call
    executive = state.get("executive_summary", "")
    market = state.get("market_analysis", "")
    financial = state.get("financial_recommendations", "")
    risk = state.get("risk_assessment", "")
    
    # Create structured final report using templates
    final_content = f"""# Business Plan: {state['restaurant_concept']}

## Strategic Recommendations & 30/60/90-Day Roadmap

### Executive Summary
{executive}

### Market Analysis  
{market}

### Financial Recommendations
{financial}

### Risk Assessment
{risk}

### Complete Business Plan Integration

This comprehensive business plan integrates market analysis, financial projections, and risk assessment to provide a complete roadmap for {state['restaurant_concept']} in {state['target_location']}.

**Key Integration Points:**
- Market opportunities identified in the analysis are supported by financial projections
- Risk mitigation strategies align with operational and financial planning
- The 30/60/90-day action plan executes the strategic recommendations

**Next Steps:**
1. Review executive summary for high-level overview
2. Examine market analysis for target demographic insights  
3. Study financial recommendations for investment requirements
4. Consult risk assessment for mitigation strategies
5. Implement the integrated action plan for successful launch

*Report generated: {datetime.now().strftime('%Y-%m-%d at %H:%M')}*
"""
    
    structured_report = {
        "business_overview": f"""**Business Concept:** {state["restaurant_concept"]}  
**Location:** {state["target_location"]}  
**Investment:** {state["investment"]}  
**Target Demographic:** {state["target_demographic"]}  
**Special Focus:** {state.get("special_note", "N/A")}""",
        
        "executive_summary": executive,
        "market_analysis": market,
        "financial_recommendations": financial,
        "risk_assessment": risk,
        "complete_business_plan": final_content,
        
        "research_metadata": f"""**Report Generated:** {datetime.now().strftime('%Y-%m-%d at %H:%M')}  
**Analysts Contributing:** {len(state.get("analysts_team", []))}  
**Research Sources:** {len(state.get("research_results", {}))}  
**Analyst Team:** {', '.join([a.role for a in state.get("analysts_team", [])])}"""
    }
    
    return {"final_report": structured_report}

def save_all_reports(state):
    report = state.get("final_report", {})
    if not report:
        return {"export_paths": state.get("export_paths", {})}

    export_paths = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        json_path = f"final_report_{timestamp}.json"
        export_paths["json"] = save_json_generic(report, json_path)
        print(f"✅ JSON saved: {json_path}")
    except Exception as e:
        print("❌ JSON save failed:", e)
    
    try:
        md_path = f"final_report_{timestamp}.md"
        export_paths["md"] = save_markdown_generic(report, md_path)
        print(f"✅ Markdown saved: {md_path}")
    except Exception as e:
        print("❌ MD save failed:", e)
    
    try:
        docx_path = f"final_report_{timestamp}.docx"
        export_paths["docx"] = save_docx_generic(report, docx_path)
        print(f"✅ DOCX saved: {docx_path}")
    except Exception as e:
        print("❌ DOCX save failed:", e)

    return {"export_paths": export_paths}

def display_export_summary(state: ResearchState) -> Dict[str, Any]:
    export_paths = state.get("export_paths", {})
    print("\n" + "="*60)
    print("📁 EXPORT SUMMARY")
    print("="*60)
    for format_name, filepath in export_paths.items():
        print(f"✅ {format_name.upper()}: {filepath}")
    print("="*60)
    return {}

# Graph 3 Setup
graph_3 = StateGraph(ResearchState)
graph_3.add_node("compile_executive_summary", compile_executive_summary)
graph_3.add_node("compile_market_analysis", compile_market_analysis)
graph_3.add_node("compile_financial_recommendations", compile_financial_recommendations)
graph_3.add_node("compile_risk_assessment", compile_risk_assessment)
graph_3.add_node("compile_final_report", compile_final_report)
graph_3.add_node("display_export_summary", display_export_summary)
graph_3.add_node("save_all_reports", save_all_reports)

graph_3.add_edge(START, "compile_executive_summary")
graph_3.add_edge("compile_executive_summary", "compile_market_analysis")
graph_3.add_edge("compile_market_analysis", "compile_financial_recommendations")
graph_3.add_edge("compile_financial_recommendations", "compile_risk_assessment")
graph_3.add_edge("compile_risk_assessment", "compile_final_report")
graph_3.add_edge("compile_final_report", "save_all_reports")
graph_3.add_edge("save_all_reports", "display_export_summary")
graph_3.add_edge("display_export_summary", END)

memory_3 = MemorySaver()
app_3 = graph_3.compile(checkpointer=memory_3)

# Main Execution
def main():
    initial_state = {
        "restaurant_concept": "Setup momo speciality Restaurant",
        "target_location": "Sneha Paradise-A, Warje-Malwadi, Pune, Maharashtra - 411058",
        "investment": "₹350,000", "target_demographic": "Professionals 25-45, health-conscious",
        "special_note": "momo demand, spending power, competition density", "max_analysts": 1, "retry_count": 0
    }
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    print("🔧 RUNNING GRAPH_1 - ANALYST TEAM CREATION")
    graph_1_result = app_1.invoke(initial_state, config=config)
    
    if graph_1_result.get("analysts_team"):
        print("\n\n🔧 RUNNING GRAPH_2 - PARALLEL RESEARCH")
        graph_2_state = {
            **initial_state,
            "analysts_team": graph_1_result["analysts_team"],
            "research_tasks": [],
            "research_results": {},
            "research_summary": {}
        }
        graph_2_result = app_2.invoke(graph_2_state, config)
        
        print("\n\n🔧 RUNNING GRAPH_3 - REPORT COMPILATION & EXPORT")
        graph_3_state = {
            **graph_2_result,
            "executive_summary": "",
            "market_analysis": "",
            "financial_recommendations": "",
            "risk_assessment": "",
            "final_report": {},
            "export_paths": {}
        }
        graph_3_result = app_3.invoke(graph_3_state, config)
        
        print("\n🎉 COMPLETE PIPELINE FINISHED!")
        export_paths = graph_3_result.get("export_paths", {})
        for format_name, filepath in export_paths.items():
            print(f"   • {format_name.upper()}: {filepath}")
    else:
        print("❌ No analysts generated")

if __name__ == "__main__":
    main()