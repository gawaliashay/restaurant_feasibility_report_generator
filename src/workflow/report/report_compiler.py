# src\workflow\report\report_compiler.py

"""
Report Compiler.

Stacks all section reports into one final document.
No LLM used.
"""

from typing import Any
from datetime import datetime


class ReportCompiler:
    """Compile final report from all section reports."""

    def compile(self, state: dict[str, Any]) -> str:
        """Stack all reports into one document."""
        reports = state.get("section_reports", {})
        research = state.get("research_results", {})

        # Count total evidence
        total = 0
        for sec in ["market_analysis", "competitive_analysis", "location_analysis", 
                   "customer_demographics", "compliance_requirements"]:
            total += len(research.get(sec, {}).get("evidence", []))

        # Build report
        parts = [
            self._header(state),
            self._summary(state, total, reports),
            self._sections(reports),
            self._risk(reports),
            self._recommendations(reports),
            self._conclusion(state, total, reports),
        ]

        return "\n\n".join([p for p in parts if p])

    def _header(self, state: dict) -> str:
        return "\n".join([
            "# RESTAURANT FEASIBILITY REPORT",
            "",
            f"**Concept:** {state.get('restaurant_concept', '')}",
            f"**Location:** {state.get('local_area', '')}, {state.get('city', '')}",
            f"**Investment:** {state.get('investment', '')}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "", "---"
        ])

    def _summary(self, state: dict, total: int, reports: dict) -> str:
        lines = ["## Executive Summary", ""]
        lines.append(f"Report for **{state.get('restaurant_concept', '')}** in **{state.get('local_area', '')}, {state.get('city', '')}**.")
        lines.append(f"**Total Evidence:** {total} items.")
        lines.append("")

        for key, title in [("market_report", "Market"), ("competitive_report", "Competition"),
                          ("location_report", "Location"), ("demographics_report", "Demographics"),
                          ("compliance_report", "Compliance")]:
            result = reports.get(key, {})
            if result.get("status") == "success":
                report = result.get("report", "")
                first = report.split("\n")[0] if report else "No data"
                lines.append(f"- **{title}:** {first[:80]}...")

        lines.append("")
        lines.append("---")
        return "\n".join(lines)

    def _sections(self, reports: dict) -> str:
        section_map = {
            "market_report": "Market Analysis",
            "competitive_report": "Competitive Analysis",
            "location_report": "Location Analysis",
            "demographics_report": "Customer Demographics",
            "compliance_report": "Compliance Requirements",
        }

        parts = []
        for key, title in section_map.items():
            result = reports.get(key, {})
            if result.get("status") == "success":
                report = result.get("report", "")
                if report:
                    parts.append(f"## {title}\n{report}\n---")
        return "\n".join(parts)

    def _risk(self, reports: dict) -> str:
        result = reports.get("risk_assessment", {})
        if result.get("status") == "success":
            report = result.get("report", "")
            return f"## Risk Assessment\n\n{report}\n\n---" if report else ""
        return ""

    def _recommendations(self, reports: dict) -> str:
        result = reports.get("strategic_recommendations", {})
        if result.get("status") == "success":
            report = result.get("report", "")
            return f"## Strategic Recommendations\n\n{report}\n\n---" if report else ""
        return ""

    def _conclusion(self, state: dict, total: int, reports: dict) -> str:
        lines = ["## Conclusion", ""]
        lines.append(f"Assessment based on {total} evidence items for **{state.get('restaurant_concept', '')}**.")
        lines.append("")
        
        if reports.get("strategic_recommendations", {}).get("report"):
            lines.append("**Recommendation:** See Strategic Recommendations section.")
        else:
            lines.append("**Recommendation:** Review all sections carefully.")

        lines.extend(["", "---", "", "*Report generated automatically*"])
        return "\n".join(lines)