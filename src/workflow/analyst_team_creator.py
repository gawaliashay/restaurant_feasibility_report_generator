# src/workflow/analyst_team_creator.py

import re
import json
from typing import Dict, Any, List, Optional
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.logging_exception.logging.logger import logger
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.common.model_loader import model_loader
from src.graph_states.states import ResearchState, Analyst

config = config_loader.get()
llm = model_loader.load_llm(config['llm']['main_provider'])
DYNAMIC_ANALYSTS_PROMPT = prompts_loader.get_chat_prompt('analyst_generation', 'dynamic_analysts')

class AnalystTeamCreator:
    """Handles Graph 1 - Dynamic Analyst Team Creation with Human Feedback."""
    
    def __init__(self):
        self.config = config_loader.get()
        self.llm = model_loader.load_llm(self.config['llm']['main_provider'])
        self.dynamic_analysts_prompt = prompts_loader.get_chat_prompt('analyst_generation', 'dynamic_analysts')
        self.app = self._build_graph()
    
    def _extract_json_array(self, text: str) -> Optional[str]:
        """Extract JSON array from text response."""
        text = text.strip()
        code_block = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()
        json_match = re.search(r"(\[.*\])", text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        return None

    def load_dynamic_analysts(self, state: ResearchState) -> Dict[str, List[Analyst]]:
        """Node: Load dynamic analysts based on business context."""
        extra_note = state.get("extra_instructions", "") or ""
        
        tools_config = self.config['tools']
        analysis_config = self.config['analysis']
        
        available_tools = list(tools_config.keys())
        required_roles = analysis_config['required_roles']
        
        print(f"DEBUG - Template variables:")
        print(f"  max_analysts: {state['max_analysts']}")
        print(f"  restaurant_concept: {state['restaurant_concept']}")
        print(f"  target_location: {state['target_location']}")
        print(f"  investment: {state['investment']}")
        print(f"  target_demographic: {state['target_demographic']}")
        print(f"  special_note: {state.get('special_note', '')}")
        print(f"  available_tools: {available_tools}")
        print(f"  required_roles: {required_roles}")
        
        try:
            # Test the template variables first
            template_vars = {
                "max_analysts": state["max_analysts"],
                "restaurant_concept": state["restaurant_concept"],
                "target_location": state["target_location"],
                "investment": state["investment"],
                "target_demographic": state["target_demographic"],
                "special_note": (state.get("special_note", "") + " " + extra_note).strip(),
                "available_tools": available_tools,
                "required_roles": ", ".join(required_roles)
            }
            
            # Test format first
            test_prompt = self.dynamic_analysts_prompt.format(**template_vars)
            print("✅ Template formatting successful")
            prompt_text = test_prompt
            
        except KeyError as e:
            print(f"❌ Template formatting error: Missing variable {e}")
            print("🔄 Using fallback analyst generation...")
            return self._generate_fallback_analysts(state)
        
        print(f"🤖 Generating {state['max_analysts']} analysts...")
        try:
            result = self.llm.invoke(prompt_text)
            raw = getattr(result, "content", "") or ""
            print(f"DEBUG - Raw LLM response length: {len(raw)} chars")
            print(f"DEBUG - First 200 chars: {raw[:200]}...")
        except Exception as e:
            print(f"❌ LLM invocation failed: {e}")
            return self._generate_fallback_analysts(state)
        
        parsed_items = []
        json_candidate = self._extract_json_array(raw)
        
        if json_candidate:
            print(f"DEBUG - Found JSON candidate, length: {len(json_candidate)}")
            try:
                parsed_items = json.loads(json_candidate)
                print(f"✅ Successfully parsed JSON with {len(parsed_items)} items")
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse failed: {e}")
                try:
                    # Try to clean and parse again
                    cleaned = json_candidate.replace("'", '"').replace("\\n", "").strip()
                    parsed_items = json.loads(cleaned)
                    print(f"✅ Successfully parsed cleaned JSON")
                except json.JSONDecodeError as e2:
                    print(f"❌ Cleaned JSON also failed: {e2}")
                    parsed_items = []
        else:
            print("❌ No JSON array found in response")
            # Try to extract any JSON-like structure
            json_match = re.search(r'\[\s*{.*}\s*\]', raw, re.DOTALL)
            if json_match:
                try:
                    parsed_items = json.loads(json_match.group())
                    print(f"✅ Found and parsed JSON with regex")
                except:
                    parsed_items = []
        
        dynamic_analysts = []
        for item in parsed_items:
            if isinstance(item, dict):
                try:
                    if all(k in item for k in ["role", "affiliation", "tools", "description"]):
                        analyst = Analyst(**item)
                        dynamic_analysts.append(analyst)
                        print(f"✅ Added analyst: {analyst.role}")
                    else:
                        missing = [k for k in ["role", "affiliation", "tools", "description"] if k not in item]
                        print(f"❌ Analyst missing fields {missing}: {item}")
                except Exception as e:
                    print(f"❌ Failed to create analyst from {item}: {e}")
        
        # If no analysts were created, use fallback
        if not dynamic_analysts:
            print("❌ No valid analysts created, using fallback")
            return self._generate_fallback_analysts(state)
        
        # Enforce max_analysts limit
        if len(dynamic_analysts) > state["max_analysts"]:
            print(f"⚠️  Limiting to {state['max_analysts']} analysts")
            dynamic_analysts = dynamic_analysts[:state["max_analysts"]]
        
        print(f"🎯 Total analysts created: {len(dynamic_analysts)}")
        return {"dynamic_analysts": dynamic_analysts}

    def _generate_fallback_analysts(self, state: ResearchState) -> Dict[str, List[Analyst]]:
        """Generate fallback analysts when template fails."""
        print("🔄 Using fallback analyst generation...")
        
        fallback_analysts = [
            {
                "role": "Market Research Analyst",
                "affiliation": "Euromonitor International",
                "tools": ["tavily_search"],
                "description": "Analyze market trends and consumer demand patterns for momo restaurants"
            },
            {
                "role": "Financial Analyst", 
                "affiliation": "Deloitte",
                "tools": [],
                "description": "Evaluate financial feasibility and investment returns for restaurant startup"
            },
            {
                "role": "Location Intelligence Analyst",
                "affiliation": "Esri",
                "tools": ["openstreetmap"],
                "description": "Assess location viability and demographic patterns in target area"
            },
            {
                "role": "Competition Analysis Analyst",
                "affiliation": "IBISWorld", 
                "tools": ["google_maps"],
                "description": "Analyze competitive landscape and market positioning strategies"
            }
        ]
        
        dynamic_analysts = []
        for i, analyst_data in enumerate(fallback_analysts[:state["max_analysts"]]):
            try:
                analyst = Analyst(**analyst_data)
                dynamic_analysts.append(analyst)
                print(f"✅ Added fallback analyst: {analyst.role}")
            except Exception as e:
                print(f"❌ Failed to create fallback analyst: {e}")
        
        return {"dynamic_analysts": dynamic_analysts}
    
    def human_feedback(self, state: ResearchState) -> Dict[str, Any]:
        """Node: Get human feedback on generated analysts."""
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

    def final_research_team(self, state: ResearchState) -> Dict[str, List[Analyst]]:
        """Node: Finalize the research team."""
        return {"analysts_team": list(state.get("dynamic_analysts", []))}

    def route_feedback(self, state: ResearchState) -> str:
        """Conditional routing based on human feedback."""
        if state.get("accept"): 
            return "final_research_team"
        count = state.get("retry_count", 0) + 1
        state["retry_count"] = count
        return "final_research_team" if count >= self.config['research']['max_retries'] else "load_dynamic_analysts"

    def _build_graph(self):
        """Build and compile Graph 1."""
        graph = StateGraph(ResearchState)
        
        graph.add_node("load_dynamic_analysts", self.load_dynamic_analysts)
        graph.add_node("human_feedback", self.human_feedback)
        graph.add_node("final_research_team", self.final_research_team)
        
        graph.add_edge(START, "load_dynamic_analysts")
        graph.add_edge("load_dynamic_analysts", "human_feedback")
        graph.add_conditional_edges("human_feedback", self.route_feedback, {
            "final_research_team": "final_research_team",
            "load_dynamic_analysts": "load_dynamic_analysts",
        })
        graph.add_edge("final_research_team", END)
        
        memory = MemorySaver()
        return graph.compile(checkpointer=memory)

    def create_team(self, initial_state: ResearchState) -> Dict[str, Any]:
        """Execute the analyst team creation workflow."""
        from src.utils.create_unique_uuid import generate_thread_id
        config_thread = {"configurable": {"thread_id": generate_thread_id()}}
        return self.app.invoke(initial_state, config=config_thread)