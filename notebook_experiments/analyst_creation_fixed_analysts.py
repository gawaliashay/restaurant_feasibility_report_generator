import os, sys
from datetime import datetime
import uuid
from typing import TypedDict, Dict, Any, List, Literal, Optional
from pydantic import Field, BaseModel
import operator
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException

from dotenv import load_dotenv
import json
import re

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["HUGGINGFACEHUB_API_TOKEN"] = os.getenv("HUGGINGFACEHUB_API_TOKEN")

class Analyst(BaseModel):
    role: str = Field(description="Role in the context of the restaurant_concept")
    affiliation: str = Field(description="Organisation -the analyst belongs to")
    tools: List[str] = Field(description="Tools this analyst can use")
    description: str = Field(description="Responsibilities and focus areas")

class ResearchState(TypedDict, total=False):
    restaurant_concept: str
    target_location: str
    investment: str
    target_demographic: str
    special_note: str
    max_analysts: int
    fixed_analysts: List[Analyst]
    dynamic_analysts: List[Analyst]
    analysts_team: List[Analyst]
    accept: bool
    extra_instructions: str

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=1)

DYNAMIC_ANALYSTS_PROMPT = ChatPromptTemplate.from_template("""
Generate EXACTLY {max_analysts} new analysts for a restaurant research team. 
They must add capabilities not present in the fixed analysts.

BUSINESS CONTEXT:
- restaurant_concept: {restaurant_concept}
- target_location: {target_location}
- Investment: {investment}
- target_demographic: {target_demographic}
- special_note: {special_note}

EXISTING FIXED ANALYSTS:
{existing_analysts}

RULES:
- Do not repeat or rename any fixed-analyst roles.
- Cover capability gaps only.
- Stay specific to the concept and location.
- Each analyst must be practically useful for market-research workflows.

Each analyst must include:
- "role": unique specialization name
- "affiliation": credible organisation
- "tools": 2–3 items from [tavily_search, google_trends, openstreetmap, numbeo, yelp, reddit]
- "description": clear responsibility scope

IMPORTANT: Return ONLY a valid JSON array. No markdown formatting, no additional text, no explanations.
""")

def load_fixed_analysts(state: ResearchState) -> Dict[str, List[Analyst]]:
    fixed_analysts = [
        Analyst(
            role="Market Analyst",
            affiliation="Market Intelligence Division",
            tools=["tavily_search", "google_trends"],
            description="Study demand signals, track industry trends, identify opportunity gaps and analyze market trends and demand patterns"
        ),
        Analyst(
            role="Demographics Analyst",
            affiliation="Geographic Research Institute",
            tools=["openstreetmap"],
            description="Analyze population data, map catchment areas, study locality characteristics and conduct demographic and geographic analysis"
        ),
        Analyst(
            role="Financial Analyst",
            affiliation="Financial Planning Department",
            tools=["numbeo", "tavily_search"],
            description="Build cost models, calculate breakeven points, estimate ROI and perform financial modeling and cost analysis"
        ),
        Analyst(
            role="Competitor Analyst",
            affiliation="Competitive Intelligence Unit",
            tools=["openstreetmap", "yelp"],
            description="Identify competitors, analyze menus and pricing, study reviews and provide competitive intelligence"
        )
    ]
    return {"fixed_analysts": fixed_analysts}

def _extract_json_array(text: str) -> Optional[str]:
    match = re.search(r'(\[\s*\{.*?\}\s*\])', text, re.DOTALL)
    if match:
        return match.group(1)
    block = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if block:
        inner = block.group(1).strip()
        mm = re.search(r'(\[\s*\{.*?\}\s*\])', inner, re.DOTALL)
        if mm:
            return mm.group(1)
    return None

def load_dynamic_analysts(state: ResearchState) -> Dict[str, List[Analyst]]:
    extra_note = state.get("extra_instructions", "") or ""
    existing_analysts_text = ""
    for a in state["fixed_analysts"]:
        existing_analysts_text += f"- {a.role}; {a.affiliation}; {a.tools}; {a.description}\n"

    prompt_text = DYNAMIC_ANALYSTS_PROMPT.format(
        max_analysts=state["max_analysts"],
        restaurant_concept=state["restaurant_concept"],
        target_location=state["target_location"],
        investment=state["investment"],
        target_demographic=state["target_demographic"],
        special_note=(state.get("special_note", "") + " " + extra_note).strip(),
        existing_analysts=existing_analysts_text,
    )

    result = llm.invoke(prompt_text)
    raw = getattr(result, "content", "") or ""

    parsed_items = []
    json_candidate = _extract_json_array(raw)
    if json_candidate:
        try:
            parsed_items = json.loads(json_candidate)
        except json.JSONDecodeError:
            cleaned = json_candidate.replace("'", '"')
            try:
                parsed_items = json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from LLM output.")
                parsed_items = []
    else:
        try:
            parsed_items = json.loads(raw)
        except Exception:
            parsed_items = []

    dynamic_analysts: List[Analyst] = []
    for item in parsed_items:
        if not isinstance(item, dict):
            continue
        try:
            dynamic_analysts.append(Analyst(**item))
        except Exception:
            logger.debug("Skipping invalid analyst item: %s", item)
            continue

    return {"dynamic_analysts": dynamic_analysts}

def human_feedback(state: ResearchState) -> Dict[str, Any]:
    print("\nFixed Analysts:")
    for idx, analyst in enumerate(state.get("fixed_analysts", []), 1):
        print(f"\n{idx}. {analyst.role}")
        print(f"   Affiliation: {analyst.affiliation}")
        print(f"   Tools: {', '.join(analyst.tools)}")
        print(f"   Description: {analyst.description}")

    print("\nGenerated Dynamic Analysts:")
    for idx, analyst in enumerate(state.get("dynamic_analysts", []), 1):
        print(f"\n{idx}. {analyst.role}")
        print(f"   Affiliation: {analyst.affiliation}")
        print(f"   Tools: {', '.join(analyst.tools)}")
        print(f"   Description: {analyst.description}")

    try:
        user_input = input("\nAccept these Analysts? Enter 'y' for Yes or 'n' for No:  ").strip().lower()
    except Exception:
        user_input = "n"

    if user_input == 'y':
        return {"accept": True}

    try:
        extra = input("Give Extra Instructions (or press Enter to skip): ").strip()
    except Exception:
        extra = ""

    return {"accept": False, "extra_instructions": extra}

def combine_analysts(state: ResearchState) -> Dict[str, List[Analyst]]:
    all_analysts = list(state.get("fixed_analysts", [])) + list(state.get("dynamic_analysts", []))
    return {"analysts_team": all_analysts}

def route_feedback(state: ResearchState) -> str:
    return "combine_analysts" if state.get("accept") else "load_dynamic_analysts"

graph = StateGraph(ResearchState)
graph.add_node("load_fixed_analysts", load_fixed_analysts)
graph.add_node("load_dynamic_analysts", load_dynamic_analysts)
graph.add_node("human_feedback", human_feedback)
graph.add_node("combine_analysts", combine_analysts)

graph.add_edge(START, "load_fixed_analysts")
graph.add_edge("load_fixed_analysts", "load_dynamic_analysts")
graph.add_edge("load_dynamic_analysts", "human_feedback")

graph.add_conditional_edges(
    "human_feedback",
    route_feedback,
    {
        "combine_analysts": "combine_analysts",
        "load_dynamic_analysts": "load_dynamic_analysts",
    },
)

graph.add_edge("combine_analysts", END)

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

initial_state: ResearchState = {
    "restaurant_concept": "Setup momo speciality Restaurant",
    "target_location": "Sneha Paradise-A, Warje-Malwadi, Pune, Maharashtra - 411058",
    "investment": "₹350,000",
    "target_demographic": "Professionals 25-45, health-conscious",
    "special_note": "momo demand, spending power, competition density",
    "max_analysts": 2
}

config = {"configurable": {"thread_id": str(uuid.uuid4())}}
final_state = app.invoke(initial_state, config=config)

print("\n" + "="*50)
print("FINAL RESEARCH TEAM")
print("="*50)
for idx, analyst in enumerate(final_state.get("analysts_team", []), 1):
    print(f"\n{idx}. {analyst.role}")
    print(f"   Affiliation: {analyst.affiliation}")
    print(f"   Tools: {', '.join(analyst.tools)}")
    print(f"   Description: {analyst.description}")
