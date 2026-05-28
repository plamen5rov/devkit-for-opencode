"""DevKit Orchestrator Agent — Coordinates all analysis.

Reads config, runs permission/agent/skill/MCP/command analyzers,
and produces a unified report with health score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from devkit.tools.agent_analyzer import analyze_agents
from devkit.tools.command_analyzer import analyze_commands
from devkit.tools.config_reader import read_config
from devkit.tools.mcp_analyzer import analyze_mcp_servers
from devkit.tools.permission_analyzer import analyze_permissions
from devkit.tools.skill_analyzer import analyze_skills


@dataclass
class OrchestratorResult:
    """Unified result from the orchestrator."""

    config_path: str
    config: dict[str, Any] = field(default_factory=dict)
    permissions: dict[str, Any] = field(default_factory=dict)
    agents: dict[str, Any] = field(default_factory=dict)
    skills: dict[str, Any] = field(default_factory=dict)
    mcp_servers: dict[str, Any] = field(default_factory=dict)
    commands: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "config": self.config,
            "permissions": self.permissions,
            "agents": self.agents,
            "skills": self.skills,
            "mcp_servers": self.mcp_servers,
            "commands": self.commands,
            "summary": self.summary,
            "issues": self.issues,
            "warnings": self.warnings,
        }


def run_orchestration(
    config_path: str,
    project_root: Optional[Path] = None,
    model: str = "anthropic/claude-sonnet-4-20250514",
    verbose: bool = False,
) -> OrchestratorResult:
    """Run the full orchestration pipeline.

    Args:
        config_path: Path to the OpenCode config file.
        project_root: Project root for local skill/command discovery.
        model: LLM model to use (kept for API compatibility).
        verbose: Enable verbose output.

    Returns:
        OrchestratorResult with unified analysis.
    """
    result = OrchestratorResult(config_path=config_path)

    # Step 1: Read config
    config_result = read_config(config_path)
    if not config_result.success:
        result.issues = config_result.errors
        return result

    config = config_result.config
    result.config = config

    # Step 2: Run all analyzers
    perm_result = analyze_permissions(config)
    result.permissions = perm_result.to_dict()
    result.issues.extend(perm_result.issues)
    result.warnings.extend(perm_result.warnings)

    agent_result = analyze_agents(config)
    result.agents = agent_result.to_dict()
    result.issues.extend(agent_result.issues)
    result.warnings.extend(agent_result.warnings)

    skill_result = analyze_skills(project_root, config)
    result.skills = skill_result.to_dict()
    result.issues.extend(skill_result.issues)
    result.warnings.extend(skill_result.warnings)

    mcp_result = analyze_mcp_servers(config)
    result.mcp_servers = mcp_result.to_dict()
    result.issues.extend(mcp_result.issues)
    result.warnings.extend(mcp_result.warnings)

    cmd_result = analyze_commands(project_root)
    result.commands = cmd_result.to_dict()
    result.issues.extend(cmd_result.issues)
    result.warnings.extend(cmd_result.warnings)

    # Step 3: Build summary
    result.summary = _build_summary(result)

    return result


def _build_summary(result: OrchestratorResult) -> dict[str, Any]:
    """Build a summary of the analysis."""
    return {
        "total_issues": len(result.issues),
        "total_warnings": len(result.warnings),
        "agent_count": result.agents.get("total_agents", 0),
        "skill_count": result.skills.get("total_skills", 0),
        "mcp_count": result.mcp_servers.get("enabled_count", 0),
        "command_count": result.commands.get("total_commands", 0),
        "mcp_token_estimate": result.mcp_servers.get("total_estimated_tokens", 0),
        "health_score": _calculate_health_score(result),
    }


def _calculate_health_score(result: OrchestratorResult) -> int:
    """Calculate a 0-100 health score based on analysis results."""
    score = 100

    # Deduct for issues (10 points each, max 50)
    issue_deduction = min(len(result.issues) * 10, 50)
    score -= issue_deduction

    # Deduct for warnings (5 points each, max 30)
    warning_deduction = min(len(result.warnings) * 5, 30)
    score -= warning_deduction

    # Deduct for high MCP token cost
    mcp_tokens = result.mcp_servers.get("total_estimated_tokens", 0)
    if mcp_tokens > 5000:
        score -= 10
    elif mcp_tokens > 3000:
        score -= 5

    # Deduct for no agents configured
    if result.agents.get("total_agents", 0) == 0:
        score -= 5

    # Deduct for no catch-all permission
    global_perms = result.config.get("permission", {})
    if isinstance(global_perms, dict) and "*" not in global_perms:
        score -= 5

    return max(0, min(100, score))
