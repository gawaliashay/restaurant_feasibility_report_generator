# src\workflow\parallel_research_engine.py

"""
Parallel Research Engine Module

This module implements a robust parallel research execution system with enhanced error handling.
It orchestrates multiple analysts conducting research simultaneously using various tools.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send
import re

from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.common.model_loader import model_loader
from src.common.tool_loader import tool_loader
from src.graph_states.states import ResearchState


class ParallelResearchEngine:
    """
    Robust Parallel Research Execution Engine with Enhanced Error Handling.
    
    This engine orchestrates parallel research execution across multiple analysts,
    each with specialized tools and expertise. It handles tool execution, data
    aggregation, and analysis generation with comprehensive error handling.
    
    Attributes:
        config (Dict): Loaded configuration from config_loader
        analysis_config (Dict): Analysis-specific configuration
        tools_config (Dict): Tools-specific configuration
        llm: Language model for analysis generation
        research_prompt: Prompt template for research tasks
        analysis_prompt: Prompt template for analysis generation
        app: Compiled LangGraph application
    """
    
    def __init__(self):
        """Initialize the ParallelResearchEngine with configuration and models."""
        try:
            logger.info("Initializing ParallelResearchEngine")
            
            self.config = config_loader.get()
            self.analysis_config = self.config["analysis"]
            self.tools_config = self.config["tools"]

            self.llm = model_loader.get_llm("research_llm")
            self.research_prompt = prompts_loader.get_chat_prompt("research", "single_analyst")
            self.analysis_prompt = prompts_loader.get_prompt("research", "optimized_analysis")

            self.app = self._build_graph()
            
            logger.info("ParallelResearchEngine initialized successfully")
            
        except KeyError as e:
            logger.error(f"Missing configuration key: {e}")
            raise CustomException(
                f"Configuration error: Missing key {e}",
                "CONFIGURATION_ERROR",
                {"missing_key": str(e)}
            )
        except Exception as e:
            logger.error(f"Failed to initialize ParallelResearchEngine: {e}")
            raise CustomException(
                f"Initialization failed: {str(e)}",
                "INITIALIZATION_ERROR",
                {"component": "ParallelResearchEngine"}
            )

    def _extract_location(self, state: ResearchState) -> Dict[str, str]:
        """
        Safely extract location data with comprehensive validation.
        
        Args:
            state (ResearchState): Current research state containing location data
            
        Returns:
            Dict[str, str]: Extracted location components with fallback values
            
        Raises:
            CustomException: If location extraction fails critically
        """
        try:
            logger.debug("Extracting location data from state")
            
            location = state.get("location", {})
            
            if not isinstance(location, dict):
                logger.warning(f"Location is not a dictionary: {type(location)}")
                location = {}
                
            result = {
                "local_area": location.get("local_area", ""),
                "city": location.get("city", ""),
                "state": location.get("state", ""),
                "pincode": location.get("pincode", ""),
                "society": location.get("society", ""),
            }
            
            logger.debug(f"Extracted location: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Location extraction failed: {e}")
            raise CustomException(
                f"Location extraction error: {str(e)}",
                "LOCATION_EXTRACTION_ERROR",
                {"state_keys": list(state.keys()) if isinstance(state, dict) else "unknown"}
            )

    def _build_tool_context(self, state: ResearchState, analyst_role: str) -> Dict[str, str]:
        """
        Build tool execution context with guaranteed field availability.
        
        Args:
            state (ResearchState): Current research state
            analyst_role (str): Role of the analyst executing the tool
            
        Returns:
            Dict[str, str]: Context dictionary for tool execution
            
        Raises:
            CustomException: If context building fails
        """
        try:
            logger.debug(f"Building tool context for analyst: {analyst_role}")
            
            loc = self._extract_location(state)
            
            context = {
                "analyst_role": analyst_role,
                "restaurant_concept": state.get("restaurant_concept", "Restaurant Business"),
                "local_area": loc["local_area"],
                "city": loc["city"],
                "state": loc["state"],
                "pincode": loc["pincode"],
                "investment": state.get("investment", ""),
                "target_demographic": state.get("target_demographic", ""),
                "special_note": state.get("special_note", ""),
            }
            
            # Add full_city for templates that need it
            if loc["city"] and loc["state"]:
                context["full_city"] = f"{loc['city']}, {loc['state']}, India"
            else:
                context["full_city"] = "India"
                
            logger.debug(f"Built context with keys: {list(context.keys())}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to build tool context: {e}")
            raise CustomException(
                f"Tool context building error: {str(e)}",
                "CONTEXT_BUILDING_ERROR",
                {"analyst_role": analyst_role}
            )

    def _build_tool_parameters(self, tool_name: str, context: Dict[str, str]) -> Dict[str, str]:
        """
        Build tool parameters with error handling.
        
        Args:
            tool_name (str): Name of the tool
            context (Dict[str, str]): Context dictionary for parameter templating
            
        Returns:
            Dict[str, str]: Tool parameters dictionary
            
        Raises:
            CustomException: If required parameters are missing or templating fails
        """
        try:
            logger.debug(f"Building parameters for tool: {tool_name}")
            
            tool_cfg = self.tools_config.get(tool_name, {})
            params_cfg = tool_cfg.get("parameters", {})
            
            if not params_cfg:
                logger.warning(f"No parameters configured for tool: {tool_name}")
                return {}

            params = {}
            missing_required = []
            
            for name, cfg in params_cfg.items():
                if not cfg.get("required", True):
                    continue
                    
                template = cfg.get("template", "")
                try:
                    params[name] = template.format(**context)
                except KeyError as e:
                    logger.warning(f"Missing context variable {e} for {tool_name}, using fallback")
                    missing_required.append(str(e))
                    params[name] = f"{context['analyst_role']} {context['restaurant_concept']} in {context['city']}"
            
            if missing_required:
                logger.warning(f"Missing required context variables for {tool_name}: {missing_required}")
                
            logger.debug(f"Built parameters for {tool_name}: {list(params.keys())}")
            return params
            
        except Exception as e:
            logger.error(f"Failed to build tool parameters for {tool_name}: {e}")
            raise CustomException(
                f"Parameter building error for {tool_name}: {str(e)}",
                "PARAMETER_BUILDING_ERROR",
                {"tool_name": tool_name, "context_keys": list(context.keys())}
            )

    def _execute_single_tool(self, tool_name: str, context: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a single tool with comprehensive error handling.
        
        Args:
            tool_name (str): Name of the tool to execute
            context (Dict[str, str]): Context for tool execution
            
        Returns:
            Dict[str, Any]: Tool execution result with metadata
            
        Raises:
            CustomException: If tool execution fails critically
        """
        logger.info(f"Executing tool: {tool_name}")
        
        # Get tool instance
        tool = tool_loader.get(tool_name)
        if not tool:
            error_msg = f"Tool not found: {tool_name}"
            logger.error(error_msg)
            return {
                "tool": tool_name, 
                "status": "failed", 
                "data": {"error": error_msg},
                "execution_time": datetime.now().isoformat()
            }

        try:
            # Build and validate parameters
            params = self._build_tool_parameters(tool_name, context)
            logger.debug(f"Executing {tool_name} with params: {params}")
            
            # Execute tool
            result = tool(params)
            
            # Enhanced error detection
            failed = False
            error_reason = ""
            
            if result is None:
                failed = True
                error_reason = "Tool returned None"
            elif isinstance(result, dict) and not result:
                failed = True
                error_reason = "Tool returned empty dictionary"
            elif isinstance(result, list) and len(result) == 0:
                failed = True
                error_reason = "Tool returned empty list"
            elif isinstance(result, str) and any(err in result.lower() for err in ['error', 'failed', 'not found']):
                failed = True
                error_reason = f"Tool returned error: {result[:100]}"
            elif isinstance(result, dict) and 'error' in str(result).lower():
                failed = True
                error_reason = f"Tool error: {result}"

            # Compile tool result
            tool_result = {
                "tool": tool_name,
                "status": "failed" if failed else "success",
                "data": result if not failed else {"error": error_reason},
                "execution_time": datetime.now().isoformat(),
                "parameters_used": params
            }

            if not failed:
                logger.info(f"✅ Tool {tool_name} executed successfully")
            else:
                logger.warning(f"⚠️ Tool {tool_name} failed: {error_reason}")

            return tool_result

        except CustomException as e:
            logger.error(f"❌ Tool execution failed for {tool_name} with CustomException: {e}")
            return {
                "tool": tool_name, 
                "status": "failed", 
                "data": {"error": str(e), "error_type": e.error_type},
                "execution_time": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Tool execution failed for {tool_name}: {e}")
            raise CustomException(
                f"Tool execution error for {tool_name}: {str(e)}",
                "TOOL_EXECUTION_ERROR",
                {"tool_name": tool_name, "context_keys": list(context.keys())}
            )

    def _process_research_findings(self, findings: List[Dict[str, Any]]) -> str:
        """
        Process research findings into a concise summary without LLM calls.
        
        Args:
            findings (List[Dict[str, Any]]): List of tool execution findings
            
        Returns:
            str: Concatenated summary of successful findings
            
        Raises:
            CustomException: If findings processing fails
        """
        try:
            logger.debug(f"Processing {len(findings)} research findings")
            
            successful_findings = [f for f in findings if f["status"] == "success"]
            
            if not successful_findings:
                logger.warning("No successful research data collected")
                return "No successful research data collected."
            
            # Simple aggregation of successful tool outputs
            tool_summaries = []
            for finding in successful_findings:
                tool_name = finding.get("tool", "Unknown")
                data = finding.get("data", {})
                
                # Extract meaningful content from different data structures
                summary_parts = []
                
                if isinstance(data, dict):
                    # Try to extract key information
                    for key in ["title", "name", "summary", "content", "result", "insight"]:
                        if key in data and isinstance(data[key], str) and len(data[key]) > 10:
                            summary_parts.append(data[key][:150])
                            break
                    
                    # Handle list results
                    if "results" in data and isinstance(data["results"], list):
                        for item in data["results"][:2]:
                            if isinstance(item, dict):
                                for k in ["title", "name", "snippet"]:
                                    if k in item and isinstance(item[k], str):
                                        summary_parts.append(item[k][:100])
                                        break
                    
                    # If no specific content found, note the tool success
                    if not summary_parts:
                        summary_parts.append("Data collected successfully")
                        
                elif isinstance(data, str) and len(data) > 20:
                    summary_parts.append(data[:200])
                else:
                    summary_parts.append("Data available")
                    
                if summary_parts:
                    tool_summaries.append(f"{tool_name}: {' | '.join(summary_parts[:2])}")

            result = " | ".join(tool_summaries) if tool_summaries else "Research data collected from multiple sources"
            logger.debug(f"Processed findings into summary: {result[:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process research findings: {e}")
            raise CustomException(
                f"Findings processing error: {str(e)}",
                "FINDINGS_PROCESSING_ERROR",
                {"findings_count": len(findings)}
            )

    def _build_analysis_context(self, task: Dict[str, Any], state: ResearchState, research_data: str) -> Dict[str, str]:
        """
        Build analysis context with guaranteed variable availability.
        
        Args:
            task (Dict[str, Any]): Research task details
            state (ResearchState): Current research state
            research_data (str): Processed research findings
            
        Returns:
            Dict[str, str]: Context dictionary for analysis generation
            
        Raises:
            CustomException: If context building fails
        """
        try:
            logger.debug(f"Building analysis context for task: {task.get('analyst_role', 'unknown')}")
            
            loc = self._extract_location(state)
            
            context = {
                "analyst_role": task["analyst_role"],
                "affiliation": task["affiliation"],
                "description": task["description"],
                "restaurant_concept": state.get("restaurant_concept", "Restaurant Business"),
                "local_area": loc["local_area"],
                "city": loc["city"],
                "state": loc["state"],
                "pincode": loc["pincode"],
                "investment": state.get("investment", ""),
                "target_demographic": state.get("target_demographic", ""),
                "special_note": state.get("special_note", ""),
                "research_findings": research_data,
                "structured_data": "Research data compiled from multiple sources",
                "analysis_depth": "comprehensive" if len(research_data) > 100 else "preliminary"
            }
            
            logger.debug(f"Built analysis context with keys: {list(context.keys())}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to build analysis context: {e}")
            raise CustomException(
                f"Analysis context building error: {str(e)}",
                "ANALYSIS_CONTEXT_ERROR",
                {"task_keys": list(task.keys()) if isinstance(task, dict) else "unknown"}
            )

    def _parse_analysis_output(self, content: str) -> tuple[str, List[str]]:
        """
        Parse LLM analysis output with robust error handling.
        
        Args:
            content (str): Raw LLM analysis content
            
        Returns:
            tuple[str, List[str]]: Parsed analysis text and list of insights
            
        Raises:
            CustomException: If parsing fails critically
        """
        try:
            logger.debug("Parsing analysis output")
            
            if not content:
                logger.warning("Empty analysis content received")
                return "Professional analysis based on collected research data.", []
                
            analysis = content.strip()
            insights = []

            # Clean common formatting issues
            analysis = analysis.replace("****", "").replace("====", "").replace("```", "")
            
            # Extract insights using multiple patterns
            insight_patterns = [
                r'[-•*]\s*(.+?)(?=\n[-•*]|\n\n|$)',
                r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|$)',
                r'-\s*(.+?)(?=\n-|\n\n|$)',
                r'KEY INSIGHTS?:\s*(.+?)(?=\n\n|$)',
            ]
            
            for pattern in insight_patterns:
                matches = re.findall(pattern, analysis, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    insight = match.strip()
                    if len(insight) > 20 and len(insight) < 500:  # Reasonable length
                        insights.append(insight)

            # Ensure analysis has reasonable content
            if len(analysis) < 50:
                logger.warning("Analysis content too short, using fallback")
                analysis = "Comprehensive analysis based on market research findings."
                
            # Deduplicate and limit insights
            unique_insights = []
            seen = set()
            for insight in insights:
                if insight not in seen and len(insight) > 10:
                    unique_insights.append(insight)
                    seen.add(insight)
                    
            result_insights = unique_insights[:5]  # Limit to top 5 insights
            
            logger.debug(f"Parsed analysis: {len(analysis)} chars, {len(result_insights)} insights")
            
            return analysis, result_insights
            
        except Exception as e:
            logger.error(f"Analysis parsing failed: {e}")
            raise CustomException(
                f"Analysis parsing error: {str(e)}",
                "ANALYSIS_PARSING_ERROR",
                {"content_length": len(content) if content else 0}
            )

    def create_research_tasks(self, state: ResearchState) -> Dict[str, Any]:
        """
        Create research tasks with validation.
        
        Args:
            state (ResearchState): Current research state
            
        Returns:
            Dict[str, Any]: Dictionary with research tasks and empty results
            
        Raises:
            CustomException: If task creation fails
        """
        try:
            logger.info("Creating research tasks")
            
            analysts_team = state.get("analysts_team", [])
            if not analysts_team:
                logger.warning("No analysts team found for research tasks")
                return {"research_tasks": [], "research_results": {}}

            tasks = []
            for analyst in analysts_team:
                if not analyst.tools:
                    logger.warning(f"Analyst {analyst.role} has no tools assigned, skipping")
                    continue
                    
                task = {
                    "analyst_role": analyst.role,
                    "affiliation": analyst.affiliation,
                    "description": analyst.description,
                    "tools": analyst.tools,
                    "expected_output": f"{analyst.role} analysis for {state.get('restaurant_concept', 'restaurant')}"
                }
                tasks.append(task)

            if not tasks:
                logger.error("No valid research tasks created (no analysts with tools)")
                raise CustomException(
                    "No valid research tasks created",
                    "TASK_CREATION_ERROR",
                    {"analysts_count": len(analysts_team)}
                )

            total_tools = sum(len(task["tools"]) for task in tasks)
            logger.info(f"✅ Created {len(tasks)} research tasks with {total_tools} total tool executions")
            
            for task in tasks:
                logger.info(f"🔧 Task: {task['analyst_role']} with {len(task['tools'])} tools")

            return {"research_tasks": tasks, "research_results": {}}
            
        except Exception as e:
            logger.error(f"Failed to create research tasks: {e}")
            raise CustomException(
                f"Research task creation error: {str(e)}",
                "TASK_CREATION_ERROR",
                {"state_keys": list(state.keys()) if isinstance(state, dict) else "unknown"}
            )

    def initiate_parallel_research(self, state: ResearchState):
        """
        Initiate parallel research execution.
        
        Args:
            state (ResearchState): Current research state
            
        Returns:
            Union[Send, str]: Send objects for parallel execution or END if no tasks
            
        Raises:
            CustomException: If research initiation fails
        """
        try:
            tasks = state.get("research_tasks", [])
            if not tasks:
                logger.warning("No research tasks to execute")
                return END

            valid_tasks = [t for t in tasks if t.get("tools")]
            if not valid_tasks:
                logger.error("No tasks with valid tools found")
                return END

            logger.info(f"🚀 Initiating parallel research for {len(valid_tasks)} analysts")
            
            sends = []
            for task in valid_tasks:
                sends.append(
                    Send(
                        "execute_single_analyst_research",
                        {
                            "current_task": task,
                            "current_analyst": task["analyst_role"],
                            "task_timestamp": datetime.now().isoformat()
                        },
                    )
                )
                
            logger.info(f"Created {len(sends)} parallel execution sends")
            return sends
            
        except Exception as e:
            logger.error(f"Failed to initiate parallel research: {e}")
            raise CustomException(
                f"Parallel research initiation error: {str(e)}",
                "RESEARCH_INITIATION_ERROR",
                {"tasks_count": len(state.get("research_tasks", []))}
            )

    def execute_single_analyst_research(self, state: ResearchState) -> Dict[str, Any]:
        """
        Execute research for a single analyst with comprehensive error handling.
        
        Args:
            state (ResearchState): Current research state
            
        Returns:
            Dict[str, Any]: Research results for the analyst
            
        Raises:
            CustomException: If research execution fails critically
        """
        task = state.get("current_task")
        if not task:
            logger.warning("No current task for research execution")
            return {"research_results": {}, "current_analyst": None}

        role = task["analyst_role"]
        logger.info(f"🔍 Executing research for {role}")

        try:
            # Build context and execute tools
            context = self._build_tool_context(state, role)
            findings = []
            
            for tool in task.get("tools", []):
                logger.debug(f"Executing {tool} for {role}")
                tool_result = self._execute_single_tool(tool, context)
                findings.append(tool_result)

            # Process findings without LLM calls
            research_data = self._process_research_findings(findings)
            
            # Generate analysis with LLM
            try:
                analysis_ctx = self._build_analysis_context(task, state, research_data)
                llm_response = self.llm.invoke(self.analysis_prompt.format(**analysis_ctx))
                analysis_content = getattr(llm_response, "content", "")
                analysis_text, insights = self._parse_analysis_output(analysis_content)
            except CustomException as e:
                logger.error(f"Analysis generation failed for {role} with CustomException: {e}")
                analysis_text = f"Professional analysis based on research data. Error: {e.error_type}"
                insights = ["Research completed with available data"]
            except Exception as e:
                logger.error(f"Analysis generation failed for {role}: {e}")
                analysis_text = f"Professional analysis based on research data. Error: {e}"
                insights = ["Research completed with available data"]

            # Compile results
            successful_tools = sum(1 for f in findings if f["status"] == "success")
            total_tools = len(findings)
            success_rate = round(successful_tools / total_tools * 100, 2) if total_tools > 0 else 0

            result = {
                "analyst_role": role,
                "affiliation": task["affiliation"],
                "specialization": task["description"],
                "tools_used": [f["tool"] for f in findings],
                "research_data": findings,
                "expert_analysis": analysis_text,
                "key_insights": insights[:3],
                "timestamp": datetime.now().isoformat(),
                "successful_tools": successful_tools,
                "total_tools": total_tools,
                "success_rate": success_rate,
            }

            logger.info(f"✅ Completed research for {role}: {successful_tools}/{total_tools} tools successful ({success_rate}%)")

            return {
                "research_results": {role: result},
                "current_analyst": role,
            }
            
        except CustomException as e:
            logger.error(f"❌ Research execution failed for {role} with CustomException: {e}")
            return {
                "research_results": {
                    role: {
                        "analyst_role": role,
                        "status": "failed",
                        "error": str(e),
                        "error_type": e.error_type,
                        "timestamp": datetime.now().isoformat()
                    }
                },
                "current_analyst": role,
            }
        except Exception as e:
            logger.error(f"❌ Research execution failed for {role}: {e}")
            raise CustomException(
                f"Research execution error for {role}: {str(e)}",
                "RESEARCH_EXECUTION_ERROR",
                {"analyst_role": role, "tools_count": len(task.get("tools", []))}
            )

    def compile_research_summary(self, state: ResearchState) -> Dict[str, Any]:
        """
        Compile comprehensive research summary.
        
        Args:
            state (ResearchState): Current research state
            
        Returns:
            Dict[str, Any]: Compiled research summary
            
        Raises:
            CustomException: If summary compilation fails
        """
        try:
            logger.info("Compiling research summary")
            
            results = state.get("research_results", {})
            loc = self._extract_location(state)

            if not results:
                logger.warning("No research results to compile")
                return {"research_summary": {"error": "No research results available"}}

            # Aggregate metrics
            insights = []
            tool_count = 0
            successful_tools = 0
            quality_scores = []

            for analyst, result in results.items():
                if isinstance(result, dict) and result.get("status") != "failed":
                    insights.extend(result.get("key_insights", []))
                    tool_count += result.get("total_tools", 0)
                    successful_tools += result.get("successful_tools", 0)
                    # Use success rate as quality proxy
                    quality_scores.append(result.get("success_rate", 0))

            # Calculate overall metrics
            success_rate = round(successful_tools / tool_count * 100, 2) if tool_count > 0 else 0
            avg_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0

            # Determine research quality
            if success_rate > 80 and avg_quality > 70:
                research_quality = "High"
            elif success_rate > 60 and avg_quality > 50:
                research_quality = "Medium"
            else:
                research_quality = "Standard"

            summary = {
                "total_analysts": len([r for r in results.values() if isinstance(r, dict) and r.get("status") != "failed"]),
                "total_tools_executed": tool_count,
                "total_successful_tools": successful_tools,
                "overall_success_rate": success_rate,
                "average_data_quality": avg_quality,
                "research_completed": datetime.now().isoformat(),
                "business_context": {
                    "concept": state.get("restaurant_concept", ""),
                    "location": f"{loc['local_area']}, {loc['city']}, {loc['state']} {loc['pincode']}",
                    "investment": state.get("investment", ""),
                    "target_demographic": state.get("target_demographic", ""),
                },
                "analyst_findings": results,
                "key_insights": list(set(insights))[:self.analysis_config.get("max_key_insights", 5)],
                "research_summary_text": f"Research completed: {len(results)} analysts, {successful_tools}/{tool_count} tools successful ({success_rate}%)",
                "research_quality": research_quality
            }

            logger.info(f"📊 Research summary: {summary['research_summary_text']}")
            logger.debug(f"Research quality: {research_quality}, Average quality: {avg_quality}")

            return {"research_summary": summary}
            
        except Exception as e:
            logger.error(f"Failed to compile research summary: {e}")
            raise CustomException(
                f"Research summary compilation error: {str(e)}",
                "SUMMARY_COMPILATION_ERROR",
                {"results_count": len(state.get("research_results", {}))}
            )

    def _build_graph(self) -> StateGraph:
        """
        Build the parallel research execution graph.
        
        Returns:
            StateGraph: Compiled LangGraph application
            
        Raises:
            CustomException: If graph building fails
        """
        try:
            logger.info("Building parallel research graph")
            
            graph = StateGraph(ResearchState)

            # Add nodes
            graph.add_node("create_research_tasks", self.create_research_tasks)
            graph.add_node("execute_single_analyst_research", self.execute_single_analyst_research)
            graph.add_node("compile_research_summary", self.compile_research_summary)

            # Add edges
            graph.add_edge(START, "create_research_tasks")
            graph.add_conditional_edges("create_research_tasks",
                self.initiate_parallel_research,
                {
                    "execute_single_analyst_research": "execute_single_analyst_research", 
                    END: END
                },
                )
            graph.add_edge("execute_single_analyst_research", "compile_research_summary")
            graph.add_edge("compile_research_summary", END)

            compiled_graph = graph.compile(checkpointer=MemorySaver(), name="ParallelResearchEngine")
            
            logger.info("✅ Parallel research graph built successfully")
            return compiled_graph
            
        except Exception as e:
            logger.error(f"Failed to build research graph: {e}")
            raise CustomException(
                f"Graph building error: {str(e)}",
                "GRAPH_BUILDING_ERROR",
                {"component": "ParallelResearchEngine"}
            )

    def execute_research(self, initial_state: ResearchState) -> Dict[str, Any]:
        """
        Execute the enhanced research pipeline.
        
        Args:
            initial_state (ResearchState): Initial state for research execution
            
        Returns:
            Dict[str, Any]: Research execution results
            
        Raises:
            CustomException: If research execution fails
        """
        from langsmith import uuid7

        logger.info("🚀 Starting enhanced parallel research execution")
        
        try:
            thread_id = str(uuid7())
            logger.debug(f"Using thread_id: {thread_id}")
            
            result = self.app.invoke(
                initial_state,
                {"configurable": {"thread_id": thread_id}},
            )
            
            logger.info("✅ Enhanced parallel research completed successfully")
            return result
            
        except CustomException as e:
            logger.error(f"❌ Enhanced research execution failed with CustomException: {e}")
            # Re-raise CustomException to preserve error context
            raise
        except Exception as e:
            logger.error(f"❌ Enhanced research execution failed: {e}")
            raise CustomException(
                f"Research execution error: {str(e)}",
                "RESEARCH_EXECUTION_ERROR",
                {"initial_state_keys": list(initial_state.keys()) if isinstance(initial_state, dict) else "unknown"}
            )