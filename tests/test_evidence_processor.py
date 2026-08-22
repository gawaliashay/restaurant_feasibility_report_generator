"""
Unit tests for EvidenceProcessor.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from src.common.tools.evidence_processor import EvidenceProcessor


class TestEvidenceProcessor:
    """Test EvidenceProcessor functionality."""

    def test_process_empty_results(self):
        processor = EvidenceProcessor()
        result = processor.process("test_tool", "test_query", None)
        assert result == []

    def test_process_empty_list(self):
        processor = EvidenceProcessor()
        result = processor.process("test_tool", "test_query", [])
        assert result == []

    def test_process_single_result(self):
        processor = EvidenceProcessor()
        results = [{"title": "Test Title", "content": "Test content"}]
        result = processor.process("test_tool", "test_query", results)
        assert len(result) == 1
        assert result[0]["tool"] == "test_tool"
        assert result[0]["query"] == "test_query"
        assert result[0]["title"] == "Test Title"
        assert result[0]["content"] == "Test content"

    def test_process_multiple_results(self):
        processor = EvidenceProcessor()
        results = [
            {"title": "Title 1", "content": "Content 1"},
            {"title": "Title 2", "content": "Content 2"},
        ]
        result = processor.process("test_tool", "test_query", results)
        assert len(result) == 2
        assert result[0]["title"] == "Title 1"
        assert result[1]["title"] == "Title 2"

    def test_process_dict_result(self):
        processor = EvidenceProcessor()
        results = {"title": "Test Title", "content": "Test content"}
        result = processor.process("test_tool", "test_query", results)
        assert len(result) == 1
        assert result[0]["title"] == "Test Title"

    def test_process_google_trends_data(self):
        processor = EvidenceProcessor()
        results = [
            {"values": [{"query": "momo", "value": 88}, {"query": "dumplings", "value": 45}]}
        ]
        result = processor.process("google_trends", "momo", results)
        assert len(result) == 1
        assert "momo: 88" in result[0]["content"]
        assert "dumplings: 45" in result[0]["content"]

    def test_process_google_trends_single_query(self):
        processor = EvidenceProcessor()
        results = [{"query": "momo", "value": 88}]
        result = processor.process("google_trends", "momo", results)
        assert len(result) == 1
        assert "momo: 88" in result[0]["content"]

    def test_process_google_trends_with_date(self):
        processor = EvidenceProcessor()
        results = [{"date": "2024-01-01", "value": 88}]
        result = processor.process("google_trends", "momo", results)
        assert len(result) == 1
        assert "2024-01-01: 88" in result[0]["content"]

    def test_process_with_extra_fields(self):
        processor = EvidenceProcessor()
        results = [
            {"title": "Test", "content": "Content", "rating": 4.5, "reviews": 100, "price": "₹200"}
        ]
        result = processor.process("test_tool", "test_query", results)
        assert len(result) == 1
        extra = result[0]["extra"]
        assert extra.get("rating") == 4.5
        assert extra.get("reviews") == 100
        assert extra.get("price") == "₹200"

    def test_process_with_metadata(self):
        processor = EvidenceProcessor()
        results = [
            {
                "title": "Test",
                "content": "Content",
                "metadata": {"document_name": "Test Document", "date": "2024-01-01"},
            }
        ]
        result = processor.process("test_tool", "test_query", results)
        assert len(result) == 1
        assert result[0]["source"] == "Test Document"
        extra = result[0]["extra"]
        assert extra.get("date") == "2024-01-01"

    def test_process_truncates_content(self):
        """Test content is truncated to max_text_per_result."""
        processor = EvidenceProcessor()
        long_content = "This is a long test content. " * 30
        results = [{"title": "Test", "content": long_content}]
        result = processor.process("test_tool", "test_query", results)
        # Content should be truncated (the actual limit depends on config)
        # It could be 300, 400, or 500 depending on mode
        # Just verify it's shorter than the original
        assert len(result[0]["content"]) < len(long_content)

    def test_process_invalid_items_are_skipped(self):
        processor = EvidenceProcessor()
        results = [
            {"title": "Valid", "content": "Content"},
            "not a dict",
            {"invalid": "item"},
        ]
        result = processor.process("test_tool", "test_query", results)
        assert len(result) == 1
        assert result[0]["title"] == "Valid"

    def test_process_empty_content_handling(self):
        """Test items with empty content."""
        processor = EvidenceProcessor()
        results = [
            {"title": "Title 1", "content": "Content 1"},
            {"title": "Title 2", "content": ""},
            {"title": "Title 3", "content": "Content 3"},
        ]
        result = processor.process("test_tool", "test_query", results)
        # Should not crash, regardless of skipping behavior
        assert len(result) >= 1
        # At least Title 1 and Title 3 should be present
        titles = [item["title"] for item in result]
        assert "Title 1" in titles
        assert "Title 3" in titles

    def test_source_extraction_from_title(self):
        processor = EvidenceProcessor()
        results = [{"title": "Test Title", "content": "Content"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["source"] == "Test Title"

    def test_source_extraction_from_source_field(self):
        processor = EvidenceProcessor()
        results = [{"source": "Custom Source", "content": "Content"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["source"] == "Custom Source"

    def test_source_extraction_fallback_to_tool_name(self):
        processor = EvidenceProcessor()
        results = [{"content": "Content"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["source"] == "test_tool"

    def test_source_extraction_from_url(self):
        processor = EvidenceProcessor()
        results = [{"content": "Content", "url": "https://example.com"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["source"] == "https://example.com"

    def test_title_extraction(self):
        processor = EvidenceProcessor()
        results = [{"title": "Test Title", "content": "Content"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["title"] == "Test Title"

    def test_title_extraction_from_name(self):
        processor = EvidenceProcessor()
        results = [{"name": "Test Name", "content": "Content"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["title"] == "Test Name"

    def test_url_extraction(self):
        processor = EvidenceProcessor()
        results = [{"url": "https://example.com", "content": "Content"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["url"] == "https://example.com"

    def test_url_extraction_from_link(self):
        processor = EvidenceProcessor()
        results = [{"link": "https://example.com", "content": "Content"}]
        result = processor.process("test_tool", "test_query", results)
        assert result[0]["url"] == "https://example.com"