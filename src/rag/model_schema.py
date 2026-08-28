"""RAG dataclasses: parsed docs, chunks for ingest, chunks from retrieve."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedDocument:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    file_name: str = ""


@dataclass
class DocumentChunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "metadata": self.metadata}


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
