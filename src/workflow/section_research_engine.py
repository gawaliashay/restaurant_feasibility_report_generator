# src\workflow\section_research_engine.py

"""
Executes YAML-defined research sections using LangGraph with true parallel nodes.
"""

from datetime import datetime
from typing import Any, Dict, List, cast

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langsmith.run_helpers import traceable

from src.common.tool_loader import tool_loader
from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.graph_states.workflow_states import WorkflowState


class SectionResearchEngine:
    """Executes research sections in parallel using LangGraph."""

    def __init__(self):
        config = config_loader.get_all()
        self.sections = config.get("research", {}).get("sections", {})
        self.tools = config.get("tools", {})
        
        quality = config.get('report_quality', {}).get('balanced', {})
        self.max_tool_results = quality.get('max_tool_results_per_section', 15)
        self.max_rag_chunks = quality.get('max_rag_chunks_per_section', 8)
        
        self._workflow = self._build_workflow()

    def _build_context(self, state: WorkflowState) -> Dict[str, str]:
        """Build tool context from state."""
        return {
            "restaurant_concept": state.get("restaurant_concept", ""),
            "investment": state.get("investment", ""),
            "target_demographic": state.get("target_demographic", ""),
            "special_note": state.get("special_note", ""),
            "society": state.get("society", ""),
            "local_area": state.get("local_area", ""),
            "city": state.get("city", ""),
            "state": state.get("state", ""),
            "pincode": state.get("pincode", ""),
        }

    def build_tasks(self, state: WorkflowState) -> WorkflowState:
        """Build research tasks from enabled sections."""
        tasks = []
        for name, config in self.sections.items():
            if config.get("enabled"):
                tasks.append({
                    "section": name,
                    "title": config.get("title", name),
                    "tools": config.get("tools", []),
                    "dependencies": config.get("dependencies", []),
                })
        
        logger.info("Created %s research tasks", len(tasks))
        return {"research_tasks": tasks}

    def execute_section(self, state: WorkflowState, section_name: str) -> WorkflowState:
        """Execute a single research section."""
        task = next((t for t in state.get("research_tasks", []) if t["section"] == section_name), None)
        if not task:
            logger.warning("Task not found: %s", section_name)
            return {}
        
        logger.info("Executing section: %s", section_name)
        
        context = self._build_context(state)
        findings = self._get_findings(state, task, context)
        
        return {
            "research_results": {
                section_name: {
                    "section": section_name,
                    "title": task.get("title"),
                    "tools_used": task.get("tools"),
                    "research_data": findings,
                    "evidence": self._build_evidence(findings),
                    "timestamp": datetime.now().isoformat(),
                }
            }
        }

    def _get_findings(self, state: WorkflowState, task: Dict[str, Any], context: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get findings from tools or dependencies."""
        # Synthesis section - use dependencies
        if not task.get("tools") and task.get("dependencies"):
            return self._synthesize_from_dependencies(state, task["dependencies"])
        
        # Research section - execute tools
        findings = []
        for tool_name in task.get("tools", []):
            findings.append(self._execute_tool(tool_name, context))
        return findings

    def _synthesize_from_dependencies(self, state: WorkflowState, dependencies: List[str]) -> List[Dict[str, Any]]:
        """Synthesize evidence from dependency sections."""
        findings = []
        research_results = state.get("research_results", {})
        
        for dep in dependencies:
            dep_result = research_results.get(dep, {})
            evidence = dep_result.get("evidence", "")
            title = dep_result.get("title", dep)
            
            if evidence:
                findings.append({
                    "tool": f"synthesis_from_{dep}",
                    "status": "success",
                    "data": {"source": dep},
                    "summary": f"Evidence from {title}:\n{evidence}"
                })
            else:
                logger.warning(f"No evidence from dependency: {dep}")
                findings.append({
                    "tool": f"synthesis_from_{dep}",
                    "status": "warning",
                    "summary": f"No evidence available from {dep}"
                })
        
        return findings

    def aggregate_results(self, state: WorkflowState) -> WorkflowState:
        """Aggregate all research results."""
        completed = list(state.get("research_results", {}).keys())
        logger.info("All sections completed: %s", completed)
        return {"completed_sections": completed}

    def _execute_tool(self, tool_name: str, context: Dict[str, str]) -> Dict[str, Any]:
        """Execute a tool - NO special cases."""
        tool = tool_loader.get(tool_name)
        if not tool:
            return {"tool": tool_name, "status": "failed", "error": "Tool not found"}
        
        try:
            # Build params from config
            params = {}
            tool_config = self.tools.get(tool_name, {})
            
            for param_name, param_config in tool_config.get("parameters", {}).items():
                template = param_config.get("template")
                if isinstance(template, str):
                    params[param_name] = template.format(**context)
                elif isinstance(template, list):
                    params[param_name] = [t.format(**context) for t in template]
            
            # Execute tool - tool handles its own summarization
            result = tool(params)
            
            return result
        except Exception as e:
            logger.exception("%s failed", tool_name)
            return {"tool": tool_name, "status": "failed", "error": str(e)}

    def _build_evidence(self, findings: List[Any]) -> str:
        """Build evidence from findings using tool-provided summaries."""
        parts = []
        for item in findings:
            if isinstance(item, dict) and item.get("status") == "success":
                parts.append(item.get("summary", str(item)))
            else:
                parts.append(str(item))
        return "\n\n".join(parts)

    def _build_workflow(self):
        """Build parallel LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        workflow.add_node("build_tasks", self.build_tasks)
        
        for name in self.sections:
            if self.sections[name].get("enabled"):
                def make_executor(section_name: str):
                    def executor(state: WorkflowState, config: Any = None) -> WorkflowState:
                        return self.execute_section(state, section_name)
                    return executor
                workflow.add_node(f"execute_{name}", make_executor(name))
        
        workflow.add_node("aggregate", self.aggregate_results)
        
        workflow.add_edge(START, "build_tasks")
        
        for name in self.sections:
            if self.sections[name].get("enabled"):
                workflow.add_edge("build_tasks", f"execute_{name}")
        
        for name, config in self.sections.items():
            if not config.get("enabled"):
                continue
            for dep in config.get("dependencies", []):
                if dep in self.sections and self.sections[dep].get("enabled"):
                    workflow.add_edge(f"execute_{dep}", f"execute_{name}")
        
        for name in self.sections:
            if self.sections[name].get("enabled"):
                workflow.add_edge(f"execute_{name}", "aggregate")
        
        workflow.add_edge("aggregate", END)
        
        return workflow.compile(checkpointer=MemorySaver())

    @traceable(name="Phase 1: execute section_research")
    def execute_research(self, state: WorkflowState) -> WorkflowState:
        """Execute research workflow."""
        from src.utils.create_unique_uuid import generate_uuid
        
        result = self._workflow.invoke(
            state,
            {"configurable": {"thread_id": generate_uuid()}},
        )
        return cast(WorkflowState, result)