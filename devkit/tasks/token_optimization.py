"""Token Optimization Task — Analyze and reduce token usage.

Analyzes: MCP server token costs, agent model selection, skill description length,
command template size.
Suggests: Model downgrades for simple tasks, skill deduplication, command consolidation.
Output: Token usage report with optimization recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from devkit.tools.agent_analyzer import analyze_agents
from devkit.tools.command_analyzer import analyze_commands
from devkit.tools.config_reader import read_config
from devkit.tools.mcp_analyzer import analyze_mcp_servers, MCP_TOKEN_ESTIMATES
from devkit.tools.skill_analyzer import analyze_skills


@dataclass
class TokenRecommendation:
    """A token optimization recommendation."""

    category: str
    title: str
    description: str
    current_tokens: int
    estimated_savings: int
    effort: str  # "low", "medium", "high"
    action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "current_tokens": self.current_tokens,
            "estimated_savings": self.estimated_savings,
            "effort": self.effort,
            "action": self.action,
        }


@dataclass
class TokenUsageReport:
    """Token usage analysis report."""

    config_path: str
    total_estimated_tokens: int = 0
    mcp_tokens: int = 0
    agent_tokens: int = 0
    skill_tokens: int = 0
    command_tokens: int = 0
    recommendations: list[TokenRecommendation] = field(default_factory=list)
    breakdown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "total_estimated_tokens": self.total_estimated_tokens,
            "mcp_tokens": self.mcp_tokens,
            "agent_tokens": self.agent_tokens,
            "skill_tokens": self.skill_tokens,
            "command_tokens": self.command_tokens,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "breakdown": self.breakdown,
        }

    def to_markdown(self) -> str:
        """Generate a Markdown token report."""
        lines = [
            "# Token Usage Report",
            f"",
            f"**Config:** `{self.config_path}`",
            f"**Total Estimated Tokens:** ~{self.total_estimated_tokens}",
            f"",
            "## Breakdown",
            f"",
            f"| Category | Tokens | % of Total |",
            f"|----------|--------|------------|",
        ]

        total = max(self.total_estimated_tokens, 1)
        for category, tokens in [
            ("MCP Servers", self.mcp_tokens),
            ("Agents", self.agent_tokens),
            ("Skills", self.skill_tokens),
            ("Commands", self.command_tokens),
        ]:
            pct = (tokens / total) * 100
            lines.append(f"| {category} | ~{tokens} | {pct:.1f}% |")

        lines.append("")

        if self.recommendations:
            lines.extend([
                "## Recommendations",
                f"",
                f"**Potential Savings:** ~{sum(r.estimated_savings for r in self.recommendations)} tokens",
                f"",
                f"| Category | Title | Savings | Effort |",
                f"|----------|-------|---------|--------|",
            ])
            for rec in self.recommendations:
                lines.append(
                    f"| {rec.category} | {rec.title} "
                    f"| ~{rec.estimated_savings} | {rec.effort} |"
                )
            lines.append("")

        return "\n".join(lines)


def run_token_analysis(
    config_path: str,
) -> TokenUsageReport:
    """Run token usage analysis.

    Args:
        config_path: Path to the OpenCode config file.

    Returns:
        TokenUsageReport with breakdown and recommendations.
    """
    report = TokenUsageReport(config_path=config_path)

    # Read config
    config_result = read_config(config_path)
    if not config_result.success:
        return report

    config = config_result.config

    # Analyze MCP tokens
    mcp_result = analyze_mcp_servers(config)
    report.mcp_tokens = mcp_result.total_estimated_tokens

    # Estimate agent tokens (based on model context windows)
    agent_result = analyze_agents(config)
    report.agent_tokens = _estimate_agent_tokens(agent_result)

    # Estimate skill tokens (based on description lengths)
    skill_result = analyze_skills(config=config)
    report.skill_tokens = _estimate_skill_tokens(skill_result)

    # Estimate command tokens (based on template sizes)
    cmd_result = analyze_commands()
    report.command_tokens = _estimate_command_tokens(cmd_result)

    # Total
    report.total_estimated_tokens = (
        report.mcp_tokens
        + report.agent_tokens
        + report.skill_tokens
        + report.command_tokens
    )

    # Build breakdown
    report.breakdown = {
        "mcp_servers": {
            name: server.estimated_tokens
            for name, server in mcp_result.servers.items()
            if server.enabled
        },
        "agents": {
            name: _get_agent_token_estimate(info)
            for name, info in agent_result.agents.items()
        },
        "skills": {
            name: len(skill.description)
            for name, skill in skill_result.skills.items()
            if skill.is_valid
        },
        "commands": {
            name: len(cmd.template)
            for name, cmd in cmd_result.commands.items()
        },
    }

    # Generate recommendations
    _recommend_mcp_optimizations(mcp_result, report)
    _recommend_agent_optimizations(agent_result, report)
    _recommend_skill_optimizations(skill_result, report)
    _recommend_command_optimizations(cmd_result, report)

    # Sort by savings
    report.recommendations.sort(
        key=lambda r: r.estimated_savings, reverse=True
    )

    return report


def _estimate_agent_tokens(agent_result: Any) -> int:
    """Estimate token cost for agent configurations."""
    total = 0
    for name, info in agent_result.agents.items():
        total += _get_agent_token_estimate(info)
    return total


def _get_agent_token_estimate(info: Any) -> int:
    """Estimate tokens for a single agent config."""
    # Base cost for agent definition
    tokens = 100

    # Add for description length
    if info.description:
        tokens += len(info.description) // 4

    # Add for prompt (if file reference, estimate)
    if info.prompt:
        tokens += 200  # Assume prompt file is ~200 tokens

    # Add for permission config
    if info.permission:
        tokens += len(info.permission) * 20

    return tokens


def _estimate_skill_tokens(skill_result: Any) -> int:
    """Estimate token cost for skill configurations."""
    total = 0
    for name, skill in skill_result.skills.items():
        if skill.is_valid:
            # Description + frontmatter overhead
            total += len(skill.description) // 4 + 50
    return total


def _estimate_command_tokens(cmd_result: Any) -> int:
    """Estimate token cost for command configurations."""
    total = 0
    for name, cmd in cmd_result.commands.items():
        # Template + frontmatter overhead
        total += len(cmd.template) // 4 + 30
    return total


def _recommend_mcp_optimizations(
    mcp_result: Any,
    report: TokenUsageReport,
) -> None:
    """Generate MCP token optimization recommendations."""
    # High token cost servers
    for name, server in mcp_result.servers.items():
        if server.enabled and server.estimated_tokens > 1000:
            report.recommendations.append(
                TokenRecommendation(
                    category="mcp",
                    title=f"Consider disabling high-cost MCP '{name}'",
                    description=(
                        f"Server '{name}' costs ~{server.estimated_tokens} tokens. "
                        f"If not frequently used, disable it."
                    ),
                    current_tokens=server.estimated_tokens,
                    estimated_savings=server.estimated_tokens,
                    effort="low",
                    action=f'Set "enabled": false for "{name}"',
                )
            )

    # Disabled servers still in config
    for name, server in mcp_result.servers.items():
        if not server.enabled:
            report.recommendations.append(
                TokenRecommendation(
                    category="mcp",
                    title=f"Remove disabled MCP '{name}'",
                    description=(
                        f"Server '{name}' is disabled but still in config. "
                        f"Remove to reduce config parsing overhead."
                    ),
                    current_tokens=0,
                    estimated_savings=10,
                    effort="low",
                    action=f'Remove "{name}" from mcp config',
                )
            )


def _recommend_agent_optimizations(
    agent_result: Any,
    report: TokenUsageReport,
) -> None:
    """Generate agent token optimization recommendations."""
    for name, info in agent_result.agents.items():
        # Agents using high-cost models for simple tasks
        model = info.model or ""
        if "opus" in model.lower() and "plan" in name.lower():
            report.recommendations.append(
                TokenRecommendation(
                    category="agent",
                    title=f"Downgrade model for agent '{name}'",
                    description=(
                        f"Agent '{name}' uses Opus model but appears to be "
                        f"a planning agent. Consider a cheaper model."
                    ),
                    current_tokens=_get_agent_token_estimate(info),
                    estimated_savings=200,
                    effort="low",
                    action=(
                        f'Set "model": "anthropic/claude-haiku-4-20250514" '
                        f'for "{name}"'
                    ),
                )
            )

        # Disabled agents still in config
        if info.disabled:
            report.recommendations.append(
                TokenRecommendation(
                    category="agent",
                    title=f"Remove disabled agent '{name}'",
                    description=(
                        f"Agent '{name}' is disabled but still in config. "
                        f"Remove to reduce config size."
                    ),
                    current_tokens=_get_agent_token_estimate(info),
                    estimated_savings=50,
                    effort="low",
                    action=f'Remove "{name}" from agent config',
                )
            )


def _recommend_skill_optimizations(
    skill_result: Any,
    report: TokenUsageReport,
) -> None:
    """Generate skill token optimization recommendations."""
    # Long descriptions
    for name, skill in skill_result.skills.items():
        if len(skill.description) > 500:
            report.recommendations.append(
                TokenRecommendation(
                    category="skill",
                    title=f"Shorten description for skill '{name}'",
                    description=(
                        f"Skill '{name}' has a {len(skill.description)}-character "
                        f"description. Shorten to reduce token overhead."
                    ),
                    current_tokens=len(skill.description) // 4 + 50,
                    estimated_savings=(len(skill.description) - 200) // 4,
                    effort="medium",
                    action=f"Reduce description to ~200 characters",
                )
            )

    # Duplicate skills
    if any("Duplicate" in i for i in skill_result.issues):
        report.recommendations.append(
            TokenRecommendation(
                category="skill",
                title="Resolve duplicate skills",
                description=(
                    "Duplicate skill names cause redundant token loading. "
                    "Ensure unique names across all search paths."
                ),
                current_tokens=0,
                estimated_savings=100,
                effort="medium",
                action="Rename or remove duplicate skills",
            )
        )


def _recommend_command_optimizations(
    cmd_result: Any,
    report: TokenUsageReport,
) -> None:
    """Generate command token optimization recommendations."""
    # Large templates
    for name, cmd in cmd_result.commands.items():
        if len(cmd.template) > 1000:
            report.recommendations.append(
                TokenRecommendation(
                    category="command",
                    title=f"Condense command template '{name}'",
                    description=(
                        f"Command '{name}' has a {len(cmd.template)}-character "
                        f"template. Consider using a file reference instead."
                    ),
                    current_tokens=len(cmd.template) // 4 + 30,
                    estimated_savings=(len(cmd.template) - 500) // 4,
                    effort="medium",
                    action="Use @file reference or shorten template",
                )
            )
