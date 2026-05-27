"""Config Audit Agent — Specialized config validation agent.

Role: Validate OpenCode configs for errors, anti-patterns, security issues.
Tools: config reader, permission analyzer, agent analyzer.
Output: Audit report with severity levels (error, warning, info).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from crewai import Agent, Task

from devkit.tools.agent_analyzer import analyze_agents
from devkit.tools.config_reader import read_config
from devkit.tools.permission_analyzer import analyze_permissions


class Severity(str, Enum):
    """Finding severity level."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class AuditFinding:
    """A single audit finding."""

    severity: Severity
    category: str
    message: str
    path: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "path": self.path,
            "suggestion": self.suggestion,
        }


@dataclass
class AuditResult:
    """Result of a config audit."""

    config_path: str
    findings: list[AuditFinding] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "findings": [f.to_dict() for f in self.findings],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "total_findings": len(self.findings),
        }


def create_config_auditor_agent(
    model: str = "anthropic/claude-sonnet-4-20250514",
    verbose: bool = False,
) -> Agent:
    """Create the config auditor CrewAI agent."""
    return Agent(
        role="OpenCode Configuration Auditor",
        goal="Validate OpenCode configurations for errors, anti-patterns, and security issues",
        backstory=(
            "You are a security-focused analyst specializing in OpenCode "
            "configuration validation. You identify misconfigurations, "
            "security risks, and anti-patterns in OpenCode configs."
        ),
        verbose=verbose,
        allow_delegation=False,
    )


def create_audit_task(
    agent: Agent,
    config_path: str,
) -> Task:
    """Create the audit task."""
    return Task(
        description=(
            f"Audit the OpenCode configuration at {config_path}. "
            "Check for errors, security issues, and anti-patterns."
        ),
        expected_output="JSON audit report with findings by severity",
        agent=agent,
    )


def run_audit(
    config_path: str,
    project_root: Optional[Path] = None,
) -> AuditResult:
    """Run a full config audit.

    Args:
        config_path: Path to the OpenCode config file.
        project_root: Project root for local discovery.

    Returns:
        AuditResult with findings categorized by severity.
    """
    result = AuditResult(config_path=config_path)

    # Step 1: Read config
    config_result = read_config(config_path)
    if not config_result.success:
        for error in config_result.errors:
            result.findings.append(
                AuditFinding(
                    severity=Severity.ERROR,
                    category="config-parse",
                    message=error,
                    path=config_path,
                )
            )
        result.error_count = len(result.findings)
        return result

    config = config_result.config

    # Step 2: Run analyzers and collect findings
    _audit_permissions(config, result)
    _audit_agents(config, result)
    _audit_security(config, result)
    _audit_best_practices(config, result)

    # Count by severity
    result.error_count = sum(
        1 for f in result.findings if f.severity == Severity.ERROR
    )
    result.warning_count = sum(
        1 for f in result.findings if f.severity == Severity.WARNING
    )
    result.info_count = sum(
        1 for f in result.findings if f.severity == Severity.INFO
    )

    return result


def _audit_permissions(config: dict[str, Any], result: AuditResult) -> None:
    """Audit permission configuration."""
    perm_result = analyze_permissions(config)

    # Issues are errors
    for issue in perm_result.issues:
        result.findings.append(
            AuditFinding(
                severity=Severity.ERROR,
                category="permission",
                message=issue,
                suggestion="Review and fix permission rules",
            )
        )

    # Warnings are warnings
    for warning in perm_result.warnings:
        result.findings.append(
            AuditFinding(
                severity=Severity.WARNING,
                category="permission",
                message=warning,
                suggestion="Review permission configuration",
            )
        )

    # Check for missing catch-all
    global_perms = config.get("permission", {})
    if isinstance(global_perms, dict) and "*" not in global_perms:
        result.findings.append(
            AuditFinding(
                severity=Severity.INFO,
                category="permission",
                message="No catch-all permission rule ('*') configured",
                suggestion="Add '*': 'ask' as a default catch-all rule",
            )
        )


def _audit_agents(config: dict[str, Any], result: AuditResult) -> None:
    """Audit agent configuration."""
    agent_result = analyze_agents(config)

    # Issues are errors
    for issue in agent_result.issues:
        result.findings.append(
            AuditFinding(
                severity=Severity.ERROR,
                category="agent",
                message=issue,
                suggestion="Review agent configuration",
            )
        )

    # Warnings are warnings
    for warning in agent_result.warnings:
        result.findings.append(
            AuditFinding(
                severity=Severity.WARNING,
                category="agent",
                message=warning,
                suggestion="Review agent configuration",
            )
        )


def _audit_security(config: dict[str, Any], result: AuditResult) -> None:
    """Audit security-related configuration."""
    # Check for secrets in config
    _check_secrets(config, "", result)

    # Check for overly permissive bash
    bash_config = config.get("permission", {}).get("bash", {})
    if isinstance(bash_config, str) and bash_config == "allow":
        result.findings.append(
            AuditFinding(
                severity=Severity.WARNING,
                category="security",
                message="Bash is globally allowed without restrictions",
                suggestion="Use granular bash permissions to restrict dangerous commands",
            )
        )

    # Check for disabled doom_loop
    if "doom_loop" not in config.get("permission", {}):
        result.findings.append(
            AuditFinding(
                severity=Severity.INFO,
                category="security",
                message="No explicit doom_loop protection configured",
                suggestion="Consider adding 'doom_loop': 'ask' for explicit control",
            )
        )

    # Check for external_directory without restrictions
    if "external_directory" not in config.get("permission", {}):
        result.findings.append(
            AuditFinding(
                severity=Severity.INFO,
                category="security",
                message="No external_directory rules configured",
                suggestion="Consider restricting external directory access",
            )
        )


def _check_secrets(
    obj: Any,
    path: str,
    result: AuditResult,
) -> None:
    """Recursively check for potential secrets in config."""
    secret_patterns = ["api_key", "secret", "token", "password", "credential"]

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if any(p in key.lower() for p in secret_patterns):
                if isinstance(value, str) and value and not value.startswith(
                    ("{env:", "${", "$")
                ):
                    result.findings.append(
                        AuditFinding(
                            severity=Severity.ERROR,
                            category="security",
                            message=f"Possible hardcoded secret at '{current_path}'",
                            suggestion="Use environment variable reference: {{env:VAR_NAME}}",
                        )
                    )
            _check_secrets(value, current_path, result)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_secrets(item, f"{path}[{i}]", result)


def _audit_best_practices(config: dict[str, Any], result: AuditResult) -> None:
    """Audit configuration best practices."""
    # Check for missing model
    if "model" not in config:
        result.findings.append(
            AuditFinding(
                severity=Severity.WARNING,
                category="best-practice",
                message="No primary model configured",
                suggestion="Set 'model' to your preferred LLM (e.g., 'anthropic/claude-sonnet-4-20250514')",
            )
        )

    # Check for missing small_model
    if "small_model" not in config:
        result.findings.append(
            AuditFinding(
                severity=Severity.INFO,
                category="best-practice",
                message="No small_model configured",
                suggestion="Configure 'small_model' for cost-efficient title/summary generation",
            )
        )

    # Check for schema reference
    if "$schema" not in config:
        result.findings.append(
            AuditFinding(
                severity=Severity.INFO,
                category="best-practice",
                message="No $schema reference in config",
                suggestion="Add '$schema': 'https://opencode.ai/config.json' for IDE support",
            )
        )

    # Check for share configuration
    if "share" not in config:
        result.findings.append(
            AuditFinding(
                severity=Severity.INFO,
                category="best-practice",
                message="No share configuration",
                suggestion="Set 'share' to 'manual', 'auto', or 'disabled'",
            )
        )
