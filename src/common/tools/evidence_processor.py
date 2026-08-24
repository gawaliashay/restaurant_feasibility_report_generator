# src/common/tools/evidence_processor.py

"""
Evidence Processor.

Convert raw tool results into standardized evidence.
Also: dedupe, rank, cap length, and collect sources.
"""

from typing import Any
from urllib.parse import urlparse

from src.common.schemas import EvidenceItem
from src.configuration.config_loader import config_loader

MAX_SOURCE_CHARS = 80


CONTENT_FIELDS = ["content", "text", "snippet", "description", "title", "name", "rating", "reviews", "price"]
TITLE_FIELDS = ["title", "name"]
URL_FIELDS = ["url", "link", "website"]
SOURCE_FIELDS = ["source", "source_name", "type", "category"]
EXTRA_FIELDS = [
    "rating", "reviews", "price", "address", "hours", "score",
    "document_name", "date", "value", "chunk_index",
]


class EvidenceProcessor:
    """Convert raw tool results into standardized evidence."""

    def process(self, tool_name: str, query: str, results: Any) -> list[dict[str, Any]]:
        """Convert raw tool results into EvidenceItem dicts."""
        if not results:
            return []

        if not isinstance(results, list):
            results = [results] if isinstance(results, dict) else []

        mode = config_loader.get("resource_limits.mode", "fast")
        limits = config_loader.get(f"resource_limits.{mode}", {})
        max_text_per_result = limits.get("max_text_per_result", 300)

        evidence = []

        for item in results:
            if not isinstance(item, dict):
                continue

            content = self._get_content(item)
            if not content:
                continue

            raw = {
                "tool": tool_name,
                "query": query,
                "source": self._get_source(item, tool_name),
                "title": self._get_title(item),
                "url": self._get_url(item),
                "content": content[:max_text_per_result],
                "extra": self._get_extra(item),
            }
            evidence.append(EvidenceItem.model_validate(raw).model_dump())

        return evidence

    @staticmethod
    def dedupe(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop duplicates. Key includes content so RAG chunks from one PDF stay distinct."""
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []

        for item in evidence:
            key = (
                f"{item.get('source', '')}:"
                f"{item.get('title', '')}:"
                f"{item.get('content', '')[:80]}"
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return unique

    @staticmethod
    def sort_by_score(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Highest score first. Items without a score go last."""

        def score_key(item: dict[str, Any]) -> tuple[int, float]:
            score = (item.get("extra") or {}).get("score")
            if score is None:
                return (0, 0.0)
            return (1, float(score))

        return sorted(evidence, key=score_key, reverse=True)

    @staticmethod
    def limit_by_chars(
        evidence: list[dict[str, Any]],
        max_chars: int,
    ) -> list[dict[str, Any]]:
        """Keep items until the total content length hits max_chars."""
        if not evidence or max_chars <= 0:
            return []

        limited: list[dict[str, Any]] = []
        total_chars = 0

        for item in evidence:
            content = item.get("content", "")
            remaining = max_chars - total_chars
            if remaining <= 0:
                break

            item_copy = item.copy()
            item_copy["content"] = content[:remaining]
            limited.append(item_copy)
            total_chars += len(item_copy["content"])

        return limited

    @staticmethod
    def _clip_source(text: str, max_chars: int = MAX_SOURCE_CHARS) -> str:
        """First line only, capped so citations cannot dump a social caption."""
        text = (text or "").strip()
        if not text:
            return ""
        text = text.split("\n", 1)[0].strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    @staticmethod
    def _hostname(url: str) -> str:
        if not url:
            return ""
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host

    @staticmethod
    def collect_sources(evidence: list[dict[str, Any]]) -> list[str]:
        """Unique short source labels, falling back to tool name."""
        sources: list[str] = []
        seen: set[str] = set()

        for item in evidence:
            name = EvidenceProcessor._clip_source(
                item.get("source") or item.get("tool") or ""
            )
            if not name or name in seen:
                continue
            seen.add(name)
            sources.append(name)

        return sources

    def _get_content(self, item: dict[str, Any]) -> str:
        """Extract main textual content."""
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

        if "query" in item and "value" in item:
            return f"{item['query']}: {item['value']}"

        if "date" in item and "value" in item:
            return f"{item['date']}: {item['value']}"

        primary = ""
        for field in CONTENT_FIELDS:
            if item.get(field):
                primary = str(item[field]).strip()
                break

        extra = self._get_extra(item)
        if extra:
            parts = [f"{k}: {v}" for k, v in extra.items() if v]
            if parts:
                suffix = " | ".join(parts)
                primary = f"{primary} | {suffix}" if primary else suffix

        return primary

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
        """Short citation label. Never a full snippet or social caption."""
        if tool_name == "google_maps":
            return "google_maps"

        metadata = item.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("document_name"):
            return self._clip_source(str(metadata["document_name"]))

        host = self._hostname(self._get_url(item))
        if host:
            return host

        title = item.get("title") or item.get("name")
        if title:
            return self._clip_source(str(title))

        for field in SOURCE_FIELDS:
            value = item.get(field)
            if value:
                return self._clip_source(str(value))

        if item.get("query"):
            return self._clip_source(str(item["query"]))

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
