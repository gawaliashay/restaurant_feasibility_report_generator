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
        sections = [
            "market_analysis",
            "competitive_analysis",
            "location_analysis",
            "customer_demographics",
            "compliance_requirements",
        ]
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
            "---",
        ])

    def _summary(self, state: dict, total: int, reports: dict) -> str:
        """Generate executive summary."""
        lines = [
            "## Executive Summary",
            "",
            f"**{state.get('restaurant_concept', '')}** in "
            f"**{state.get('local_area', '')}, {state.get('city', '')}** — {total} evidence items.",
            "",
        ]

        section_map = {
            "market_report": "Market",
            "competitive_report": "Competition",
            "location_report": "Location",
            "demographics_report": "Demographics",
            "compliance_report": "Compliance",
        }

        for key, title in section_map.items():
            result = reports.get(key, {})
            if result.get("status") == "success":
                report_text = result.get("report", "")
                if report_text:
                    summary = self._get_first_sentence(report_text)
                    if summary:
                        lines.append(f"- **{title}:** {summary}")

        lines.extend(["", "---"])
        return "\n".join(lines)

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

    def _sections(self, reports: dict) -> str:
        section_map = {
            "market_report": "Market Analysis",
            "competitive_report": "Competitive Analysis",
            "location_report": "Location Analysis",
            "demographics_report": "Customer Demographics",
            "compliance_report": "Compliance Requirements",
        }

        parts = []
        for key in section_map:
            result = reports.get(key, {})
            if result.get("status") == "success":
                report_text = result.get("report", "")
                if report_text:
                    parts.append(f"{report_text}\n\n---")

        return "\n".join(parts)

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
            for line in risk_text.split("\n"):
                clean = line.strip()
                lower = clean.lower()
                if "high risks" in lower or "medium risks" in lower or "low risks" in lower:
                    if "high risks" in lower:
                        lines.append("**Risk Overview:**")
                    lines.append(clean)
            lines.append("")

        # Recommendations from strategic section
        rec_result = reports.get("strategic_recommendations", {})
        if rec_result.get("status") == "success":
            rec_text = rec_result.get("report", "")
            lines.append("**Key Recommendations:**")

            found = False
            for line in rec_text.split("\n"):
                raw = line.strip()
                if not raw or raw.startswith("#") or raw.startswith("*Sources"):
                    continue
                if raw.startswith("- "):
                    lines.append(f"- {raw[2:].strip()}")
                    found = True
                elif raw[0].isdigit() and ". " in raw[:5]:
                    lines.append(raw)
                    found = True

                if not found:
                    lines.append("- See Strategic Recommendations section for details.")
            else:
                lines.append("**Recommendation:** Review all sections carefully.")

        lines.extend([
            "",
            "---",
            "",
            "*Report generated by AI*",
        ])

        return "\n".join(lines)