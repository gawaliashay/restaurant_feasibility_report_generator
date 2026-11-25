# src/common/schemas.py

"""
Pipeline contracts for research and report nodes.

WorkflowState stays a TypedDict by choice (dict transport + Annotated reducers).
These models validate payloads at node boundaries, then are stored as dicts.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """One normalized tool result. Output of EvidenceProcessor."""

    tool: str
    query: str
    content: str
    source: str = ""
    title: str = ""
    url: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class ResearchSectionResult(BaseModel):
    """Return value of one research section node."""

    section: str
    status: Literal["success", "failed", "skipped"]
    evidence: list[EvidenceItem] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ReportSectionResult(BaseModel):
    """Return value of one report section node."""

    section: str
    status: Literal["success", "failed", "skipped"]
    report: str = ""
    sources: list[str] = Field(default_factory=list)
    error: str | None = None
