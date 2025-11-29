# src\workflow\parallel_research_engine.py

import re
from datetime import datetime
from typing import Dict, Any, List
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send

from src.logging_exception.logging.logger import logger
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.common.model_loader import model_loader
from src.common.tool_loader import tool_loader
from src.graph_states.states import ResearchState

config = config_loader.get()
llm = model_loader.load_llm(config['llm']['main_provider'])
RESEARCH_PROMPT = prompts_loader.get_chat_prompt('research', 'single_analyst')
OPTIMIZED_ANALYSIS_PROMPT = prompts_loader.get_prompt('research', 'optimized_analysis')

class ParallelResearchEngine:
    """Handles Graph 2 - Parallel Research Execution with Dynamic Send()."""
    
    def __init__(self):
        self.config = config_loader.get()
        self.llm = model_loader.load_llm(self.config['llm']['main_provider'])
        # Use single_analyst for task creation, optimized_analysis for actual research
        self.research_prompt = prompts_loader.get_chat_prompt('research', 'single_analyst')
        self.optimized_analysis_prompt = prompts_loader.get_prompt('research', 'optimized_analysis')
        self.app = self._build_graph()
    
    def compress_research_data(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only key insights, numbers, and actionable data from research."""
        analysis_config = self.config['analysis']
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
                    pattern = '|'.join([f'[^.]*{word}[^.]*\\.' for word in keyword_list])
                    matches = re.findall(pattern, analysis, re.IGNORECASE)
                    compressed[category].extend(matches)
        
        # Remove duplicates and limit length using config
        for key in compressed:
            if isinstance(compressed[key], list):
                compressed[key] = list(set(compressed[key]))[:analysis_config['max_compressed_items']]
        
        return compressed

    def summarize_research_for_reports(self, compressed_data: Dict[str, Any]) -> str:
        """Create a concise summary for report generation."""
        analysis_config = self.config['analysis']
        summary_parts = []
        
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
                    cleaned_items = []
                    for item in items:
                        cleaned = ' '.join(item.split())
                        cleaned_items.append(cleaned)
                    summary_parts.append(f"{category.replace('_', ' ').title()}: {'; '.join(cleaned_items)}")
        
        return " | ".join(summary_parts)

    def create_research_tasks(self, state: ResearchState) -> Dict[str, Any]:
        """Node: Create research tasks for all analysts."""
        research_tasks = []
        for analyst in state.get("analysts_team", []):
            # Use the single_analyst prompt which doesn't require research_findings
            task = {
                "analyst_role": analyst.role, 
                "affiliation": analyst.affiliation,
                "description": analyst.description, 
                "tools": analyst.tools,
                "prompt": self.research_prompt.format(
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

    def initiate_parallel_research(self, state: ResearchState):
        """Dynamic Send() to launch all analysts in parallel."""
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

        
    def execute_single_analyst_research(self, state: ResearchState) -> Dict[str, Any]:
        """Node: Process ONE analyst with OPTIMIZED analysis + insights."""
        current_task = state.get("current_task")
        
        if not current_task:
            print("❌ No current task found in state")
            return {}
        
        analyst_role = current_task["analyst_role"]
        tools = current_task.get("tools", [])
        
        print(f"\n🔍 Conducting research for: {analyst_role}")
        print(f"   Tools: {', '.join(tools)}")
        
        # Better search queries for each analyst type
        enhanced_queries = {
            "Market Research Analyst": f"momo popularity trends Pune Maharashtra 2024 consumer demand",
            "Financial Analyst": f"restaurant startup costs Pune profit margins food business investment",
            "Location Intelligence Analyst": f"Warje Pune demographics foot traffic commercial property",
            "Competition Analysis Analyst": f"restaurants competition Warje Pune menu prices reviews"
        }
        
        research_query = enhanced_queries.get(analyst_role, f"{state['restaurant_concept']} {state['target_location']}")
        
        research_findings = []
        research_data_summary = []

        for tool_name in tools:
            try:
                tool_func = tool_loader.get(tool_name)
                if tool_func:
                    # Use better parameters for each tool
                    if tool_name == "tavily_search":
                        tool_params = {"search_query": research_query}
                    elif tool_name == "google_trends":
                        tool_params = {"trend_query": f"momo restaurant Pune"}
                    elif tool_name in ["openstreetmap", "google_maps"]:
                        tool_params = {"location": "Warje Pune Maharashtra"}
                    else:
                        tool_params = {"search_query": research_query}
                    
                    print(f"🔧 DEBUG: Executing {tool_name} with params: {tool_params}")
                    result = tool_func(tool_params)
                    status = "success" if "error" not in str(result) else "error"
                    research_findings.append({"tool": tool_name, "data": result, "status": status})
                else:
                    print(f"❌ Tool {tool_name} not found in tool_loader")
                    research_findings.append({"tool": tool_name, "data": {"error": "Tool not found"}, "status": "failed"})
            except Exception as e:
                print(f"❌ Tool {tool_name} failed with error: {str(e)}")
                research_findings.append({"tool": tool_name, "data": {"error": str(e)}, "status": "failed"})
        
        # SIMPLE DATA EXTRACTION - FIXED VERSION
        successful_findings = [f for f in research_findings if f["status"] == "success"]
        
        for finding in successful_findings:
            data = finding['data']
            tool_name = finding['tool']
            
            # Simple extraction for each tool type
            if tool_name == 'tavily_search' and 'results' in data:
                # Tavily returns list of results directly
                results_list = data['results']
                if isinstance(results_list, list):
                    for result in results_list[:2]:  # Get first 2 results
                        title = result.get('title', '')
                        content = result.get('content', '')[:100]
                        if title:
                            research_data_summary.append(f"Search: {title} - {content}...")
            
            elif tool_name == 'google_maps' and 'results' in data:
                # Google Maps returns list of businesses
                results_list = data['results']
                if isinstance(results_list, list):
                    for result in results_list[:2]:
                        title = result.get('title', 'Business')
                        research_data_summary.append(f"Business: {title}")
            
            elif tool_name == 'openstreetmap':
                # OpenStreetMap returns location data
                display_name = data.get('display_name', 'Location')
                research_data_summary.append(f"Location: {display_name}")
            
            elif tool_name == 'google_trends' and 'data' in data:
                # Google Trends data
                trends_data = data['data']
                if 'averages' in trends_data:
                    for avg in trends_data['averages'][:2]:
                        query = avg.get('query', '')
                        value = avg.get('value', 0)
                        if value > 0:
                            research_data_summary.append(f"Trend: {query} (score: {value})")

        # SIMPLE FALLBACK LOGIC
        if research_data_summary:
            research_data_for_analysis = " | ".join(research_data_summary)
            print(f"✅ Research data extracted: {research_data_for_analysis}")
        else:
            # Only show fallback if NO tools provided data
            if successful_findings:
                # Tools worked but no specific data extracted - use generic success message
                research_data_for_analysis = f"Research conducted using {len(successful_findings)} tools for {analyst_role}"
                print(f"ℹ️  Tools executed successfully, using research context")
            else:
                # No tools worked - use contextual data
                research_data_for_analysis = f"Market analysis for {state['restaurant_concept']} targeting {state['target_demographic']} in Pune with {state['investment']} investment"
                print(f"ℹ️  No tool data available, using contextual research data")
        
        # REST OF THE METHOD REMAINS EXACTLY THE SAME
        # Use the updated prompt format from prompts file
        analysis_prompt = self.optimized_analysis_prompt.format(
            analyst_role=analyst_role,
            affiliation=current_task["affiliation"],
            description=current_task["description"],
            restaurant_concept=state["restaurant_concept"],
            target_location=state["target_location"],
            investment=state["investment"],
            target_demographic=state["target_demographic"],
            research_findings=research_data_for_analysis
        )
        
        try:
            analysis_result = self.llm.invoke(analysis_prompt)
            analysis_content = getattr(analysis_result, "content", "Analysis unavailable")
            
            # FIXED: Handle the new prompt format properly
            analysis_text = ""
            key_insights = []
            
            # Extract analysis section
            if "ANALYSIS SECTION:" in analysis_content:
                parts = analysis_content.split("ANALYSIS SECTION:")
                if len(parts) > 1:
                    analysis_text = parts[1].split("KEY INSIGHTS:")[0].strip() if "KEY INSIGHTS:" in parts[1] else parts[1].strip()
            elif "ANALYSIS:" in analysis_content:
                parts = analysis_content.split("ANALYSIS:")
                if len(parts) > 1:
                    analysis_text = parts[1].split("KEY INSIGHTS:")[0].strip() if "KEY INSIGHTS:" in parts[1] else parts[1].strip()
            else:
                analysis_text = analysis_content
            
            # Extract key insights
            if "KEY INSIGHTS:" in analysis_content:
                insights_part = analysis_content.split("KEY INSIGHTS:")[1]
                key_insights = [insight.strip() for insight in insights_part.split('\n') 
                            if insight.strip() and insight.strip().startswith('-')]
            
            # Final cleanup - remove any remaining **** patterns
            analysis_text = analysis_text.replace("****", "").strip()
            
            # Ensure we have at least some content
            if not analysis_text or len(analysis_text.strip()) < 30:
                analysis_text = f"Comprehensive analysis for {analyst_role} based on market research of {state['restaurant_concept']} in {state['target_location']}. Investment analysis for {state['investment']} targeting {state['target_demographic']}."
            
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
        print(f"   Analysis preview: {analysis_text[:100]}...")
        
        return {
            "research_results": {analyst_role: research_result},
            "current_analyst": analyst_role
        }

    def compile_research_summary(self, state: ResearchState) -> Dict[str, Any]:
        """Node: Compile research summary from all analysts."""
        research_results = state.get("research_results", {})
        print("\n" + "="*60)
        print("📊 PARALLEL RESEARCH COMPLETED - SUMMARY")
        print("="*60)
        
        compressed_data = self.compress_research_data(research_results)
        research_summary_text = self.summarize_research_for_reports(compressed_data)
        
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
            "key_insights": all_insights[:self.config['analysis']['max_key_insights']],
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

    def _build_graph(self):
        """Build and compile Graph 2 with Dynamic Send()."""
        graph = StateGraph(ResearchState)
        
        graph.add_node("create_research_tasks", self.create_research_tasks)
        graph.add_node("execute_single_analyst_research", self.execute_single_analyst_research)
        graph.add_node("compile_research_summary", self.compile_research_summary)
        
        graph.add_edge(START, "create_research_tasks")
        graph.add_conditional_edges("create_research_tasks", self.initiate_parallel_research, {
            "execute_single_analyst_research": "execute_single_analyst_research",
            END: END
        })
        graph.add_edge("execute_single_analyst_research", "compile_research_summary")
        graph.add_edge("compile_research_summary", END)
        
        memory = MemorySaver()
        return graph.compile(checkpointer=memory)

    def execute_research(self, initial_state: ResearchState) -> Dict[str, Any]:
        """Execute the parallel research workflow."""
        from src.utils.create_unique_uuid import generate_thread_id
        config_thread = {"configurable": {"thread_id": generate_thread_id()}}
        return self.app.invoke(initial_state, config_thread)