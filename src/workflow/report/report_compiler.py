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
        sections = ["market_analysis", "competitive_analysis", "location_analysis", 
                   "customer_demographics", "compliance_requirements"]
        for section in sections:
            total += len(research.get(section, {}).get("evidence", []))

        # Build report
        parts = [
            self._header(state),
            self._summary(state, total, reports),
            self._sections(reports),
            self._risk(reports),
            self._recommendations(reports),
            self._conclusion(state, total, reports),
        ]

        return "\n\n".join([part for part in parts if part])

    def _header(self, state: dict) -> str:
        """Generate report header."""
        return "\n".join([
            "# RESTAURANT FEASIBILITY REPORT",
            "",
            f"**Concept:** {state.get('restaurant_concept', '')}",
            f"**Location:** {state.get('local_area', '')}, {state.get('city', '')}",
            f"**Investment:** {state.get('investment', '')}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---"
        ])

    def _summary(self, state: dict, total: int, reports: dict) -> str:
        """Generate executive summary."""
        lines = []
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"Report for **{state.get('restaurant_concept', '')}** in **{state.get('local_area', '')}, {state.get('city', '')}**.")
        lines.append(f"**Total Evidence:** {total} items.")
        lines.append("")
        
        # Map report keys to display names
        section_map = {
            "market_report": "Market",
            "competitive_report": "Competition",
            "location_report": "Location",
            "demographics_report": "Demographics",
            "compliance_report": "Compliance"
        }
        
        for key, title in section_map.items():
            result = reports.get(key, {})
            if result.get("status") == "success":
                report_text = result.get("report", "")
                if report_text:
                    summary = self._get_first_sentence(report_text)
                    if summary:
                        lines.append(f"- **{title}:** {summary}")
        
        lines.append("")
        lines.append("---")
        return "\n".join(lines)

    def _get_first_sentence(self, text: str, max_length: int = 120) -> str:
        """Extract first meaningful sentence from text."""
        for line in text.split("\n"):
            clean = line.strip()
            
            # Skip empty lines
            if not clean:
                continue
            
            # Skip headings, tables, bullet lists, sources, and question headers
            if clean.startswith(("#", "|", "-")):
                continue
            if clean.lower().startswith("sources:"):
                continue
            if clean.endswith("?") and len(clean) < 50:
                continue
            
            # Found real content
            if len(clean) > 10:
                return clean[:max_length] + "..." if len(clean) > max_length else clean
        
        return ""

    def _sections(self, reports: dict) -> str:
        """Generate main report sections."""
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
                report_text = result.get("report", "")
                if report_text:
                    parts.append(f"## {title}\n{report_text}\n---")
        
        return "\n".join(parts)

    def _risk(self, reports: dict) -> str:
        """Generate risk assessment section."""
        result = reports.get("risk_assessment", {})
        if result.get("status") == "success":
            report_text = result.get("report", "")
            if report_text:
                return f"## Risk Assessment\n\n{report_text}\n\n---"
        return ""

    def _recommendations(self, reports: dict) -> str:
        """Generate recommendations section."""
        result = reports.get("strategic_recommendations", {})
        if result.get("status") == "success":
            report_text = result.get("report", "")
            if report_text:
                return f"## Strategic Recommendations\n\n{report_text}\n\n---"
        return ""

    def _conclusion(self, state: dict, total: int, reports: dict) -> str:
        """Generate conclusion."""
        lines = []
        lines.append("## Conclusion")
        lines.append("")
        lines.append(f"Assessment based on {total} evidence items for **{state.get('restaurant_concept', '')}**.")
        lines.append("")
        
        # Extract recommendations
        rec_result = reports.get("strategic_recommendations", {})
        if rec_result.get("status") == "success":
            rec_text = rec_result.get("report", "")
            lines.append("**Key Recommendations:**")
            
            count = 0
            keywords = ["price", "position", "target", "menu", "marketing"]
            
            for line in rec_text.split("\n"):
                if count >= 3:
                    break
                
                clean = line.strip()
                if not clean or len(clean) <= 10 or clean.startswith("#"):
                    continue
                
                if any(word in clean.lower() for word in keywords):
                    lines.append(f"- {clean[:100]}...")
                    count += 1
            
            if count == 0:
                lines.append("- See Strategic Recommendations section for details.")
        else:
            lines.append("**Recommendation:** Review all sections carefully.")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Report generated automatically*")
        
        return "\n".join(lines)