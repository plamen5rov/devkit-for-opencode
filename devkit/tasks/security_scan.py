"""Security Scan Task — Security-focused config analysis.

Checks for: secrets in config, overly permissive bash rules, exposed external
directories, disabled doom_loop protection, and other security anti-patterns.
Output: Security findings with severity and remediation steps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from devkit.tools.config_reader import read_config
from devkit.tools.permission_analyzer import analyze_permissions


class SecuritySeverity(str, Enum):
    """Security finding severity."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityFinding:
    """A single security finding."""

    severity: SecuritySeverity
    category: str
    title: str
    description: str
    location: str = ""
    remediation: str = ""
    cve_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "remediation": self.remediation,
            "cve_reference": self.cve_reference,
        }


@dataclass
class SecurityScanResult:
    """Result of a security scan."""

    config_path: str
    findings: list[SecurityFinding] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    risk_score: int = 100  # 0 = highest risk, 100 = no risk

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "findings": [f.to_dict() for f in self.findings],
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "risk_score": self.risk_score,
            "total_findings": len(self.findings),
        }

    def to_markdown(self) -> str:
        """Generate a Markdown security report."""
        lines = [
            "# Security Scan Report",
            f"",
            f"**Config:** `{self.config_path}`",
            f"**Risk Score:** {self.risk_score}/100",
            f"",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| Critical | {self.critical_count} |",
            f"| High | {self.high_count} |",
            f"| Medium | {self.medium_count} |",
            f"| Low | {self.low_count} |",
            f"| Info | {self.info_count} |",
            f"",
        ]

        if self.findings:
            lines.extend([
                "## Findings",
                f"",
                f"| Severity | Category | Title | Remediation |",
                f"|----------|----------|-------|-------------|",
            ])
            for finding in self.findings:
                lines.append(
                    f"| {finding.severity.value.upper()} "
                    f"| {finding.category} "
                    f"| {finding.title} "
                    f"| {finding.remediation} |"
                )
            lines.append("")

        return "\n".join(lines)


def run_security_scan(
    config_path: str,
) -> SecurityScanResult:
    """Run a comprehensive security scan.

    Args:
        config_path: Path to the OpenCode config file.

    Returns:
        SecurityScanResult with findings and risk score.
    """
    result = SecurityScanResult(config_path=config_path)

    # Read config
    config_result = read_config(config_path)
    if not config_result.success:
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.HIGH,
                category="config",
                title="Cannot read config file",
                description=f"Failed to read config: {', '.join(config_result.errors)}",
                location=config_path,
                remediation="Ensure config file exists and is valid JSON/JSONC",
            )
        )
        result.risk_score = 0
        return result

    config = config_result.config

    # Run security checks
    _check_secrets(config, result)
    _check_bash_permissions(config, result)
    _check_edit_permissions(config, result)
    _check_external_directories(config, result)
    _check_doom_loop(config, result)
    _check_mcp_security(config, result)
    _check_agent_permissions(config, result)
    _check_plugin_security(config, result)
    _check_share_security(config, result)

    # Count by severity
    result.critical_count = sum(
        1 for f in result.findings if f.severity == SecuritySeverity.CRITICAL
    )
    result.high_count = sum(
        1 for f in result.findings if f.severity == SecuritySeverity.HIGH
    )
    result.medium_count = sum(
        1 for f in result.findings if f.severity == SecuritySeverity.MEDIUM
    )
    result.low_count = sum(
        1 for f in result.findings if f.severity == SecuritySeverity.LOW
    )
    result.info_count = sum(
        1 for f in result.findings if f.severity == SecuritySeverity.INFO
    )

    # Calculate risk score
    result.risk_score = _calculate_risk_score(result)

    return result


def _check_secrets(config: dict[str, Any], result: SecurityScanResult) -> None:
    """Check for hardcoded secrets in config."""
    secret_patterns = [
        "api_key", "apikey", "api-key",
        "secret", "secret_key",
        "token", "access_token", "auth_token",
        "password", "passwd",
        "credential", "credentials",
        "private_key",
    ]

    _scan_for_secrets(config, "", secret_patterns, result)


def _scan_for_secrets(
    obj: Any,
    path: str,
    patterns: list[str],
    result: SecurityScanResult,
) -> None:
    """Recursively scan for secrets."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if any(p in key.lower() for p in patterns):
                if isinstance(value, str) and value:
                    # Check if it's an env reference
                    if not re.match(r"^\{env:[^}]+\}$|^\$\{[^}]+\}$|^\$[A-Z_]+$", value):
                        # Check if it looks like a real secret (not a placeholder)
                        if not value.startswith(("sk-test-", "pk-test-", "your_", "example")):
                            result.findings.append(
                                SecurityFinding(
                                    severity=SecuritySeverity.CRITICAL,
                                    category="secrets",
                                    title=f"Hardcoded secret at '{current_path}'",
                                    description=(
                                        f"Possible hardcoded secret found in config. "
                                        f"Value appears to be a real credential."
                                    ),
                                    location=current_path,
                                    remediation=(
                                        "Use environment variable reference: "
                                        "{env:VAR_NAME} or ${VAR_NAME}"
                                    ),
                                )
                            )
            _scan_for_secrets(value, current_path, patterns, result)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _scan_for_secrets(item, f"{path}[{i}]", patterns, result)


def _check_bash_permissions(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check for overly permissive bash rules."""
    perm_result = analyze_permissions(config)
    bash_config = config.get("permission", {}).get("bash", {})

    if isinstance(bash_config, str) and bash_config == "allow":
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.HIGH,
                category="bash",
                title="Bash globally allowed",
                description=(
                    "All bash commands are allowed without restrictions. "
                    "This allows execution of any command including destructive ones."
                ),
                location="permission.bash",
                remediation=(
                    'Use granular permissions: {"*": "ask", "git *": "allow"}'
                ),
            )
        )

    # Check for dangerous commands allowed
    dangerous_commands = {
        "rm -rf *": SecuritySeverity.CRITICAL,
        "rm -rf /*": SecuritySeverity.CRITICAL,
        "sudo *": SecuritySeverity.HIGH,
        "curl * | sh": SecuritySeverity.HIGH,
        "curl * | bash": SecuritySeverity.HIGH,
        "wget * | sh": SecuritySeverity.HIGH,
        "chmod 777 *": SecuritySeverity.MEDIUM,
        "pkill *": SecuritySeverity.MEDIUM,
        "kill *": SecuritySeverity.MEDIUM,
    }

    if isinstance(bash_config, dict):
        for pattern, action in bash_config.items():
            if action == "allow":
                for dangerous, severity in dangerous_commands.items():
                    if dangerous.replace(" *", "") in pattern:
                        result.findings.append(
                            SecurityFinding(
                                severity=severity,
                                category="bash",
                                title=f"Dangerous command pattern allowed: '{pattern}'",
                                description=(
                                    f"The pattern '{pattern}' matches potentially "
                                    f"dangerous commands."
                                ),
                                location=f"permission.bash.{pattern}",
                                remediation=f"Remove or restrict '{pattern}' rule",
                            )
                        )


def _check_edit_permissions(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check for overly permissive edit rules."""
    edit_config = config.get("permission", {}).get("edit", {})

    if isinstance(edit_config, str) and edit_config == "allow":
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.MEDIUM,
                category="edit",
                title="Edit globally allowed",
                description=(
                    "All file edits are allowed without restrictions. "
                    "Consider restricting to specific file patterns."
                ),
                location="permission.edit",
                remediation=(
                    'Use granular permissions: {"*.md": "allow", "*": "ask"}'
                ),
            )
        )


def _check_external_directories(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check for exposed external directories."""
    ext_dir_config = config.get("permission", {}).get("external_directory", {})

    if isinstance(ext_dir_config, dict):
        for pattern, action in ext_dir_config.items():
            if action == "allow":
                # Check if pattern is too broad
                if pattern.endswith("**") or pattern.endswith("*"):
                    result.findings.append(
                        SecurityFinding(
                            severity=SecuritySeverity.MEDIUM,
                            category="external-directory",
                            title=f"Broad external directory access: '{pattern}'",
                            description=(
                                f"External directory pattern '{pattern}' grants "
                                f"access to a broad set of paths."
                            ),
                            location=f"permission.external_directory.{pattern}",
                            remediation=(
                                "Restrict to specific directories needed"
                            ),
                        )
                    )

    if not ext_dir_config:
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.LOW,
                category="external-directory",
                title="No external directory rules configured",
                description=(
                    "No external_directory rules found. Defaults to 'ask' "
                    "but explicit configuration is recommended."
                ),
                location="permission.external_directory",
                remediation="Add explicit external_directory rules",
            )
        )


def _check_doom_loop(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check for disabled doom_loop protection."""
    doom_config = config.get("permission", {}).get("doom_loop")

    if doom_config == "allow":
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.MEDIUM,
                category="doom-loop",
                title="Doom loop protection disabled",
                description=(
                    "The doom_loop protection is set to 'allow'. This means "
                    "the agent can enter infinite tool call loops without "
                    "intervention, potentially causing excessive API costs."
                ),
                location="permission.doom_loop",
                remediation="Set 'doom_loop': 'ask' or 'deny'",
            )
        )

    if not doom_config:
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.INFO,
                category="doom-loop",
                title="No explicit doom_loop configuration",
                description=(
                    "No doom_loop rule found. Defaults to 'ask' but explicit "
                    "configuration is recommended for cost control."
                ),
                location="permission.doom_loop",
                remediation="Add 'doom_loop': 'ask' for explicit control",
            )
        )


def _check_mcp_security(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check MCP server security."""
    mcp_config = config.get("mcp", {})

    if isinstance(mcp_config, dict):
        for name, server in mcp_config.items():
            if isinstance(server, dict):
                # Check for hardcoded credentials in environment
                env = server.get("environment", {})
                if isinstance(env, dict):
                    for key, value in env.items():
                        if any(
                            p in key.lower()
                            for p in ["key", "token", "secret", "password"]
                        ):
                            if isinstance(value, str) and value:
                                if not re.match(
                                    r"^\{env:[^}]+\}$|^\$\{[^}]+\}$|^\$[A-Z_]+$",
                                    value,
                                ):
                                    result.findings.append(
                                        SecurityFinding(
                                            severity=SecuritySeverity.CRITICAL,
                                            category="mcp",
                                            title=f"Hardcoded credential in MCP '{name}'",
                                            description=(
                                                f"MCP server '{name}' has a hardcoded "
                                                f"credential in environment variable "
                                                f"'{key}'."
                                            ),
                                            location=f"mcp.{name}.environment.{key}",
                                            remediation=(
                                                "Use {env:VAR_NAME} reference"
                                            ),
                                        )
                                    )

                # Check for insecure URLs
                url = server.get("url", "")
                if url and url.startswith("http://"):
                    result.findings.append(
                        SecurityFinding(
                            severity=SecuritySeverity.HIGH,
                            category="mcp",
                            title=f"Insecure MCP URL for '{name}'",
                            description=(
                                f"MCP server '{name}' uses HTTP instead of HTTPS. "
                                "Credentials and data will be transmitted in plaintext."
                            ),
                            location=f"mcp.{name}.url",
                            remediation="Use HTTPS URL",
                        )
                    )


def _check_agent_permissions(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check agent permission security."""
    agents = config.get("agent", {})

    if isinstance(agents, dict):
        for name, agent_config in agents.items():
            if isinstance(agent_config, dict):
                agent_perms = agent_config.get("permission", {})
                if isinstance(agent_perms, dict):
                    # Check for agents with weaker permissions than global
                    global_edit = config.get("permission", {}).get("edit", "allow")
                    agent_edit = agent_perms.get("edit")

                    if (
                        agent_edit == "allow"
                        and isinstance(global_edit, str)
                        and global_edit in ("ask", "deny")
                    ):
                        result.findings.append(
                            SecurityFinding(
                                severity=SecuritySeverity.MEDIUM,
                                category="agent",
                                title=f"Agent '{name}' has weaker edit restrictions",
                                description=(
                                    f"Agent '{name}' allows edits while global "
                                    f"config restricts them. This may bypass "
                                    f"intended security controls."
                                ),
                                location=f"agent.{name}.permission.edit",
                                remediation=(
                                    "Align agent permissions with global policy"
                                ),
                            )
                        )


def _check_plugin_security(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check plugin security."""
    plugins = config.get("plugin", [])

    if isinstance(plugins, list):
        for plugin in plugins:
            if isinstance(plugin, str):
                # Check for unpinned versions
                if "@latest" in plugin or ("@" not in plugin and "/" in plugin):
                    result.findings.append(
                        SecurityFinding(
                            severity=SecuritySeverity.LOW,
                            category="plugin",
                            title=f"Unpinned plugin version: '{plugin}'",
                            description=(
                                f"Plugin '{plugin}' is not pinned to a specific "
                                f"version. This may introduce unexpected changes."
                            ),
                            location=f"plugin[]",
                            remediation="Pin to specific version: plugin@1.2.3",
                        )
                    )


def _check_share_security(
    config: dict[str, Any],
    result: SecurityScanResult,
) -> None:
    """Check share configuration security."""
    share_config = config.get("share")

    if share_config == "auto":
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.LOW,
                category="share",
                title="Auto-sharing enabled",
                description=(
                    "Sessions are automatically shared. Ensure this is "
                    "intended and doesn't expose sensitive information."
                ),
                location="share",
                remediation="Set 'share': 'manual' for explicit control",
            )
        )

    if not share_config:
        result.findings.append(
            SecurityFinding(
                severity=SecuritySeverity.INFO,
                category="share",
                title="No share configuration",
                description=(
                    "No share setting found. Review sharing preferences "
                    "to ensure sensitive sessions aren't exposed."
                ),
                location="share",
                remediation="Set 'share' to 'manual', 'auto', or 'disabled'",
            )
        )


def _calculate_risk_score(result: SecurityScanResult) -> int:
    """Calculate risk score (0 = highest risk, 100 = no risk)."""
    score = 100

    # Deduct based on severity
    score -= result.critical_count * 25
    score -= result.high_count * 15
    score -= result.medium_count * 8
    score -= result.low_count * 3
    score -= result.info_count * 1

    return max(0, min(100, score))
