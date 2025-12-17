# src/workflow/analyst_team_creator.py
"""
Analyst Team Creator Workflow

High-level Purpose
- Generate a dynamic analyst team using an LLM.
- Enforce schema, tool, and role constraints.
- Allow controlled human feedback and retries.
- Orchestrate execution using LangGraph with memory.

Engineering Principles
- Every failure path is logged.
- Every exception is wrapped with CustomException at boundaries.
- No hard crash of the pipeline.
- LLM output is treated as hostile input.
"""

import re
import json
from typing import Dict, Any, List

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.common.model_loader import model_loader
from src.graph_states.states import ResearchState, Analyst


class AnalystTeamCreator:
    """
    Graph 1: Analyst Team Creation

    What this class owns
    - Configuration loading
    - LLM invocation for analyst generation
    - Validation and sanitisation of analysts
    - Human feedback routing
    - Final analyst team emission
    """

    def __init__(self):
        """
        Step-by-step initialisation

        1. Load global configuration.
        2. Extract analysis and tools sections.
        3. Load LLM instance.
        4. Load prompt template.
        5. Build and compile LangGraph workflow.
        """
        try:
            # Load full config
            self.config = config_loader.get()

            # Extract required config sections
            self.analysis_config = self.config["analysis"]
            self.tools_config = self.config["tools"]

            # Load analysis LLM
            self.llm = model_loader.get_llm("team_creator_llm")

            # Load analyst generation prompt
            self.prompt = prompts_loader.get_chat_prompt(
                "analyst_generation",
                "dynamic_analysts",
            )

            # Build LangGraph workflow
            self.app = self._build_graph()

            logger.info("AnalystTeamCreator initialised")

        except Exception as e:
            logger.error("Initialisation failed", exc_info=True)
            raise CustomException("AnalystTeamCreator init failed", e)

    @staticmethod
    def _extract_json_array(text: str) -> str:
        """
        Extract JSON array from LLM output.

        Why this exists
        - LLM output is not guaranteed to be valid JSON.
        - Common failure modes: markdown, commentary, partial arrays.

        Extraction strategy (ordered)
        1. Markdown fenced JSON block
        2. Direct array containing objects
        3. Any bracketed array that looks object-based
        """
        try:
            if not text:
                raise ValueError("Empty LLM output")

            cleaned_text = text.strip()

            # Case 1: ```json [...] ```
            match = re.search(
                r"```(?:json)?\s*(\[.*?\])\s*```",
                cleaned_text,
                re.DOTALL,
            )
            if match:
                return match.group(1).strip()

            # Case 2: Direct array with object literals
            match = re.search(r"(\[\s*\{.*?\}\s*\])", cleaned_text, re.DOTALL)
            if match:
                return match.group(1).strip()

            # Case 3: Any array-looking structure
            match = re.search(r"(\[.*\])", cleaned_text, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                if "{" in candidate and "}" in candidate:
                    return candidate

            raise ValueError("No valid JSON array detected")

        except Exception as e:
            logger.error("JSON extraction failed", exc_info=True)
            raise CustomException("LLM JSON extraction failed", e)

    def _validate_analyst_data(self, item: dict) -> Analyst:
        """
        Validate and normalise a single analyst definition.

        Validation steps
        1. Mandatory fields present.
        2. Tools is a list.
        3. Tools exist in configured tool registry.

        Output
        - Fully constructed Analyst object.
        """
        try:
            # Required schema fields
            required_fields = ["role", "affiliation", "tools", "description"]
            missing = [f for f in required_fields if f not in item]
            if missing:
                raise ValueError(f"Missing fields: {missing}")

            # Tools must be list
            if not isinstance(item["tools"], list):
                raise TypeError("Tools must be a list")

            # Filter invalid tools
            valid_tools = [t for t in item["tools"] if t in self.tools_config]
            invalid_tools = set(item["tools"]) - set(valid_tools)
            if invalid_tools:
                logger.warning(
                    f"Invalid tools ignored for role '{item.get('role')}': {invalid_tools}"
                )

            # Construct Analyst dataclass
            return Analyst(
                role=item["role"].strip(),
                affiliation=item["affiliation"].strip(),
                tools=valid_tools,
                description=item["description"].strip(),
            )

        except Exception as e:
            logger.error("Analyst validation error", exc_info=True)
            raise CustomException("Analyst validation failed", e)

    def load_dynamic_analysts(
        self, state: ResearchState
    ) -> Dict[str, List[Analyst]]:
        """
        LangGraph Node: Analyst Generation

        Responsibilities
        1. Build prompt from ResearchState.
        2. Invoke LLM.
        3. Parse JSON safely.
        4. Validate analysts individually.
        5. Enforce max analyst count.

        Contract
        - Never raises.
        - Always returns dynamic_analysts key.
        """
        try:
            # Defensive read of location
            location = state.get("location", {})
            if not isinstance(location, dict):
                logger.warning("Invalid location format")
                location = {}

            # Render prompt text
            prompt_text = self.prompt.format(
                max_analysts=state["max_analysts"],
                restaurant_concept=state["restaurant_concept"],
                local_area=location.get("local_area", ""),
                city=location.get("city", ""),
                state=location.get("state", ""),
                pincode=location.get("pincode", ""),
                investment=state["investment"],
                target_demographic=state["target_demographic"],
                special_note=state.get("special_note", ""),
                available_tools=list(self.tools_config),
                required_roles=self.analysis_config["required_roles"],
            )

            # Call LLM
            response = self.llm.invoke(prompt_text)
            raw = getattr(response, "content", "") or ""
            if not raw:
                raise ValueError("Empty LLM response")

            # Try parsing via multiple strategies
            parsed = None
            for attempt in [lambda: self._extract_json_array(raw), lambda: raw.strip()]:
                try:
                    parsed = json.loads(attempt())
                    break
                except Exception:
                    continue

            if not isinstance(parsed, list):
                raise ValueError("Parsed output is not a list")

            analysts: List[Analyst] = []

            # Validate each analyst independently
            for idx, item in enumerate(parsed):
                if not isinstance(item, dict):
                    logger.warning(f"Skipping non-dict item at index {idx}")
                    continue
                try:
                    analysts.append(self._validate_analyst_data(item))
                except CustomException as ce:
                    logger.warning(f"Invalid analyst skipped at index {idx}: {ce}")

            # Enforce max analysts
            analysts = analysts[: state["max_analysts"]]

            if not analysts:
                raise ValueError("No valid analysts produced")

            logger.info(f"{len(analysts)} analysts generated successfully")
            return {"dynamic_analysts": analysts}

        except Exception as e:
            logger.error("Analyst generation failed", exc_info=True)
            return {"dynamic_analysts": []}

    def human_feedback(self, state: ResearchState) -> Dict[str, Any]:
        """
        LangGraph Node: Human Feedback

        Purpose
        - Present analysts to user.
        - Capture accept / regenerate / modify decision.

        Note
        - This node is intentionally blocking.
        """
        try:
            analysts = state.get("dynamic_analysts", [])
            if not analysts:
                logger.warning("No analysts available for feedback")
                return {"accept": False, "extra_instructions": "No analysts generated"}

            # Display analysts
            for i, analyst in enumerate(analysts, 1):
                print(f"{i}. {analyst.role} | {analyst.affiliation}")
                print(f"   Tools: {', '.join(analyst.tools)}")
                print(f"   Focus: {analyst.description}")

            # Capture user decision
            choice = input("Accept team? (y/n/r): ").strip().lower()

            if choice == "y":
                return {"accept": True}
            if choice == "r":
                return {
                    "accept": False,
                    "extra_instructions": "Generate a new team with different roles",
                }

            feedback = input("Improvement instructions: ").strip()
            return {"accept": False, "extra_instructions": feedback}

        except Exception as e:
            logger.error("Human feedback failed", exc_info=True)
            return {"accept": False, "extra_instructions": "Feedback error"}

    def final_research_team(
        self, state: ResearchState
    ) -> Dict[str, List[Analyst]]:
        """
        LangGraph Node: Finalisation

        Responsibilities
        - Lock analyst team.
        - Log role and tool coverage.
        """
        try:
            team = list(state.get("dynamic_analysts", []))
            if not team:
                logger.warning("Final analyst team empty")
                return {"analysts_team": []}

            tool_usage: Dict[str, int] = {}
            roles = set()

            # Aggregate analytics
            for analyst in team:
                roles.add(analyst.role.lower())
                for tool in analyst.tools:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1

            logger.info(f"Final team size: {len(team)}")
            logger.info(f"Tool usage: {tool_usage}")
            logger.info(f"Unique roles: {len(roles)}")

            return {"analysts_team": team}

        except Exception as e:
            logger.error("Final team creation failed", exc_info=True)
            return {"analysts_team": []}

    @staticmethod
    def route_feedback(state: ResearchState) -> str:
        """
        Conditional Router

        Decision logic
        - accept == True → final_research_team
        - retry until max_retries
        - force finalisation after limit
        """
        try:
            if state.get("accept"):
                return "final_research_team"

            retry_count = state.get("retry_count", 0) + 1
            max_retries = config_loader.get("research.max_retries", 3)

            if retry_count >= max_retries:
                logger.warning("Retry limit reached")
                return "final_research_team"

            return "load_dynamic_analysts"

        except Exception as e:
            logger.error("Routing failed", exc_info=True)
            return "final_research_team"

    def _build_graph(self):
        """
        Build LangGraph workflow.

        Nodes
        - load_dynamic_analysts
        - human_feedback
        - final_research_team

        Edges
        - START → load
        - load → feedback
        - feedback → conditional routing
        - final → END
        """
        try:
            graph = StateGraph(ResearchState)

            graph.add_node("load_dynamic_analysts", self.load_dynamic_analysts)
            graph.add_node("human_feedback", self.human_feedback)
            graph.add_node("final_research_team", self.final_research_team)

            graph.add_edge(START, "load_dynamic_analysts")
            graph.add_edge("load_dynamic_analysts", "human_feedback")

            graph.add_conditional_edges(
                "human_feedback",
                self.route_feedback,
                {
                    "final_research_team": "final_research_team",
                    "load_dynamic_analysts": "load_dynamic_analysts",
                },
            )

            graph.add_edge("final_research_team", END)

            return graph.compile(checkpointer=MemorySaver())

        except Exception as e:
            logger.error("Graph build failed", exc_info=True)
            raise CustomException("Graph construction failed", e)

    def create_team(self, initial_state: ResearchState) -> Dict[str, Any]:
        """
        Public API

        Guarantees
        - Safe execution.
        - No exception leakage.
        - Always returns analysts_team.
        """
        from langsmith import uuid7

        try:
            logger.info("Analyst team creation started")
            thread_id = str(uuid7())  # ✅ LangSmith-compliant UUID v7
            return self.app.invoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}},
            )

        except Exception as e:
            logger.error("Analyst team creation failed", exc_info=True)
            return {"analysts_team": [], "dynamic_analysts": []}
