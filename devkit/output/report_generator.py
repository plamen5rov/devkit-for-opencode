"""Report generator for DevKit analysis outputs.

Generates formatted reports in JSON, Markdown, and HTML formats.
Saves to output/ directory with timestamped filenames.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


class ReportGenerator:
    """Generate formatted analysis reports."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        data: dict[str, Any],
        fmt: str = "json",
        prefix: str = "devkit",
    ) -> Path:
        """Generate and save a report.

        Args:
            data: Report data dictionary.
            fmt: Output format (json, markdown, html).
            prefix: Filename prefix.

        Returns:
            Path to the saved report file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.{self._extension(fmt)}"
        filepath = self.output_dir / filename

        content = self._render(data, fmt)
        filepath.write_text(content, encoding="utf-8")

        return filepath

    def generate_json(self, data: dict[str, Any], prefix: str = "devkit") -> Path:
        """Generate JSON report."""
        return self.generate(data, "json", prefix)

    def generate_markdown(self, data: dict[str, Any], prefix: str = "devkit") -> Path:
        """Generate Markdown report."""
        return self.generate(data, "markdown", prefix)

    def generate_html(self, data: dict[str, Any], prefix: str = "devkit") -> Path:
        """Generate HTML report."""
        return self.generate(data, "html", prefix)

    def _extension(self, fmt: str) -> str:
        return {"json": "json", "markdown": "md", "html": "html"}.get(fmt, "txt")

    def _render(self, data: dict[str, Any], fmt: str) -> str:
        if fmt == "json":
            return json.dumps(data, indent=2, default=str)
        if fmt == "markdown":
            return self._render_markdown(data)
        if fmt == "html":
            return self._render_html(data)
        return str(data)

    def _render_markdown(self, data: dict[str, Any]) -> str:
        lines = ["# DevKit Analysis Report\n"]

        # Summary
        summary = data.get("summary", {})
        if summary:
            lines.append("## Summary\n")
            if "health_score" in summary:
                lines.append(f"**Health Score:** {summary['health_score']}/100\n")
            if "risk_score" in summary:
                lines.append(f"**Risk Score:** {summary['risk_score']}/100\n")
            lines.append("")

        # Findings
        findings = data.get("findings", [])
        if findings:
            lines.append("## Findings\n")
            lines.append("| Severity | Category | Message |")
            lines.append("|----------|----------|---------|")
            for f in findings:
                severity = f.get("severity", "info")
                category = f.get("category", "general")
                message = f.get("message", "")
                lines.append(f"| {severity} | {category} | {message} |")
            lines.append("")

        # Recommendations
        recommendations = data.get("recommendations", [])
        if recommendations:
            lines.append("## Recommendations\n")
            for i, rec in enumerate(recommendations, 1):
                title = rec.get("title", f"Recommendation {i}")
                description = rec.get("description", "")
                category = rec.get("category", "")
                lines.append(f"### {i}. {title}\n")
                if category:
                    lines.append(f"**Category:** {category}\n")
                lines.append(f"{description}\n")
            lines.append("")

        # Score trends
        trends = data.get("trends", [])
        if trends:
            lines.append("## Score Trends\n")
            lines.append("| Date | Health Score | Risk Score |")
            lines.append("|------|-------------|------------|")
            for t in trends:
                date = t.get("timestamp", "")[:10]
                health = t.get("health_score", "")
                risk = t.get("risk_score", "")
                lines.append(f"| {date} | {health} | {risk} |")
            lines.append("")

        # Raw data (if present)
        if "raw" in data:
            lines.append("## Raw Data\n")
            lines.append("```json")
            lines.append(json.dumps(data["raw"], indent=2, default=str))
            lines.append("```\n")

        return "\n".join(lines)

    def _render_html(self, data: dict[str, Any]) -> str:
        summary = data.get("summary", {})
        findings = data.get("findings", [])
        recommendations = data.get("recommendations", [])

        health_score = summary.get("health_score", 0)
        risk_score = summary.get("risk_score", 0)

        findings_rows = ""
        for f in findings:
            severity = f.get("severity", "info")
            category = f.get("category", "general")
            message = f.get("message", "")
            findings_rows += f"<tr><td>{severity}</td><td>{category}</td><td>{message}</td></tr>\n"

        rec_rows = ""
        for i, rec in enumerate(recommendations, 1):
            title = rec.get("title", f"Recommendation {i}")
            description = rec.get("description", "")
            category = rec.get("category", "")
            rec_rows += f"<tr><td>{i}</td><td>{category}</td><td>{title}</td><td>{description}</td></tr>\n"

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>DevKit Analysis Report</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
        h1 {{ color: #1a1a1a; }}
        .score {{ display: inline-block; padding: 0.5rem 1rem; border-radius: 4px; margin: 0.5rem; }}
        .health {{ background: #e8f5e9; color: #2e7d32; }}
        .risk {{ background: #ffebee; color: #c62828; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .severity-error {{ color: #c62828; font-weight: bold; }}
        .severity-warning {{ color: #f57f17; }}
        .severity-info {{ color: #1565c0; }}
    </style>
</head>
<body>
    <h1>DevKit Analysis Report</h1>
    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <h2>Summary</h2>
    <div>
        <span class="score health">Health Score: {health_score}/100</span>
        <span class="score risk">Risk Score: {risk_score}/100</span>
    </div>

    <h2>Findings ({len(findings)})</h2>
    <table>
        <tr><th>Severity</th><th>Category</th><th>Message</th></tr>
        {findings_rows}
    </table>

    <h2>Recommendations ({len(recommendations)})</h2>
    <table>
        <tr><th>#</th><th>Category</th><th>Title</th><th>Description</th></tr>
        {rec_rows}
    </table>
</body>
</html>"""
