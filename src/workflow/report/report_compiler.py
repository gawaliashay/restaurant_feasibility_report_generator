# src\workflow\report\report_compiler.py

"""
Report Compiler.

Stacks all section reports into one final document.
No LLM used.
"""

from typing import Any
from datetime import datetime
from src.configuration.config_loader import config_loader


class ReportCompiler:
    """Compile final report from all section reports."""

    def compile(self, state: dict[str, Any]) -> str:
        """Stack all reports into one document."""
        reports = state.get("section_reports", {})
        research = state.get("research_results", {})

        # Load from config instead of hardcoding
        research_sections = config_loader.get("research.sections", {})
        total = 0
        for section_name, section_config in research_sections.items():
            if section_config.get("enabled", True):
                total += len(research.get(section_name, {}).get("evidence", []))

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
            "---",
        ])

    # src/workflow/report/report_compiler.py

    def _summary(self, state: dict, total: int, reports: dict) -> str:
        """Generate executive summary."""
        lines = [
            "## Executive Summary",
            "",
            f"**{state.get('restaurant_concept', '')}** in "
            f"**{state.get('local_area', '')}, {state.get('city', '')}** — {total} evidence items.",
            "",
        ]

        # Load from config instead of hardcoding
        sections = config_loader.get("report.sections", {})
        
        for section_name, section_config in sections.items():
            if section_name == "final_compilation":
                continue
            result = reports.get(section_name, {})
            if result.get("status") == "success":
                report_text = result.get("report", "")
                if report_text:
                    summary = self._get_first_sentence(report_text)
                    if summary:
                        title = section_config.get("title", section_name).replace(" Report", "")
                        lines.append(f"- **{title}:** {summary}")

        lines.extend(["", "---"])
        return "\n".join(lines)


    def _sections(self, reports: dict) -> str:
        """Generate all section reports."""
        sections = config_loader.get("report.sections", {})
        parts = []
        
        for section_name, section_config in sections.items():
            # Skip disabled sections
            if not section_config.get("enabled", True):
                continue
            # Skip cross-section sections (they are added separately)
            if section_config.get("research_section") is None:
                continue
                
            result = reports.get(section_name, {})
            if result.get("status") == "success":
                report_text = result.get("report", "")
                if report_text:
                    parts.append(f"{report_text}\n\n---")
        
        return "\n".join(parts)

    def _get_first_sentence(self, text: str) -> str:
        """Extract first meaningful line from section text."""
        skip_starts = (
            "the google trends data",
            "the analysis of google trends",
            "most common service",
        )

        candidates = []
        for line in text.split("\n"):
            clean = line.strip()
            if not clean:
                continue
            if clean.startswith("- "):
                clean = clean[2:].strip()
            if clean.startswith(("#", "|")):
                continue
            if clean.startswith("**") and clean.endswith(":"):
                continue
            if clean.lower().startswith("sources:"):
                continue
            if any(clean.lower().startswith(s) for s in skip_starts):
                continue
            if len(clean) <= 10:
                continue
            candidates.append(clean)

        for clean in candidates:
            lower = clean.lower()
            if (
                lower.startswith("overall")
                or "notable competitors" in lower
                or "this trend indicates" in lower
            ):
                return self._first_sentence(clean)

        if candidates:
            return self._first_sentence(candidates[0])

        return ""

    def _first_sentence(self, text: str) -> str:
        """Trim text to its first sentence only."""
        idx = text.find(". ")
        if idx != -1 and idx > 20:
            return text[:idx + 1]
        return text

    def _risk(self, reports: dict) -> str:
        result = reports.get("risk_assessment", {})
        if result.get("status") == "success":
            report_text = result.get("report", "")
            if report_text:
                return f"{report_text}\n\n---"
        return ""

    def _recommendations(self, reports: dict) -> str:
        result = reports.get("strategic_recommendations", {})
        if result.get("status") == "success":
            report_text = result.get("report", "")
            if report_text:
                return f"{report_text}\n\n---"
        return ""

    def _conclusion(self, state: dict, total: int, reports: dict) -> str:
        """Generate conclusion."""
        lines = [
            "## Conclusion",
            "",
            f"Assessment based on {total} evidence items for "
            f"**{state.get('restaurant_concept', '')}** "
            f"in **{state.get('local_area', '')}, {state.get('city', '')}** "
            f"with an investment of **{state.get('investment', '')}**.",
            "",
        ]

        # Risk summary from risk section
        risk_result = reports.get("risk_assessment", {})
        if risk_result.get("status") == "success":
            risk_text = risk_result.get("report", "")
            has_risks = False
            
            # Look for "Overall Risk Summary" or "Overall"
            for line in risk_text.split("\n"):
                clean = line.strip()
                lower = clean.lower()
                
                # Look for risk summary section
                if "overall risk summary" in lower or "## overall" in lower:
                    lines.append("**Risk Overview:**")
                    has_risks = True
                    continue
                
                # Look for risk lines
                if has_risks and ("- high risks" in lower or "- medium risks" in lower or "- low risks" in lower):
                    lines.append(clean)
                    
                # Stop when we reach the next section
                if has_risks and clean.startswith("##") and "risk" not in lower:
                    break
            
            if has_risks:
                lines.append("")

        # Point to recommendations section
        rec_result = reports.get("strategic_recommendations", {})
        if rec_result.get("status") == "success":
            lines.append("**Key Recommendations:**")
            lines.append("See the Strategic Recommendations section for a complete action plan.")
            lines.append("")

        lines.extend([
            "---",
            "",
            "*Report generated by AI*",
        ])

        return "\n".join(lines)