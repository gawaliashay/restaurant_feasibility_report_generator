# src\workflow\research\evidence_processor.py

"""
Evidence Processor.

Normalizes raw tool responses into a common evidence structure.
"""

from typing import Any

from src.configuration.config_loader import config_loader


class EvidenceProcessor:
    """Convert raw tool responses into standardized evidence."""

    def __init__(self) -> None:
        limits = config_loader.get(
            "research.limits",
            {},
        )

        self.max_evidence_chars = limits.get(
            "max_evidence_chars",
            3000,
        )

        self.max_text_per_result = limits.get(
            "max_text_per_result",
            500,
        )

    def process(
        self,
        tool_name: str,
        query: str,
        results: Any,
    ) -> list[dict[str, Any]]:
        """Normalize raw tool results into evidence."""

        if not results:
            return []

        results = self._filter_results(results)

        evidence = []

        for result in results:
            item = self._build_evidence(
                tool_name=tool_name,
                query=query,
                result=result,
            )

            if item:
                evidence.append(item)

        return self._limit_evidence(evidence)

    def _filter_results(
        self,
        results: Any,
    ) -> list[dict[str, Any]]:
        """Return only dictionary results."""

        if isinstance(results, dict):
            return [results]

        if isinstance(results, list):
            return [
                item
                for item in results
                if isinstance(item, dict)
            ]

        return []

    def _build_evidence(
        self,
        tool_name: str,
        query: str,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Create common evidence structure."""

        content = self._extract_content(result)

        if not content:
            return None

        return {
            "tool": tool_name,
            "query": query,
            "source": self._extract_source(
                result,
                tool_name,
            ),
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": content[
                :self.max_text_per_result
            ],
        }

    def _extract_content(
        self,
        result: dict[str, Any],
    ) -> str:
        """Extract text content from a tool result."""

        content = (
            result.get("content")
            or result.get("text")
            or result.get("snippet")
            or result.get("description")
            or ""
        )

        if not isinstance(content, str):
            content = str(content)

        return content.strip()

    def _extract_source(
        self,
        result: dict[str, Any],
        tool_name: str,
    ) -> str:
        """Extract source name from a tool result."""

        return str(
            result.get("source")
            or result.get("source_name")
            or tool_name
        )

    def _limit_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Limit total evidence size."""

        if not evidence:
            return []

        limited = []
        total_chars = 0

        for item in evidence:
            content = item.get("content", "")
            remaining = (
                self.max_evidence_chars
                - total_chars
            )

            if remaining <= 0:
                break

            item = item.copy()
            item["content"] = content[:remaining]

            limited.append(item)

            total_chars += len(item["content"])

        return limited