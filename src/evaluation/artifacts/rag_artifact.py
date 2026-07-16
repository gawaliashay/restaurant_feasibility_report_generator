# src\evaluation\artifacts\rag_artifact.py

from pydantic import BaseModel, Field


class RagArtifact(BaseModel):

    query: str | None = None

    retrieved_documents: int | None = None

    retrieval_latency_ms: float | None = None

    metadata: dict = Field(default_factory=dict)