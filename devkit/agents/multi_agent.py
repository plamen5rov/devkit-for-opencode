"""Multi-Agent Orchestration — Aggregates results from all analyzers.

Runs orchestrator, auditor, and advisor, then aggregates findings
into a unified report with health and risk scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from devkit.agents.config_auditor import AuditResult, run_audit
from devkit.agents.optimization_advisor import OptimizationResult, run_optimization
from devkit.agents.orchestrator import OrchestratorResult, run_orchestration


@dataclass
class MultiAgentReport:
    """Unified report from multi-agent orchestration."""

    config_path: str
    orchestrator_result: Optional[OrchestratorResult] = None
    audit_result: Optional[AuditResult] = None
    optimization_result: Optional[OptimizationResult] = None
    aggregated_findings: list[dict[str, Any]] = field(default_factory=list)
    aggregated_recommendations: list[dict[str, Any]] = field(default_factory=list)
    health_score: int = 0
    risk_score: int = 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "health_score": self.health_score,
            "risk_score": self.risk_score,
            "orchestrator": self.orchestrator_result.to_dict() if self.orchestrator_result else None,
            "audit": self.audit_result.to_dict() if self.audit_result else None,
            "optimization": self.optimization_result.to_dict() if self.optimization_result else None,
            "aggregated_findings": self.aggregated_findings,
            "aggregated_recommendations": self.aggregated_recommendations,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Multi-Agent Analysis Report\n",
            f"**Config:** {self.config_path}\n",
            f"**Health Score:** {self.health_score}/100\n",
            f"**Risk Score:** {self.risk_score}/100\n",
        ]

        if self.aggregated_findings:
            lines.append("\n## Findings\n")
            lines.append("| Severity | Category | Message |")
            lines.append("|----------|----------|---------|")
            for f in self.aggregated_findings:
                lines.append(
                    f"| {f.get('severity', 'info')} | {f.get('category', '')} | {f.get('message', '')} |"
                )

        if self.aggregated_recommendations:
            lines.append("\n## Recommendations\n")
            for i, rec in enumerate(self.aggregated_recommendations, 1):
                lines.append(f"{i}. **{rec.get('title', '')}** — {rec.get('description', '')}")

        return "\n".join(lines)


def run_multi_agent_analysis(
    config_path: str,
    project_root: Optional[Path] = None,
    model: str = "anthropic/claude-sonnet-4-20250514",
    verbose: bool = False,
    process: str = "sequential",
) -> MultiAgentReport:
    """Run multi-agent analysis with delegation.

    Args:
        config_path: Path to the OpenCode config file.
        project_root: Project root for local discovery.
        model: LLM model to use (kept for API compatibility).
        verbose: Enable verbose output.
        process: Process type (kept for API compatibility).

    Returns:
        MultiAgentReport with aggregated results.
    """
    report = MultiAgentReport(config_path=config_path)

    # Run all three analyses
    report.orchestrator_result = run_orchestration(
        config_path, project_root=project_root, model=model, verbose=verbose
    )
    report.audit_result = run_audit(config_path, project_root=project_root)
    report.optimization_result = run_optimization(
        config_path, project_root=project_root
    )

    # Aggregate findings
    report.aggregated_findings = _aggregate_findings(report)
    report.aggregated_recommendations = _aggregate_recommendations(report)

    # Calculate scores
    report.health_score = _calculate_multi_agent_health(report)
    report.risk_score = _calculate_multi_agent_risk(report)

    return report


def _aggregate_findings(report: MultiAgentReport) -> list[dict[str, Any]]:
    """Aggregate findings from all agents."""
    findings = []

    # From orchestrator
    if report.orchestrator_result:
        for issue in report.orchestrator_result.issues:
            findings.append({
                "severity": "error",
                "category": "orchestrator",
                "message": issue,
            })
        for warning in report.orchestrator_result.warnings:
            findings.append({
                "severity": "warning",
                "category": "orchestrator",
                "message": warning,
            })

    # From auditor
    if report.audit_result:
        for finding in report.audit_result.findings:
            findings.append({
                "severity": finding.severity.value,
                "category": finding.category,
                "message": finding.message,
                "suggestion": finding.suggestion,
            })

    # Deduplicate by message
    seen = set()
    unique = []
    for f in findings:
        if f["message"] not in seen:
            seen.add(f["message"])
            unique.append(f)

    return unique


def _aggregate_recommendations(report: MultiAgentReport) -> list[dict[str, Any]]:
    """Aggregate recommendations from all agents."""
    recommendations = []

    if report.optimization_result:
        for rec in report.optimization_result.recommendations:
            recommendations.append({
                "priority": rec.priority,
                "category": rec.category,
                "title": rec.title,
                "description": rec.description,
                "before": rec.current_state,
                "after": rec.suggested_state,
            })

    # Sort by priority
    recommendations.sort(key=lambda r: r.get("priority", 99))

    return recommendations


def _calculate_multi_agent_health(report: MultiAgentReport) -> int:
    """Calculate health score from multi-agent analysis."""
    score = 100

    # From orchestrator
    if report.orchestrator_result:
        score = report.orchestrator_result.summary.get("health_score", 100)

    # Deduct for audit errors
    if report.audit_result:
        score -= report.audit_result.error_count * 10
        score -= report.audit_result.warning_count * 5

    return max(0, min(100, score))


def _calculate_multi_agent_risk(report: MultiAgentReport) -> int:
    """Calculate risk score from multi-agent analysis."""
    score = 100

    # From audit findings
    if report.audit_result:
        for finding in report.audit_result.findings:
            if finding.severity.value == "error":
                score -= 15
            elif finding.severity.value == "warning":
                score -= 8
            elif finding.severity.value == "info":
                score -= 2

    return max(0, min(100, score))
