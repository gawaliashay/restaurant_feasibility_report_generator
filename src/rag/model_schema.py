"""
Generic data schemas for RAG pipeline.

Contains:
- ParsedDocument
- DocumentChunk
- RetrievedChunk

No business-specific fields.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ParsedDocument:
    """Represents parsed document content. Output of parser layer."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_name: str = ""

    @property
    def text_length(self) -> int:
        return len(self.content)


@dataclass
class DocumentChunk:
    """Represents a chunk created during ingestion. Used before storing."""
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "metadata": self.metadata}


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk. Output of retriever layer."""
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "score": self.score, "metadata": self.metadata}