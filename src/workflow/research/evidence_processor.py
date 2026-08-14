"""
Evidence Processor.

Converts tool results into standardized evidence structure.
Assumes data is already normalized as a list of dictionaries.
"""

from typing import Any

from src.configuration.config_loader import config_loader


class EvidenceProcessor:
    """Convert tool results into standardized evidence."""

    def __init__(self) -> None:
        limits = config_loader.get("research.limits", {})
        self.max_evidence_chars = limits.get("max_evidence_chars", 3000)
        self.max_text_per_result = limits.get("max_text_per_result", 500)

    def process(
        self,
        tool_name: str,
        query: str,
        results: Any,
    ) -> list[dict[str, Any]]:
        """
        Convert results into evidence.

        Args:
            tool_name: Name of the tool that produced the results
            query: The query that was used
            results: List of result items (already normalized)

        Returns:
            List of evidence items
        """
        if not results:
            return []

        # Ensure results is a list
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
            })

        return self._limit_evidence(evidence)

    def _get_content(self, item: dict[str, Any]) -> str:
        """
        Extract text content from a result item.
        Handles multiple data formats: Tavily, Google Maps, Google Trends, RAG.
        """
        
        # ✅ Handle Google Trends data (values list)
        if "values" in item and isinstance(item["values"], list):
            value_strs = []
            for v in item["values"]:
                if isinstance(v, dict):
                    query = v.get("query", "")
                    value = v.get("value", "")
                    if query and value:
                        value_strs.append(f"{query}: {value}")
            if value_strs:
                return " | ".join(value_strs)
        
        # ✅ Handle Google Trends data (single value)
        if "query" in item and "value" in item:
            return f"{item['query']}: {item['value']}"
        
        if "date" in item and "value" in item:
            return f"{item['date']}: {item['value']}"
        
        # ✅ Handle Tavily / General content
        if "content" in item and item["content"]:
            return str(item["content"]).strip()
        
        if "text" in item and item["text"]:
            return str(item["text"]).strip()
        
        if "snippet" in item and item["snippet"]:
            return str(item["snippet"]).strip()
        
        if "description" in item and item["description"]:
            return str(item["description"]).strip()
        
        # ✅ Fallback: use title or name
        if "title" in item and item["title"]:
            return str(item["title"]).strip()
        
        if "name" in item and item["name"]:
            return str(item["name"]).strip()
        
        return ""

    def _get_title(self, item: dict[str, Any]) -> str:
        """
        Extract title from a result item.
        Handles multiple data formats.
        """
        
        # ✅ Handle Google Trends (values list)
        if "values" in item and isinstance(item["values"], list):
            for v in item["values"]:
                if isinstance(v, dict) and v.get("query"):
                    return str(v["query"])
        
        # ✅ Handle Google Trends (single query)
        if "query" in item:
            return str(item["query"])
        
        # ✅ Handle date as title
        if "date" in item:
            return str(item["date"])
        
        # ✅ Handle Tavily / General
        if "title" in item and item["title"]:
            return str(item["title"])
        
        if "name" in item and item["name"]:
            return str(item["name"])
        
        return ""

    def _get_url(self, item: dict[str, Any]) -> str:
        """Extract URL from a result item."""
        for field in ["url", "link", "website"]:
            if field in item and item[field]:
                return str(item[field])
        return ""

    def _get_source(self, item: dict[str, Any], tool_name: str) -> str:
        """Extract source from a result item."""
        # Check for source fields
        for field in ["source", "source_name", "type", "category"]:
            if field in item and item[field]:
                return str(item[field])
        
        # For Google Trends, use the query as source
        if "query" in item:
            return str(item["query"])
        
        return tool_name

    def _limit_evidence(self, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Limit total evidence size."""
        if not evidence:
            return []

        limited = []
        total_chars = 0

        for item in evidence:
            content = item.get("content", "")
            remaining = self.max_evidence_chars - total_chars

            if remaining <= 0:
                break

            item = item.copy()
            item["content"] = content[:remaining]

            limited.append(item)
            total_chars += len(item["content"])

        return limited