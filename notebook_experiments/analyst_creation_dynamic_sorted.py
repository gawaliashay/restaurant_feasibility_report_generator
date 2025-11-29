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

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException

load_dotenv()

# LLM client (kept as originally configured)

# llm = ChatGroq(model="llama-3.1-8b-instant", temperature=1)
# llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=1)
# llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct", temperature=1)
llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=1)

# Models
class Analyst(BaseModel):
    role: str = Field(description="Role in the context of the restaurant_concept")
    affiliation: str = Field(description="Organisation the analyst belongs to")
    tools: List[str] = Field(description="Tools this analyst can use")
    description: str = Field(description="Responsibilities and focus areas")

from typing import TypedDict, Dict, Any, List, Optional

# =============================================================================
# RESEARCH STATE - COMPLETE PIPELINE DATA MODEL
# =============================================================================

class ResearchState(TypedDict, total=False):
    # =========================================================================
    # GRAPH 1: ANALYST TEAM CREATION STATE
    # =========================================================================
    
    # Business Context Inputs (User Provided)
    restaurant_concept: str           # Core business idea - used for analyst specialization
    target_location: str              # Geographic focus - used for location-specific analysis
    investment: str                   # Budget constraints - used for financial planning
    target_demographic: str           # Customer profile - used for market targeting
    special_note: str                 # Additional requirements - used for custom analysis
    
    # Analyst Generation Control
    max_analysts: int                 # Limits analyst count - used for resource allocation
    retry_count: int                  # Tracks regeneration attempts - used for loop control
    
    # Analyst Team Management
    dynamic_analysts: List[Analyst]   # Generated analysts - used for human review
    analysts_team: List[Analyst]      # Final approved team - used for research assignment
    
    # Human Feedback System
    accept: bool                      # User approval status - used for conditional routing
    extra_instructions: str           # User feedback - used for analyst regeneration
    
    # =========================================================================
    # GRAPH 2: PARALLEL RESEARCH EXECUTION STATE  
    # =========================================================================
    
    # Research Task Management
    research_tasks: List[Dict]        # Individual analyst assignments - used for parallel processing
    completed_analysts: List[str]     # Track progress - used for conditional looping
    current_analyst: str              # Active analyst - used for progress tracking
    
    # Research Data Collection
    research_results: Dict[str, Any]  # Raw findings per analyst - used for data aggregation
    research_summary: Dict[str, Any]  # Consolidated insights - used for report generation
    
    # =========================================================================
    # GRAPH 3: REPORT COMPILATION & EXPORT STATE
    # =========================================================================
    
    # Report Section Storage
    executive_summary: str            # Business overview - used for investor presentations
    market_analysis: str              # Industry insights - used for strategic planning  
    financial_recommendations: str    # Budget guidance - used for financial planning
    risk_assessment: str              # Threat analysis - used for risk mitigation
    
    # Final Output Assembly
    final_report: Dict[str, Any]      # Complete business plan - used for decision making
    
    # Multi-Format Export Tracking
    export_paths: Dict[str, str]      # File locations - used for output management
    

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

# Fix the DYNAMIC_ANALYSTS_PROMPT - make it more explicit
DYNAMIC_ANALYSTS_PROMPT = ChatPromptTemplate.from_template("""
Generate EXACTLY {max_analysts} new analysts for a restaurant research team. 

BUSINESS CONTEXT:
- Restaurant Concept: {restaurant_concept}
- Location: {target_location}
- Investment: {investment}
- Target Demographic: {target_demographic}
- Special Note: {special_note}

RULES:
- Generate exactly {max_analysts} analysts
- Each analyst must have unique role
- Each analyst must use exactly ONE tool from: ["tavily_search", "google_trends", "openstreetmap", "google_maps"]
- Make them practical for market research

OUTPUT FORMAT - Return ONLY valid JSON array:
[
  {{
    "role": "Specific Role Name",
    "affiliation": "Credible Organization", 
    "tools": ["one_tool_name"],
    "description": "Clear responsibilities"
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text.
""")

# Fix the JSON extraction function
def _extract_json_array(text: str) -> Optional[str]:
    text = text.strip()
    
    # Try to find JSON array in code blocks first
    code_block = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if code_block:
        return code_block.group(1).strip()
    
    # Try to find bare JSON array
    json_match = re.search(r"(\[.*\])", text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    
    return None

# Add debug logging to load_dynamic_analysts
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
    
    print(f"📄 Raw LLM response: {raw[:200]}...")  # Debug
    
    parsed_items = []
    json_candidate = _extract_json_array(raw)
    
    if json_candidate:
        print(f"🔍 Found JSON candidate: {json_candidate[:100]}...")  # Debug
        try:
            parsed_items = json.loads(json_candidate)
            print(f"✅ Successfully parsed {len(parsed_items)} items")  # Debug
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")  # Debug
            # Try with cleaned version
            try:
                cleaned = json_candidate.replace("'", '"').replace("\\n", "").strip()
                parsed_items = json.loads(cleaned)
                print(f"✅ Successfully parsed cleaned JSON: {len(parsed_items)} items")
            except json.JSONDecodeError as e2:
                print(f"❌ Cleaned JSON also failed: {e2}")
                parsed_items = []
    else:
        print("❌ No JSON array found in response")  # Debug
    
    dynamic_analysts = []
    for item in parsed_items:
        if isinstance(item, dict):
            try:
                # Validate required fields
                if all(k in item for k in ["role", "affiliation", "tools", "description"]):
                    analyst = Analyst(**item)
                    dynamic_analysts.append(analyst)
                    print(f"✅ Added analyst: {analyst.role}")
                else:
                    print(f"❌ Missing fields in: {item}")
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

# Graph 1 Setup
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

# Graph 2 - Parallel Research
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
    return {"research_tasks": research_tasks, "research_results": {}, "completed_analysts": []}

def execute_analyst_research(state: ResearchState) -> Dict[str, Any]:
    research_tasks = state.get("research_tasks", [])
    research_results = state.get("research_results", {})
    completed_analysts = state.get("completed_analysts", [])
    
    current_task = None
    for task in research_tasks:
        if task["analyst_role"] not in completed_analysts:
            current_task = task
            break
    if not current_task: return {}
    
    analyst_role, tools = current_task["analyst_role"], current_task["tools"]
    print(f"\n🔍 Conducting research for: {analyst_role}")
    print(f"   Tools: {', '.join(tools)}")
    
    research_findings = []
    research_query = f"{analyst_role} analysis: {state['restaurant_concept']} in {state['target_location']}"
    
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
    
    analysis_prompt = f"""As {analyst_role} from {current_task['affiliation']}, provide expert analysis:
SPECIALIZATION: {current_task['description']}
BUSINESS: {state['restaurant_concept']} in {state['target_location']}, Investment: {state['investment']}, Target: {state['target_demographic']}
RESEARCH FINDINGS: {research_findings}
Provide specific, actionable recommendations."""
    
    try:
        analysis_result = llm.invoke(analysis_prompt)
        analysis_text = getattr(analysis_result, "content", "Analysis unavailable")
    except Exception as e:
        analysis_text = f"Analysis generation failed: {str(e)}"
    
    research_result = {
        "analyst_role": analyst_role, "affiliation": current_task["affiliation"],
        "specialization": current_task["description"], "tools_used": [f["tool"] for f in research_findings],
        "research_data": research_findings, "expert_analysis": analysis_text,
        "timestamp": datetime.now().isoformat(),
        "successful_tools": len([f for f in research_findings if f["status"] == "success"])
    }
    
    print(f"✅ Completed research for: {analyst_role}")
    print(f"   Successful tools: {research_result['successful_tools']}/{len(tools)}")
    
    updated_results = research_results.copy()
    updated_results[analyst_role] = research_result
    return {
        "research_results": updated_results,
        "completed_analysts": completed_analysts + [analyst_role],
        "current_analyst": analyst_role
    }

def should_continue_research(state: ResearchState) -> str:
    research_tasks = state.get("research_tasks", [])
    completed_analysts = state.get("completed_analysts", [])
    total_analysts = {task["analyst_role"] for task in research_tasks}
    return "complete" if len(completed_analysts) >= len(total_analysts) else "continue"

def compile_research_summary(state: ResearchState) -> Dict[str, Any]:
    research_results = state.get("research_results", {})
    print("\n" + "="*60)
    print("📊 PARALLEL RESEARCH COMPLETED - SUMMARY")
    print("="*60)
    
    summary = {
        "total_analysts": len(research_results),
        "research_completed": datetime.now().isoformat(),
        "business_context": {
            "concept": state["restaurant_concept"], "location": state["target_location"],
            "investment": state["investment"], "target_demographic": state["target_demographic"]
        },
        "analyst_findings": research_results, "key_insights": []
    }
    
    insights_prompt = f"""Based on research findings, extract top 5 key insights:
Concept: {state['restaurant_concept']}, Location: {state['target_location']}, Investment: {state['investment']}
Findings: {research_results}
Provide 5 concise, actionable insights."""
    
    try:
        insights_result = llm.invoke(insights_prompt)
        key_insights = getattr(insights_result, "content", "").split('\n')
        summary["key_insights"] = [insight.strip() for insight in key_insights if insight.strip() and not insight.strip().startswith('**')]
    except Exception as e:
        summary["key_insights"] = [f"Insights generation failed: {str(e)}"]
    
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

# Graph 2 Setup
graph_2 = StateGraph(ResearchState)
graph_2.add_node("create_research_tasks", create_research_tasks)
graph_2.add_node("execute_analyst_research", execute_analyst_research)
graph_2.add_node("compile_research_summary", compile_research_summary)

graph_2.add_edge(START, "create_research_tasks")
graph_2.add_edge("create_research_tasks", "execute_analyst_research")
graph_2.add_conditional_edges("execute_analyst_research", should_continue_research, {
    "continue": "execute_analyst_research", "complete": "compile_research_summary"
})
graph_2.add_edge("compile_research_summary", END)
memory_2 = MemorySaver()
app_2 = graph_2.compile(checkpointer=memory_2)

# Graph 3 - Report Compilation & Export
from docx import Document

PROMPTS = {
    "executive_summary": ChatPromptTemplate.from_template("""
Create executive summary for: {restaurant_concept} in {target_location}, Investment: {investment}, Target: {target_demographic}
Research: {research_summary}
Write 150-200 word summary highlighting key opportunity and next steps."""),
    
    "market_analysis": ChatPromptTemplate.from_template("""
Compile market analysis for: {restaurant_concept} in {target_location}, Target: {target_demographic}
Findings: {research_results}
Cover: target market, competition, trends, customer behavior."""),
    
    "financial": ChatPromptTemplate.from_template("""
Provide financial recommendations for: Investment: {investment}
Insights: {research_summary}
Cover: budget allocation, revenue projections, cost management, ROI."""),
    
    "risk": ChatPromptTemplate.from_template("""
Identify risks for: {restaurant_concept} in {target_location}
Data: {research_summary}
Cover: market, operational, financial, location-specific risks with mitigation."""),
    
    "final": ChatPromptTemplate.from_template("""
Compile complete business report:
Executive: {executive_summary}
Market: {market_analysis}
Financial: {financial_recommendations}
Risk: {risk_assessment}
Create structured report with actionable recommendations.""")
}

def compile_executive_summary(state: ResearchState) -> Dict[str, Any]:
    print("📝 Compiling Executive Summary...")
    prompt = PROMPTS["executive_summary"].format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        investment=state["investment"],
        target_demographic=state["target_demographic"],
        research_summary=state.get("research_summary", {})
    )
    result = llm.invoke(prompt)
    return {"executive_summary": getattr(result, "content", "Executive summary unavailable")}

def compile_market_analysis(state: ResearchState) -> Dict[str, Any]:
    print("📊 Compiling Market Analysis...")
    prompt = PROMPTS["market_analysis"].format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        target_demographic=state["target_demographic"],
        research_results=state.get("research_results", {})
    )
    result = llm.invoke(prompt)
    return {"market_analysis": getattr(result, "content", "Market analysis unavailable")}

def compile_financial_recommendations(state: ResearchState) -> Dict[str, Any]:
    print("💰 Compiling Financial Recommendations...")
    prompt = PROMPTS["financial"].format(
        investment=state["investment"],
        research_summary=state.get("research_summary", {})
    )
    result = llm.invoke(prompt)
    return {"financial_recommendations": getattr(result, "content", "Financial recommendations unavailable")}

def compile_risk_assessment(state: ResearchState) -> Dict[str, Any]:
    print("⚠️  Compiling Risk Assessment...")
    prompt = PROMPTS["risk"].format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        research_summary=state.get("research_summary", {})
    )
    result = llm.invoke(prompt)
    return {"risk_assessment": getattr(result, "content", "Risk assessment unavailable")}

def compile_final_report(state: ResearchState) -> Dict[str, Any]:
    print("📄 Compiling Final Report...")
    prompt = PROMPTS["final"].format(
        executive_summary=state.get("executive_summary", ""),
        market_analysis=state.get("market_analysis", ""),
        financial_recommendations=state.get("financial_recommendations", ""),
        risk_assessment=state.get("risk_assessment", "")
    )
    result = llm.invoke(prompt)
    final_content = getattr(result, "content", "Final report unavailable")
    
    structured_report = {
        "business_concept": state["restaurant_concept"], "location": state["target_location"],
        "investment": state["investment"], "target_demographic": state["target_demographic"],
        "special_note": state.get("special_note", ""), "executive_summary": state.get("executive_summary", ""),
        "market_analysis": state.get("market_analysis", ""), "financial_recommendations": state.get("financial_recommendations", ""),
        "risk_assessment": state.get("risk_assessment", ""), "complete_report": final_content,
        "generated_at": datetime.now().isoformat(), "analysts_contributing": len(state.get("analysts_team", [])),
        "research_sources": len(state.get("research_results", {})), "analyst_details": [
            {"role": a.role, "affiliation": a.affiliation, "tools": a.tools, "description": a.description}
            for a in state.get("analysts_team", [])]
    }
    return {"final_report": structured_report}

def save_json_report(state: ResearchState) -> Dict[str, Any]:
    final_report = state.get("final_report", {})
    if not final_report: return {"export_paths": state.get("export_paths", {})}
    
    filename = "final_business_report.json"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON report saved: {filename}")
        export_paths = state.get("export_paths", {})
        export_paths["json"] = filename
        return {"export_paths": export_paths}
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return {"export_paths": state.get("export_paths", {})}

def save_markdown_report(state: ResearchState) -> Dict[str, Any]:
    final_report = state.get("final_report", {})
    if not final_report: return {"export_paths": state.get("export_paths", {})}
    
    filename = "final_business_report.md"
    try:
        content = f"""# 🎯 Business Report: {final_report.get('business_concept', 'Restaurant')}

## 📋 Executive Summary
{final_report.get('executive_summary', 'N/A')}

## 📊 Market Analysis
{final_report.get('market_analysis', 'N/A')}

## 💰 Financial Recommendations
{final_report.get('financial_recommendations', 'N/A')}

## ⚠️ Risk Assessment
{final_report.get('risk_assessment', 'N/A')}

## 📄 Complete Report
{final_report.get('complete_report', 'N/A')}

---
*Generated: {final_report.get('generated_at', 'N/A')}*  
*Investment: {final_report.get('investment', 'N/A')}*  
*Location: {final_report.get('location', 'N/A')}*"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Markdown report saved: {filename}")
        export_paths = state.get("export_paths", {})
        export_paths["markdown"] = filename
        return {"export_paths": export_paths}
    except Exception as e:
        print(f"❌ Error saving Markdown: {e}")
        return {"export_paths": state.get("export_paths", {})}

def save_docx_report(state: ResearchState) -> Dict[str, Any]:
    final_report = state.get("final_report", {})
    if not final_report: return {"export_paths": state.get("export_paths", {})}
    
    filename = "final_business_report.docx"
    try:
        doc = Document()
        doc.add_heading(f'Business Report: {final_report.get("business_concept", "Restaurant")}', 0)
        
        # Business Info
        doc.add_paragraph(f"Location: {final_report.get('location', 'N/A')}")
        doc.add_paragraph(f"Investment: {final_report.get('investment', 'N/A')}")
        doc.add_paragraph(f"Target Demographic: {final_report.get('target_demographic', 'N/A')}")
        doc.add_paragraph(f"Generated: {final_report.get('generated_at', 'N/A')}")
        
        # Sections
        for section, title in [
            ("executive_summary", "Executive Summary"),
            ("market_analysis", "Market Analysis"),
            ("financial_recommendations", "Financial Recommendations"),
            ("risk_assessment", "Risk Assessment"),
            ("complete_report", "Complete Business Report")
        ]:
            doc.add_heading(title, level=1)
            doc.add_paragraph(final_report.get(section, 'N/A'))
        
        doc.save(filename)
        print(f"✅ DOCX report saved: {filename}")
        export_paths = state.get("export_paths", {})
        export_paths["docx"] = filename
        return {"export_paths": export_paths}
    except Exception as e:
        print(f"❌ Error saving DOCX: {e}")
        return {"export_paths": state.get("export_paths", {})}

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
graph_3.add_node("save_json_report", save_json_report)
graph_3.add_node("save_markdown_report", save_markdown_report)
graph_3.add_node("save_docx_report", save_docx_report)
graph_3.add_node("display_export_summary", display_export_summary)

# Graph 3 Flow
graph_3.add_edge(START, "compile_executive_summary")
graph_3.add_edge("compile_executive_summary", "compile_market_analysis")
graph_3.add_edge("compile_market_analysis", "compile_financial_recommendations")
graph_3.add_edge("compile_financial_recommendations", "compile_risk_assessment")
graph_3.add_edge("compile_risk_assessment", "compile_final_report")
graph_3.add_edge("compile_final_report", "save_json_report")
graph_3.add_edge("save_json_report", "save_markdown_report")
graph_3.add_edge("save_markdown_report", "save_docx_report")
graph_3.add_edge("save_docx_report", "display_export_summary")
graph_3.add_edge("display_export_summary", END)

memory_3 = MemorySaver()
app_3 = graph_3.compile(checkpointer=memory_3)

# Main Execution
def main():
    initial_state = {
        "restaurant_concept": "Setup momo speciality Restaurant",
        "target_location": "Sneha Paradise-A, Warje-Malwadi, Pune, Maharashtra - 411058",
        "investment": "₹350,000", "target_demographic": "Professionals 25-45, health-conscious",
        "special_note": "momo demand, spending power, competition density", "max_analysts": 5, "retry_count": 0
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
            "completed_analysts": [],
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