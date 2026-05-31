"""Full Config Audit Task — End-to-end config analysis.

Input: Path to OpenCode config (global or project)
Steps: read config → analyze permissions → analyze agents → analyze skills → analyze MCPs → analyze commands → generate report
Output: Comprehensive audit report (JSON + Markdown)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from devkit.agents.config_auditor import AuditResult, run_audit
from devkit.agents.optimization_advisor import OptimizationResult, run_optimization
from devkit.agents.orchestrator import OrchestratorResult, run_orchestration
from devkit.tools.agent_analyzer import analyze_agents
from devkit.tools.command_analyzer import analyze_commands
from devkit.tools.config_reader import read_config
from devkit.tools.mcp_analyzer import analyze_mcp_servers
from devkit.tools.permission_analyzer import analyze_permissions
from devkit.tools.skill_analyzer import analyze_skills


@dataclass
class FullAuditReport:
    """Comprehensive audit report."""

    config_path: str
    timestamp: str
    orchestrator: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    optimization: dict[str, Any] = field(default_factory=dict)
    raw_analyses: dict[str, Any] = field(default_factory=dict)
    markdown_report: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "timestamp": self.timestamp,
            "orchestrator": self.orchestrator,
            "audit": self.audit,
            "optimization": self.optimization,
            "raw_analyses": self.raw_analyses,
        }

    def to_markdown(self) -> str:
        """Generate a Markdown report."""
        if self.markdown_report:
            return self.markdown_report

        lines = [
            f"# OpenCode Config Audit Report",
            f"",
            f"**Config:** `{self.config_path}`",
            f"**Date:** {self.timestamp}",
            f"",
        ]

        # Summary section
        summary = self.orchestrator.get("summary", {})
        lines.extend([
            "## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Health Score | {summary.get('health_score', 'N/A')}/100 |",
            f"| Issues | {summary.get('total_issues', 0)} |",
            f"| Warnings | {summary.get('total_warnings', 0)} |",
            f"| Agents | {summary.get('agent_count', 0)} |",
            f"| Skills | {summary.get('skill_count', 0)} |",
            f"| MCP Servers | {summary.get('mcp_count', 0)} |",
            f"| Commands | {summary.get('command_count', 0)} |",
            f"| MCP Token Estimate | ~{summary.get('mcp_token_estimate', 0)} tokens |",
            f"",
        ])

        # Audit findings
        audit_findings = self.audit.get("findings", [])
        if audit_findings:
            lines.extend([
                "## Audit Findings",
                f"",
                f"| Severity | Category | Message |",
                f"|----------|----------|---------|",
            ])
            for finding in audit_findings:
                severity = finding.get("severity", "unknown").upper()
                category = finding.get("category", "")
                message = finding.get("message", "")
                lines.append(f"| {severity} | {category} | {message} |")
            lines.append("")

        # Recommendations
        recommendations = self.optimization.get("recommendations", [])
        if recommendations:
            lines.extend([
                "## Optimization Recommendations",
                f"",
                f"**Estimated Savings:** {self.optimization.get('total_estimated_savings', 'N/A')}",
                f"",
                f"| Priority | Category | Title | Effort | Impact |",
                f"|----------|----------|-------|--------|--------|",
            ])
            for rec in recommendations:
                priority = rec.get("priority", 0)
                category = rec.get("category", "")
                title = rec.get("title", "")
                effort = rec.get("effort", "")
                impact = rec.get("estimated_impact", "")
                lines.append(f"| {priority} | {category} | {title} | {effort} | {impact} |")
            lines.append("")

        # Raw analyses
        lines.extend([
            "## Detailed Analysis",
            "",
            "### Permissions",
            f"",
            f"- Total rules: {self.raw_analyses.get('permissions', {}).get('total_rules', 0)}",
            "",
            "### Agents",
            f"",
            f"- Total agents: {self.raw_analyses.get('agents', {}).get('total_agents', 0)}",
            f"- Dependencies: {self.raw_analyses.get('agents', {}).get('total_dependencies', 0)}",
            "",
            "### Skills",
            f"",
            f"- Total skills: {self.raw_analyses.get('skills', {}).get('total_skills', 0)}",
            f"- Valid skills: {self.raw_analyses.get('skills', {}).get('valid_skills', 0)}",
            "",
            "### MCP Servers",
            f"",
            f"- Enabled: {self.raw_analyses.get('mcp_servers', {}).get('enabled_count', 0)}",
            f"- Disabled: {self.raw_analyses.get('mcp_servers', {}).get('disabled_count', 0)}",
            f"- OAuth configured: {self.raw_analyses.get('mcp_servers', {}).get('oauth_count', 0)}",
            f"- Total token estimate: ~{self.raw_analyses.get('mcp_servers', {}).get('total_estimated_tokens', 0)}",
            "",
            "### Commands",
            f"",
            f"- Total commands: {self.raw_analyses.get('commands', {}).get('total_commands', 0)}",
            "",
        ])

        self.markdown_report = "\n".join(lines)
        return self.markdown_report


def create_full_audit_task(
    config_path: str,
    project_root: Optional[Path] = None,
) -> FullAuditReport:
    """Run the full audit pipeline.

    Args:
        config_path: Path to the OpenCode config file.
        project_root: Project root for local skill/command discovery.

    Returns:
        FullAuditReport with all analysis sections.
    """
    timestamp = datetime.now().isoformat()
    report = FullAuditReport(
        config_path=config_path,
        timestamp=timestamp,
    )

    # Step 1: Run orchestrator (unified analysis)
    orchestrator_result = run_orchestration(config_path, project_root)
    report.orchestrator = orchestrator_result.to_dict()

    # Step 2: Run config audit (security + best practices)
    audit_result = run_audit(config_path, project_root)
    report.audit = audit_result.to_dict()

    # Step 3: Run optimization advisor (recommendations)
    optimization_result = run_optimization(config_path)
    report.optimization = optimization_result.to_dict()

    # Step 4: Collect raw analyses for detailed report
    config_result = read_config(config_path)
    if config_result.success:
        config = config_result.config
        report.raw_analyses["permissions"] = analyze_permissions(config).to_dict()
        report.raw_analyses["agents"] = analyze_agents(config).to_dict()
        report.raw_analyses["skills"] = analyze_skills(project_root, config).to_dict()
        report.raw_analyses["mcp_servers"] = analyze_mcp_servers(config).to_dict()
        report.raw_analyses["commands"] = analyze_commands(project_root, config).to_dict()

    # Generate markdown report
    report.to_markdown()

    return report


def save_report(report: FullAuditReport, output_dir: Optional[Path] = None) -> tuple[Path, Path]:
    """Save the audit report to JSON and Markdown files.

    Args:
        report: The full audit report.
        output_dir: Directory to save reports (default: ./output/).

    Returns:
        Tuple of (json_path, markdown_path).
    """
    if output_dir is None:
        output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = report.timestamp.replace(":", "-").replace(".", "-")
    json_path = output_dir / f"audit-{timestamp}.json"
    md_path = output_dir / f"audit-{timestamp}.md"

    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    md_path.write_text(
        report.to_markdown(),
        encoding="utf-8",
    )

    return json_path, md_path
