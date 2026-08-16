# src/common/tools/evidence_processor.py

"""
Evidence Processor.

Convert raw tool results into standardized evidence.
Tool-agnostic - works with any tool.
"""

from typing import Any
from src.configuration.config_loader import config_loader


# ============================================================
# FIELD DEFINITIONS
# ============================================================

CONTENT_FIELDS = ["content", "text", "snippet", "description", "title", "name"]
TITLE_FIELDS = ["title", "name"]
URL_FIELDS = ["url", "link", "website"]
SOURCE_FIELDS = ["source", "source_name", "type", "category"]
EXTRA_FIELDS = ["rating", "reviews", "price", "address", "hours", "score", "document_name", "date", "value"]


class EvidenceProcessor:
    """Convert raw tool results into standardized evidence."""

    def __init__(self) -> None:
        limits = config_loader.get("research.limits", {})
        if limits is None:
            limits = {}

        self.max_evidence_chars = limits.get("max_evidence_chars", 3000)
        self.max_text_per_result = limits.get("max_text_per_result", 500)

    def process(self, tool_name: str, query: str, results: Any) -> list[dict[str, Any]]:
        """Convert raw tool results into standardized evidence."""
        if not results:
            return []

        if not isinstance(results, list):
            results = [results] if isinstance(results, dict) else []

        evidence = []

        for item in results:
            if not isinstance(item, dict):
                continue

            content = self._get_content(item)

            if not content:
                continue

            evidence.append({
                "tool": tool_name,
                "query": query,
                "source": self._get_source(item, tool_name),
                "title": self._get_title(item),
                "url": self._get_url(item),
                "content": content[:self.max_text_per_result],
                "extra": self._get_extra(item),
            })

        return self._limit_evidence(evidence)

    def _get_content(self, item: dict[str, Any]) -> str:
        """Extract main textual content."""
        # Google Trends (values list)
        if "values" in item and isinstance(item["values"], list):
            parts = []

            for v in item["values"]:
                if not isinstance(v, dict):
                    continue

                query = v.get("query")
                value = v.get("value")

                if query and value:
                    parts.append(f"{query}: {value}")

            if parts:
                return " | ".join(parts)

        # Google Trends (single)
        if "query" in item and "value" in item:
            return f"{item['query']}: {item['value']}"

        if "date" in item and "value" in item:
            return f"{item['date']}: {item['value']}"

        # Generic fields
        for field in CONTENT_FIELDS:
            value = item.get(field)

            if value:
                return str(value).strip()

        return ""

    def _get_title(self, item: dict[str, Any]) -> str:
        """Extract a title from the raw result."""
        if "values" in item and isinstance(item["values"], list):
            for v in item["values"]:
                if isinstance(v, dict) and v.get("query"):
                    return str(v["query"])

        if item.get("query"):
            return str(item["query"])

        if item.get("date"):
            return str(item["date"])

        for field in TITLE_FIELDS:
            value = item.get(field)

            if value:
                return str(value).strip()

        return ""

    def _get_url(self, item: dict[str, Any]) -> str:
        """Extract a source URL."""
        for field in URL_FIELDS:
            value = item.get(field)

            if value:
                return str(value).strip()

        return ""

    def _get_source(self, item: dict[str, Any], tool_name: str) -> str:
        """Extract source information."""
        for field in SOURCE_FIELDS:
            value = item.get(field)

            if value:
                return str(value).strip()

        if item.get("query"):
            return str(item["query"]).strip()

        return tool_name

    def _get_extra(self, item: dict[str, Any]) -> dict[str, Any]:
        """Preserve useful structured fields."""
        extra = {}
        metadata = item.get("metadata", {})

        for field in EXTRA_FIELDS:
            if field in item:
                extra[field] = item[field]
            elif isinstance(metadata, dict) and field in metadata:
                extra[field] = metadata[field]

        return extra

    def _limit_evidence(self, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Limit total evidence content size."""
        if not evidence:
            return []

        limited = []
        total_chars = 0

        for item in evidence:
            content = item.get("content", "")
            remaining = self.max_evidence_chars - total_chars

            if remaining <= 0:
                break

            item_copy = item.copy()
            item_copy["content"] = content[:remaining]

            limited.append(item_copy)
            total_chars += len(item_copy["content"])

        return limited