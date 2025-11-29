# src\workflow\research.py

import os
import sys
from datetime import datetime
import uuid
from typing import TypedDict, Dict, Any, List, Optional
from pydantic import Field, BaseModel
import operator
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
import requests
import json
import re
from dotenv import load_dotenv
from langgraph.types import Send
from typing_extensions import Annotated

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException

# Import loaders and configs
from src.common.tool_loader import tool_loader
from src.common.model_loader import model_loader
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.graph_states.states import ResearchState, Analyst
from src.utils.report_exporter import (
    save_json_generic,
    save_markdown_generic,
    save_docx_generic
)
from src.utils.create_unique_uuid import generate_thread_id

load_dotenv()

# Get configuration
config = config_loader.get()

# LLM clients using model_loader with config-driven providers
llm = model_loader.load_llm(config['llm']['main_provider'])
llm_fast = model_loader.load_llm(config['llm']['fast_provider'])

# Analyst Generation using prompts_loader
DYNAMIC_ANALYSTS_PROMPT = prompts_loader.get_chat_prompt('analyst_generation', 'dynamic_analysts')
FINAL_REPORT_TEMPLATE = prompts_loader.get_prompt('report_templates', 'final_report')

def _extract_json_array(text: str) -> Optional[str]:
    """Extract JSON array from text response."""
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
    
    # Get configuration values
    tools_config = config['tools']
    analysis_config = config['analysis']
    
    available_tools = list(tools_config.keys())
    required_roles = analysis_config['required_roles']
    
    # Debug: Print the values being passed to the template
    print(f"DEBUG - Template variables:")
    print(f"  max_analysts: {state['max_analysts']}")
    print(f"  restaurant_concept: {state['restaurant_concept']}")
    print(f"  target_location: {state['target_location']}")
    print(f"  investment: {state['investment']}")
    print(f"  target_demographic: {state['target_demographic']}")
    print(f"  special_note: {state.get('special_note', '')}")
    print(f"  available_tools: {available_tools}")
    print(f"  required_roles: {required_roles}")
    
    # Let's also check what the actual prompt template contains
    print(f"DEBUG - Prompt template preview:")
    prompt_template_text = DYNAMIC_ANALYSTS_PROMPT.messages[0].prompt.template
    print(prompt_template_text[:200] + "..." if len(prompt_template_text) > 200 else prompt_template_text)
    
    try:
        prompt_text = DYNAMIC_ANALYSTS_PROMPT.format(
            max_analysts=state["max_analysts"],
            restaurant_concept=state["restaurant_concept"],
            target_location=state["target_location"],
            investment=state["investment"],
            target_demographic=state["target_demographic"],
            special_note=(state.get("special_note", "") + " " + extra_note).strip(),
            available_tools=available_tools,
            required_roles=", ".join(required_roles)
        )
    except KeyError as e:
        print(f"❌ Template formatting error: Missing variable {e}")
        print("💡 Check your prompts.yaml for malformed template variables")
        # Let's see all variables in the template
        import re
        variables = re.findall(r'\{(\w+)\}', prompt_template_text)
        print(f"Variables found in template: {set(variables)}")
        return {"dynamic_analysts": []}
    
    print(f"🤖 Generating {state['max_analysts']} analysts...")
    result = llm.invoke(prompt_text)
    raw = getattr(result, "content", "") or ""
    
    # Debug: Print the raw LLM response
    print(f"DEBUG - Raw LLM response:")
    print(raw[:500] + "..." if len(raw) > 500 else raw)
    
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
    
    try: 
        user_input = input("\nAccept these Analysts? Enter 'y' for Yes or 'n' for No:  ").strip().lower()
    except: 
        user_input = "n"
    
    if user_input == 'y': 
        return {"accept": True}
    
    try: 
        extra = input("Give Extra Instructions (or press Enter to skip): ").strip()
    except: 
        extra = ""
    return {"accept": False, "extra_instructions": extra}

def final_research_team(state: ResearchState) -> Dict[str, List[Analyst]]:
    return {"analysts_team": list(state.get("dynamic_analysts", []))}

def route_feedback(state: ResearchState) -> str:
    if state.get("accept"): 
        return "final_research_team"
    count = state.get("retry_count", 0) + 1
    state["retry_count"] = count
    return "final_research_team" if count >= config['research']['max_retries'] else "load_dynamic_analysts"

# Graph 1 Setup - Analyst Team Creation
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

# Research Data Compression Functions
def compress_research_data(research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only key insights, numbers, and actionable data from research"""
    analysis_config = config['analysis']
    keywords = analysis_config['keywords']
    
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
        
        # Extract data using configurable keywords
        for category, keyword_list in keywords.items():
            if any(word in analysis.lower() for word in keyword_list):
                # Create regex pattern for the category
                pattern = '|'.join([f'[^.]*{word}[^.]*\\.' for word in keyword_list])
                matches = re.findall(pattern, analysis, re.IGNORECASE)
                compressed[category].extend(matches)
    
    # Remove duplicates and limit length using config
    for key in compressed:
        if isinstance(compressed[key], list):
            compressed[key] = list(set(compressed[key]))[:analysis_config['max_compressed_items']]
    
    return compressed

def summarize_research_for_reports(compressed_data: Dict[str, Any]) -> str:
    """Create a concise summary for report generation"""
    analysis_config = config['analysis']
    summary_parts = []
    
    # Use configurable limits for each section
    summary_config = {
        "key_numbers": 5,
        "market_insights": 3,
        "competitor_data": 2,
        "financial_data": 3,
        "risk_factors": 3
    }
    
    for category, limit in summary_config.items():
        if compressed_data.get(category):
            items = compressed_data[category][:limit]
            if category == "key_numbers":
                summary_parts.append(f"Key Numbers: {', '.join(items)}")
            else:
                # Clean up the extracted sentences
                cleaned_items = []
                for item in items:
                    # Remove extra whitespace and normalize
                    cleaned = ' '.join(item.split())
                    cleaned_items.append(cleaned)
                summary_parts.append(f"{category.replace('_', ' ').title()}: {'; '.join(cleaned_items)}")
    
    return " | ".join(summary_parts)

# Graph 2 - OPTIMIZED Parallel Research
RESEARCH_PROMPT = prompts_loader.get_chat_prompt('research', 'single_analyst')
OPTIMIZED_ANALYSIS_PROMPT = prompts_loader.get_prompt('research', 'optimized_analysis')

def create_research_tasks(state: ResearchState) -> Dict[str, Any]:
    research_tasks = []
    for analyst in state.get("analysts_team", []):
        task = {
            "analyst_role": analyst.role, 
            "affiliation": analyst.affiliation,
            "description": analyst.description, 
            "tools": analyst.tools,
            "prompt": RESEARCH_PROMPT.format(
                analyst_role=analyst.role, 
                affiliation=analyst.affiliation,
                description=analyst.description, 
                restaurant_concept=state["restaurant_concept"],
                target_location=state["target_location"], 
                investment=state["investment"],
                target_demographic=state["target_demographic"], 
                special_note=state.get("special_note", "")
            )
        }
        research_tasks.append(task)
        print(f"📋 Created research task for: {analyst.role}")
    return {"research_tasks": research_tasks, "research_results": {}}

def initiate_parallel_research(state: ResearchState):
    """Dynamic Send() to launch all analysts in parallel"""
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
            tool_func = tool_loader.get(tool_name)
            if tool_func:
                # Prepare tool parameters based on tool type
                tool_params = {"search_query": research_query}
                if tool_name in ["openstreetmap", "google_maps"]:
                    tool_params["location"] = state["target_location"]
                elif tool_name == "google_trends":
                    tool_params["trend_query"] = f"{state['restaurant_concept']} {state['target_location']}"
                
                result = tool_func(tool_params)
                status = "success" if "error" not in result else "error"
                research_findings.append({"tool": tool_name, "data": result, "status": status})
            else:
                research_findings.append({"tool": tool_name, "data": {"error": "Tool not found"}, "status": "failed"})
        except Exception as e:
            research_findings.append({"tool": tool_name, "data": {"error": str(e)}, "status": "failed"})
    
    # Use optimized analysis prompt from prompts_loader
    analysis_prompt = OPTIMIZED_ANALYSIS_PROMPT.format(
        analyst_role=analyst_role,
        affiliation=current_task["affiliation"],
        description=current_task["description"],
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        investment=state["investment"],
        target_demographic=state["target_demographic"],
        research_findings=research_findings
    )
    
    try:
        analysis_result = llm.invoke(analysis_prompt)
        analysis_content = getattr(analysis_result, "content", "Analysis unavailable")
        
        # Parse the structured response
        analysis_text = ""
        key_insights = []
        
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
        "analyst_role": analyst_role, 
        "affiliation": current_task["affiliation"],
        "specialization": current_task["description"], 
        "tools_used": [f["tool"] for f in research_findings],
        "research_data": research_findings, 
        "expert_analysis": analysis_text,
        "key_insights": key_insights[:3],
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
    
    # Compress research data for report generation
    compressed_data = compress_research_data(research_results)
    research_summary_text = summarize_research_for_reports(compressed_data)
    
    # Collect insights from individual analyses
    all_insights = []
    for analyst_role, findings in research_results.items():
        all_insights.extend(findings.get('key_insights', []))
    
    summary = {
        "total_analysts": len(research_results),
        "research_completed": datetime.now().isoformat(),
        "business_context": {
            "concept": state["restaurant_concept"], 
            "location": state["target_location"],
            "investment": state["investment"], 
            "target_demographic": state["target_demographic"]
        },
        "analyst_findings": research_results, 
        "key_insights": all_insights[:config['analysis']['max_key_insights']],
        "compressed_data": compressed_data,
        "research_summary_text": research_summary_text
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
    "executive_summary": prompts_loader.get_chat_prompt('reporting', 'executive_summary'),
    "market_analysis": prompts_loader.get_chat_prompt('reporting', 'market_analysis'),
    "financial": prompts_loader.get_chat_prompt('reporting', 'financial_recommendations'),
    "risk": prompts_loader.get_chat_prompt('reporting', 'risk_assessment'),
}

def compile_executive_summary(state: ResearchState) -> Dict[str, Any]:
    print("📝 Compiling Executive Summary...")
    
    research_summary = state.get("research_summary", {})
    compressed_data = research_summary.get("research_summary_text", "No research data available")
    
    prompt = PROMPTS["executive_summary"].format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        investment=state["investment"],
        target_demographic=state["target_demographic"],
        research_summary=compressed_data
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
        research_summary=compressed_data
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
        research_summary=compressed_data
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
        research_summary=compressed_data
    )
    
    try:
        result = llm.invoke(prompt)
        return {"risk_assessment": getattr(result, "content", "Risk assessment unavailable")}
    except Exception as e:
        print(f"⚠️  Risk assessment failed, using fallback: {e}")
        return {"risk_assessment": "Risk assessment unavailable due to technical issues."}

def compile_final_report(state: ResearchState) -> Dict[str, Any]:
    print("📄 Compiling Final Report...")
    
    # Use configurable report template
    executive = state.get("executive_summary", "")
    market = state.get("market_analysis", "")
    financial = state.get("financial_recommendations", "")
    risk = state.get("risk_assessment", "")
    
    # Use template from prompts_loader
    final_content = FINAL_REPORT_TEMPLATE.format(
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        executive_summary=executive,
        market_analysis=market,
        financial_recommendations=financial,
        risk_assessment=risk,
        timestamp=datetime.now().strftime('%Y-%m-%d at %H:%M')
    )
    
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
    timestamp = datetime.now().strftime(config['export']['timestamp_format'])
    
    for format_name in config['export']['formats']:
        try:
            if format_name == "json":
                json_path = f"final_report_{timestamp}.json"
                export_paths["json"] = save_json_generic(report, json_path)
                print(f"✅ JSON saved: {json_path}")
            elif format_name == "md":
                md_path = f"final_report_{timestamp}.md"
                export_paths["md"] = save_markdown_generic(report, md_path)
                print(f"✅ Markdown saved: {md_path}")
            elif format_name == "docx":
                docx_path = f"final_report_{timestamp}.docx"
                export_paths["docx"] = save_docx_generic(report, docx_path)
                print(f"✅ DOCX saved: {docx_path}")
        except Exception as e:
            print(f"❌ {format_name.upper()} save failed: {e}")

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
graph_3.add_node("save_all_reports", save_all_reports)
graph_3.add_node("display_export_summary", display_export_summary)

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
    # Use configurable business case
    business_case = config['business_case']['default']
    
    initial_state = {
        "restaurant_concept": business_case['restaurant_concept'],
        "target_location": business_case['target_location'],
        "investment": business_case['investment'],
        "target_demographic": business_case['target_demographic'],
        "special_note": business_case['special_note'],
        "max_analysts": config['research']['max_analysts'],
        "retry_count": config['research']['max_retries']
    }
    
    config_thread = {"configurable": {"thread_id": generate_thread_id()}}
    
    print("🔧 RUNNING GRAPH_1 - ANALYST TEAM CREATION")
    graph_1_result = app_1.invoke(initial_state, config=config_thread)
    
    if graph_1_result.get("analysts_team"):
        print("\n\n🔧 RUNNING GRAPH_2 - PARALLEL RESEARCH")
        graph_2_state = {
            **initial_state,
            "analysts_team": graph_1_result["analysts_team"],
            "research_tasks": [],
            "research_results": {},
            "research_summary": {}
        }
        graph_2_result = app_2.invoke(graph_2_state, config_thread)
        
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
        graph_3_result = app_3.invoke(graph_3_state, config_thread)
        
        print("\n🎉 COMPLETE PIPELINE FINISHED!")
        export_paths = graph_3_result.get("export_paths", {})
        for format_name, filepath in export_paths.items():
            print(f"   • {format_name.upper()}: {filepath}")
    else:
        print("❌ No analysts generated")

if __name__ == "__main__":
    main()