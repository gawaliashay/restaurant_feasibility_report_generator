# src/evaluation/builders/artifact_builder.py

"""
Builds a standardized EvaluationArtifact from a workflow execution.
"""

from datetime import datetime

from src.graph_states.workflow_states import WorkflowState
from src.configuration.config_loader import config_loader

from src.evaluation.artifacts.evaluation_artifact import EvaluationArtifact
from src.evaluation.artifacts.input_artifact import InputArtifact
from src.evaluation.artifacts.workflow_artifact import WorkflowArtifact
from src.evaluation.artifacts.report_artifact import ReportArtifact
from src.evaluation.artifacts.metadata_artifact import MetadataArtifact
from src.evaluation.artifacts.llm_artifact import LLMArtifact
from src.evaluation.artifacts.tool_artifact import ToolArtifact
from src.evaluation.artifacts.rag_artifact import RagArtifact


class ArtifactBuilder:
    """
    Converts a WorkflowState into a standardized EvaluationArtifact.

    The builder performs no evaluation logic.
    It only extracts execution data into a reusable artifact.
    """

    def build(
        self,
        workflow_state: WorkflowState,
    ) -> EvaluationArtifact:
        """
        Build an EvaluationArtifact from workflow state.
        """

        return EvaluationArtifact(
            inputs=self._build_inputs(workflow_state),
            workflow=self._build_workflow(workflow_state),
            report=self._build_report(workflow_state),
            metadata=self._build_metadata(workflow_state),
            llm=self._build_llm(),
            tools=self._build_tools(),
            rag=self._build_rag(),
        )

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    def _build_inputs(
        self,
        workflow_state: WorkflowState,
    ) -> InputArtifact:

        return InputArtifact(
            restaurant_concept=workflow_state.get("restaurant_concept"),
            investment=workflow_state.get("investment"),
            target_demographic=workflow_state.get("target_demographic"),
            special_note=workflow_state.get("special_note"),
            society=workflow_state.get("society"),
            local_area=workflow_state.get("local_area"),
            city=workflow_state.get("city"),
            state=workflow_state.get("state"),
            pincode=workflow_state.get("pincode"),
        )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def _build_workflow(
        self,
        workflow_state: WorkflowState,
    ) -> WorkflowArtifact:

        completed_nodes = workflow_state.get("completed_sections", [])

        return WorkflowArtifact(
            workflow_name=config_loader.get("app.name"),
            # workflow_status=self._get_workflow_status(workflow_state),
            completed_nodes=completed_nodes,
        )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def _build_report(
        self,
        workflow_state: WorkflowState,
    ) -> ReportArtifact:

        report = workflow_state.get("final_report", {})

        return ReportArtifact(
            report=report,
            report_size=len(str(report)),
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _build_metadata(
        self,
        workflow_state: WorkflowState,
    ) -> MetadataArtifact:

        timestamp = workflow_state.get("report_timestamp")

        created_at = None

        if timestamp:
            try:
                created_at = datetime.fromisoformat(timestamp)
            except ValueError:
                created_at = None

        return MetadataArtifact(
            workflow_id=workflow_state.get("workflow_id"),
            created_at=created_at,
        )

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def _build_llm(self) -> LLMArtifact:
        """
        Placeholder.

        LLM observability will populate this artifact later.
        """

        return LLMArtifact()

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _build_tools(self) -> ToolArtifact:
        """
        Placeholder.

        Tool observability will populate this artifact later.
        """

        return ToolArtifact()

    # ------------------------------------------------------------------
    # RAG
    # ------------------------------------------------------------------

    def _build_rag(self) -> RagArtifact:
        """
        Placeholder.

        RAG observability will populate this artifact later.
        """

        return RagArtifact()


artifact_builder = ArtifactBuilder()