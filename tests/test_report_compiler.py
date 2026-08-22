"""
Unit tests for ReportCompiler.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime
from src.workflow.report.report_compiler import ReportCompiler


class TestReportCompiler:
    """Test ReportCompiler functionality."""

    def test_compiler_creates_instance(self):
        """Test that ReportCompiler can be instantiated."""
        compiler = ReportCompiler()
        assert compiler is not None
        assert hasattr(compiler, "compile")

    def test_compile_empty_state(self):
        """Test compiling with empty state."""
        compiler = ReportCompiler()
        state = {
            "section_reports": {},
            "research_results": {},
            "restaurant_concept": "Test",
            "local_area": "Test Area",
            "city": "Test City",
        }
        result = compiler.compile(state)
        assert "# RESTAURANT FEASIBILITY REPORT" in result
        assert "Test" in result

    def test_compile_with_section_reports(self):
        """Test compiling with section reports."""
        compiler = ReportCompiler()
        state = {
            "section_reports": {
                "market_report": {
                    "status": "success",
                    "report": "## Market Analysis\nTest market content",
                },
                "competitive_report": {
                    "status": "success",
                    "report": "## Competitive Analysis\nTest competitive content",
                },
            },
            "research_results": {},
            "restaurant_concept": "Test Restaurant",
            "local_area": "Test Area",
            "city": "Test City",
        }
        result = compiler.compile(state)
        assert "# RESTAURANT FEASIBILITY REPORT" in result
        assert "Market Analysis" in result
        assert "Competitive Analysis" in result

    def test_compile_with_research_evidence(self):
        """Test compiling with research evidence count."""
        compiler = ReportCompiler()
        state = {
            "section_reports": {},
            "research_results": {
                "market_analysis": {"evidence": ["item1", "item2"]},
                "competitive_analysis": {"evidence": ["item3"]},
            },
            "restaurant_concept": "Test Restaurant",
            "local_area": "Test Area",
            "city": "Test City",
        }
        result = compiler.compile(state)
        # Total evidence should be 3
        assert "3 evidence items" in result

    def test_compile_with_header(self):
        """Test header generation."""
        compiler = ReportCompiler()
        state = {
            "restaurant_concept": "Test Restaurant",
            "local_area": "Test Area",
            "city": "Test City",
            "investment": "₹500,000",
            "section_reports": {},
            "research_results": {},
        }
        result = compiler.compile(state)
        assert "# RESTAURANT FEASIBILITY REPORT" in result
        assert "**Concept:** Test Restaurant" in result
        assert "**Location:** Test Area, Test City" in result
        assert "**Investment:** ₹500,000" in result

    def test_compile_with_executive_summary(self):
        """Test executive summary generation."""
        compiler = ReportCompiler()
        state = {
            "section_reports": {
                "market_report": {
                    "status": "success",
                    "report": "## Market Overview\nThis is a test market summary.",
                }
            },
            "research_results": {"market_analysis": {"evidence": ["item1"]}},
            "restaurant_concept": "Test Restaurant",
            "local_area": "Test Area",
            "city": "Test City",
            "investment": "₹500,000",
        }
        result = compiler.compile(state)
        assert "## Executive Summary" in result
        assert "Test Restaurant" in result

    def test_compile_with_risk_assessment(self):
        """Test risk assessment section inclusion."""
        compiler = ReportCompiler()
        state = {
            "section_reports": {
                "risk_assessment": {
                    "status": "success",
                    "report": "## Risk Assessment\nTest risk content",
                }
            },
            "research_results": {},
            "restaurant_concept": "Test Restaurant",
            "local_area": "Test Area",
            "city": "Test City",
            "investment": "₹500,000",
        }
        result = compiler.compile(state)
        assert "Risk Assessment" in result

    def test_compile_with_recommendations(self):
        """Test recommendations section inclusion."""
        compiler = ReportCompiler()
        state = {
            "section_reports": {
                "strategic_recommendations": {
                    "status": "success",
                    "report": "## Strategic Recommendations\nTest recommendation content",
                }
            },
            "research_results": {},
            "restaurant_concept": "Test Restaurant",
            "local_area": "Test Area",
            "city": "Test City",
            "investment": "₹500,000",
        }
        result = compiler.compile(state)
        assert "Strategic Recommendations" in result

    def test_compile_with_conclusion(self):
        """Test conclusion generation."""
        compiler = ReportCompiler()
        state = {
            "section_reports": {},
            "research_results": {"market_analysis": {"evidence": ["item1", "item2"]}},
            "restaurant_concept": "Test Restaurant",
            "local_area": "Test Area",
            "city": "Test City",
            "investment": "₹500,000",
        }
        result = compiler.compile(state)
        assert "## Conclusion" in result
        assert "2 evidence items" in result
        assert "*Report generated by AI*" in result

    def test_get_first_sentence(self):
        """Test first sentence extraction."""
        compiler = ReportCompiler()
        text = "This is a test. This is the second sentence."
        result = compiler._first_sentence(text)
        # The method only trims if idx > 20
        # For this text, idx=15, so it returns full text
        assert result == "This is a test. This is the second sentence."

    def test_first_sentence_no_period(self):
        """Test first sentence extraction with no period."""
        compiler = ReportCompiler()
        text = "This is a test without period"
        result = compiler._first_sentence(text)
        assert result == text

    def test_first_sentence_short(self):
        """Test first sentence extraction with short text."""
        compiler = ReportCompiler()
        text = "Short."
        result = compiler._first_sentence(text)
        # idx=5, idx > 20 is false, returns full text
        assert result == "Short."

    def test_first_sentence_long_first_sentence(self):
        """Test first sentence extraction with long first sentence."""
        compiler = ReportCompiler()
        text = "This is a very long first sentence that is longer than 20 characters. This is the second sentence."
        result = compiler._first_sentence(text)
        # idx > 20, so it should trim
        assert result == "This is a very long first sentence that is longer than 20 characters."