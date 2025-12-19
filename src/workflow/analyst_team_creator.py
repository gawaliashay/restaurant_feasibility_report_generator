# src/workflow/analyst_team_creator.py
"""
Analyst Team Creator Workflow

Core Purpose
Generates a dynamic team of analysis specialists using LLM orchestration. Handles
schema validation, tool assignment, and interactive refinement through human feedback.

Key Features
- Generates context-aware analyst teams based on business requirements
- Enforces schema compliance and tool availability constraints
- Supports interactive human review and iterative refinement
- Manages execution flow with persistent memory using LangGraph

Error Handling Principles
- All failure paths are logged with context
- Exceptions are wrapped at workflow boundaries
- Pipeline continues execution with fallback states
- LLM outputs are treated as untrusted input
"""

import re
import json
from typing import Dict, Any, List

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.common.model_loader import model_loader
from src.graph_states.states import ResearchState, Analyst

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException


class AnalystTeamCreator:
    """
    Orchestrates the creation and refinement of analyst teams for research workflows.
    
    This component generates specialized analysts based on business context, validates
    their configuration against available tools, and manages the interactive refinement
    process through human feedback loops.
    
    Responsibilities
    - Configuration management for analysts and tools
    - LLM-powered analyst generation with prompt templating
    - Schema validation and data sanitization
    - Human feedback collection and integration
    - Workflow state management via LangGraph
    """

    def __init__(self):
        """
        Initializes the analyst team creator with required components.
        
        Initialization Sequence:
        1. Load global configuration settings
        2. Extract analyst and tool-specific configurations
        3. Initialize the LLM model for team generation
        4. Load prompt templates for analyst creation
        5. Construct and compile the LangGraph workflow
        
        Raises:
            CustomException: If any critical component fails to initialize
        """
        try:
            # Load application configuration
            self.config = config_loader.get()

            # Extract configuration sections
            self.analysis_config = self.config["analysis"]
            self.tools_config = self.config["tools"]

            # Initialize LLM for team generation
            self.llm = model_loader.get_llm("team_creator_llm")

            # Load prompt template for dynamic analyst generation
            self.prompt = prompts_loader.get_chat_prompt(
                "analyst_generation",
                "dynamic_analysts",
            )

            # Build and compile the workflow graph
            self.app = self._build_graph()

            logger.info("AnalystTeamCreator initialized successfully")

        except Exception as e:
            logger.error("Initialization failed", exc_info=True)
            raise CustomException("AnalystTeamCreator initialization failed", e)

    @staticmethod
    def _extract_json_array(text: str) -> str:
        """
        Extracts a JSON array from LLM output text.
        
        Handles common LLM output formats including markdown code blocks,
        partial JSON, and mixed content. Uses regex patterns to isolate
        valid JSON structures.
        
        Args:
            text: Raw text output from the LLM
            
        Returns:
            String containing only the JSON array
            
        Raises:
            ValueError: If no valid JSON array can be extracted
            CustomException: If extraction fails unexpectedly
        """
        try:
            if not text or not text.strip():
                raise ValueError("Empty LLM output received")

            cleaned_text = text.strip()

            # Pattern 1: Markdown code blocks with JSON
            match = re.search(
                r"```(?:json)?\s*(\[.*?\])\s*```",
                cleaned_text,
                re.DOTALL,
            )
            if match:
                return match.group(1).strip()

            # Pattern 2: Direct JSON array with object literals
            match = re.search(r"(\[\s*\{.*?\}\s*\])", cleaned_text, re.DOTALL)
            if match:
                return match.group(1).strip()

            # Pattern 3: Any array-like structure containing objects
            match = re.search(r"(\[.*\])", cleaned_text, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                if "{" in candidate and "}" in candidate:
                    return candidate

            raise ValueError("No valid JSON array detected in LLM output")

        except Exception as e:
            logger.error("Failed to extract JSON array from LLM output", exc_info=True)
            raise CustomException("JSON extraction from LLM output failed", e)

    def _validate_analyst_data(self, item: dict) -> Analyst:
        """
        Validates and normalizes a single analyst definition.
        
        Ensures required fields are present, tools are properly formatted,
        and all referenced tools exist in the configuration. Invalid tools
        are logged and filtered out.
        
        Args:
            item: Dictionary containing raw analyst data from LLM
            
        Returns:
            Validated Analyst object
            
        Raises:
            ValueError: If required fields are missing
            TypeError: If tools field is not a list
            CustomException: If validation fails unexpectedly
        """
        try:
            # Validate required fields
            required_fields = ["role", "affiliation", "tools", "description"]
            missing_fields = [f for f in required_fields if f not in item]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")

            # Validate tools format
            if not isinstance(item["tools"], list):
                raise TypeError("Tools field must be a list")

            # Filter for valid, configured tools
            valid_tools = [tool for tool in item["tools"] if tool in self.tools_config]
            invalid_tools = set(item["tools"]) - set(valid_tools)
            
            if invalid_tools:
                logger.warning(
                    f"Invalid tools ignored for role '{item.get('role')}': {invalid_tools}"
                )

            # Create validated Analyst object
            return Analyst(
                role=item["role"].strip(),
                affiliation=item["affiliation"].strip(),
                tools=valid_tools,
                description=item["description"].strip(),
            )

        except Exception as e:
            logger.error("Analyst validation failed", exc_info=True)
            raise CustomException("Analyst data validation error", e)

    def load_dynamic_analysts(
        self, state: ResearchState
    ) -> Dict[str, List[Analyst]]:
        """
        LangGraph Node: Generates analyst team based on research context.
        
        Orchestrates the LLM call to create analysts, parses the response,
        validates each analyst, and enforces maximum team size constraints.
        
        Args:
            state: Current ResearchState containing business context
            
        Returns:
            Dictionary with 'dynamic_analysts' key containing list of Analyst objects
            Returns empty list on failure to ensure workflow continuation
        """
        try:
            # Safely extract location data with defensive checks
            location = state.get("location", {})
            if not isinstance(location, dict):
                logger.warning("Invalid location format in state")
                location = {}

            # Construct prompt with contextual data
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
                feedback = state.get("extra_instructions", "")
                
            )

            # Generate analysts via LLM
            response = self.llm.invoke(prompt_text)
            raw_content = getattr(response, "content", "") or ""
            
            if not raw_content:
                raise ValueError("LLM returned empty response")

            # Parse LLM output with fallback strategies
            parsed_data = None
            parse_attempts = [
                lambda: self._extract_json_array(raw_content),
                lambda: raw_content.strip()
            ]
            
            for parse_attempt in parse_attempts:
                try:
                    parsed_data = json.loads(parse_attempt())
                    if isinstance(parsed_data, list):
                        break
                except Exception:
                    continue

            if not isinstance(parsed_data, list):
                raise ValueError("LLM output could not be parsed as a list")

            validated_analysts: List[Analyst] = []

            # Validate each analyst individually
            for index, analyst_data in enumerate(parsed_data):
                if not isinstance(analyst_data, dict):
                    logger.warning(f"Skipping non-dictionary item at index {index}")
                    continue
                
                try:
                    analyst = self._validate_analyst_data(analyst_data)
                    validated_analysts.append(analyst)
                except CustomException as ce:
                    logger.warning(f"Invalid analyst skipped at index {index}: {ce}")

            # Apply maximum team size constraint
            validated_analysts = validated_analysts[:state["max_analysts"]]

            if not validated_analysts:
                raise ValueError("No valid analysts generated from LLM output")

            logger.info(f"Successfully generated {len(validated_analysts)} analysts")
            return {"dynamic_analysts": validated_analysts}

        except Exception as e:
            logger.error("Analyst generation node failed", exc_info=True)
            # Return empty team to allow workflow continuation
            return {"dynamic_analysts": []}

    def human_feedback(self, state: ResearchState) -> Dict[str, Any]:
        """
        LangGraph Node: Collects human feedback on generated analyst team.
        
        Presents the generated team to the user and captures acceptance,
        regeneration requests, or modification instructions. This node
        blocks execution for user interaction.
        
        Args:
            state: Current ResearchState containing generated analysts
            
        Returns:
            Dictionary with 'accept' boolean and optional 'extra_instructions'
        """
        try:
            analysts = state.get("dynamic_analysts", [])
            if not analysts:
                logger.warning("No analysts available for user review")
                return {
                    "accept": False,
                    "extra_instructions": "No analysts generated for review"
                }

            # Display team composition to user
            print("\n" + "="*60)
            print("GENERATED ANALYST TEAM - REVIEW AND APPROVAL")
            print("="*60)
            
            for i, analyst in enumerate(analysts, 1):
                print(f"\n{i}. {analyst.role} | {analyst.affiliation}")
                print(f"   Tools: {', '.join(analyst.tools)}")
                print(f"   Focus: {analyst.description}")
            print("\n" + "="*60)

            # Capture user decision
            print("\nOptions:")
            print("  y - Accept team and proceed")
            print("  n - Provide improvement feedback")
            print("  r - Regenerate with different roles")
            
            choice = input("\nSelect option (y/n/r): ").strip().lower()

            if choice == "y":
                return {"accept": True}
            elif choice == "r":
                return {
                    "accept": False,
                    "extra_instructions": "Generate a completely new team with different roles"
                }
            else:
                feedback = input("\nProvide improvement instructions: ").strip()

                return {
                    "accept": False,
                    "extra_instructions": feedback if feedback else "Please improve the team composition"
                }

        except Exception as e:
            logger.error("Human feedback collection failed", exc_info=True)
            return {
                "accept": False,
                "extra_instructions": "Error occurred during feedback collection"
            }

    def final_research_team(
        self, state: ResearchState
    ) -> Dict[str, List[Analyst]]:
        """
        LangGraph Node: Finalizes and locks the analyst team.
        
        Aggregates analytics on tool usage and role coverage, logs final
        team composition, and prepares the team for downstream processing.
        
        Args:
            state: Current ResearchState containing accepted analysts
            
        Returns:
            Dictionary with 'analysts_team' key containing the final team
        """
        try:
            team = list(state.get("dynamic_analysts", []))
            if not team:
                logger.warning("Final analyst team is empty")
                return {"analysts_team": []}

            # Analyze team composition
            tool_usage: Dict[str, int] = {}
            roles = set()

            for analyst in team:
                roles.add(analyst.role.lower())
                for tool in analyst.tools:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1

            # Log final team analytics
            logger.info(f"Final team composition: {len(team)} analysts")
            logger.info(f"Tool distribution: {tool_usage}")
            logger.info(f"Unique roles covered: {len(roles)}")

            return {"analysts_team": team}

        except Exception as e:
            logger.error("Final team creation failed", exc_info=True)
            return {"analysts_team": []}

    @staticmethod
    def route_feedback(state: ResearchState) -> str:
        """
        Conditional Router: Determines next step based on user feedback.
        
        Decision Logic:
        - If team accepted → proceed to finalization
        - If retry limit not reached → regenerate team
        - If retry limit reached → force finalization
        
        Args:
            state: Current ResearchState with feedback data
            
        Returns:
            String indicating next node: 'final_research_team' or 'load_dynamic_analysts'
        """
        try:
            if state.get("accept"):
                return "final_research_team"

            retry_count = state.get("retry_count", 0) + 1
            max_retries = config_loader.get("research.max_retries", 3)

            if retry_count >= max_retries:
                logger.warning(f"Retry limit reached ({max_retries} attempts)")
                return "final_research_team"

            return "load_dynamic_analysts"

        except Exception as e:
            logger.error("Routing decision failed", exc_info=True)
            return "final_research_team"

    def _build_graph(self):
        """
        Constructs the LangGraph workflow for analyst team creation.
        
        Graph Structure:
        START → load_dynamic_analysts → human_feedback → conditional routing
                 ↑                                    ↓
                 └─────────────────────── final_research_team → END
        
        Returns:
            Compiled LangGraph application
        
        Raises:
            CustomException: If graph construction fails
        """
        try:
            graph = StateGraph(ResearchState)

            # Define workflow nodes
            graph.add_node("load_dynamic_analysts", self.load_dynamic_analysts)
            graph.add_node("human_feedback", self.human_feedback)
            graph.add_node("final_research_team", self.final_research_team)

            # Define workflow edges
            graph.add_edge(START, "load_dynamic_analysts")
            graph.add_edge("load_dynamic_analysts", "human_feedback")

            # Add conditional routing based on feedback
            graph.add_conditional_edges(
                "human_feedback",
                self.route_feedback,
                {
                    "final_research_team": "final_research_team",
                    "load_dynamic_analysts": "load_dynamic_analysts",
                },
            )

            graph.add_edge("final_research_team", END)

            # Compile with memory persistence
            return graph.compile(
                checkpointer=MemorySaver(),
                name="AnalystTeamCreator"
            )

        except Exception as e:
            logger.error("Workflow graph construction failed", exc_info=True)
            raise CustomException("Failed to build analyst team creation workflow", e)

    def create_team(self, initial_state: ResearchState) -> Dict[str, Any]:
        """
        Public API: Executes the analyst team creation workflow.
        
        Guarantees safe execution with comprehensive error handling.
        Always returns a valid team structure (empty on failure).
        
        Args:
            initial_state: Initial ResearchState with business context
            
        Returns:
            Dictionary containing the final 'analysts_team' and intermediate states
        """
        from langsmith import uuid7

        try:
            logger.info("Starting analyst team creation workflow")
            
            # Generate unique thread ID for execution tracking
            thread_id = str(uuid7())  # LangSmith-compatible UUID v7
            
            # Execute the compiled workflow
            result = self.app.invoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}}
            )
            
            logger.info("Analyst team creation completed successfully")
            return result

        except Exception as e:
            logger.error("Analyst team creation workflow failed", exc_info=True)
            # Return minimal valid structure to prevent downstream failures
            return {
                "analysts_team": [],
                "dynamic_analysts": []
            }