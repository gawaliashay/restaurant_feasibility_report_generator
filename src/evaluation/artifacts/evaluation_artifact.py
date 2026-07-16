# src\evaluation\artifacts\evaluation_artifact.py

from pydantic import BaseModel, Field

from .input_artifact import InputArtifact
from .workflow_artifact import WorkflowArtifact
from .llm_artifact import LLMArtifact
from .tool_artifact import ToolArtifact
from .rag_artifact import RagArtifact
from .report_artifact import ReportArtifact
from .metadata_artifact import MetadataArtifact


class EvaluationArtifact(BaseModel):

    inputs: InputArtifact = Field(default_factory=InputArtifact)

    workflow: WorkflowArtifact = Field(default_factory=WorkflowArtifact)

    llm: LLMArtifact = Field(default_factory=LLMArtifact)

    tools: ToolArtifact = Field(default_factory=ToolArtifact)

    rag: RagArtifact = Field(default_factory=RagArtifact)

    report: ReportArtifact = Field(default_factory=ReportArtifact)

    metadata: MetadataArtifact = Field(default_factory=MetadataArtifact)