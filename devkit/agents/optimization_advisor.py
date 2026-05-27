"""Optimization Advisor Agent — Suggests config improvements.

Role: Analyze config and suggest optimizations (token reduction, model selection,
permission tightening).
Tools: All Phase 2 tools + MCP analyzer.
Output: Prioritized recommendations with rationale and before/after comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from crewai import Agent, Task

from devkit.tools.agent_analyzer import analyze_agents
from devkit.tools.config_reader import read_config
from devkit.tools.mcp_analyzer import analyze_mcp_servers
from devkit.tools.permission_analyzer import analyze_permissions
from devkit.tools.skill_analyzer import analyze_skills


@dataclass
class Recommendation:
    """A single optimization recommendation."""

    category: str
    priority: int  # 1 = highest, 5 = lowest
    title: str
    description: str
    current_state: str
    suggested_state: str
    estimated_impact: str
    effort: str  # "low", "medium", "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "current_state": self.current_state,
            "suggested_state": self.suggested_state,
            "estimated_impact": self.estimated_impact,
            "effort": self.effort,
        }


@dataclass
class OptimizationResult:
    """Result of optimization analysis."""

    config_path: str
    recommendations: list[Recommendation] = field(default_factory=list)
    total_estimated_savings: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "total_recommendations": len(self.recommendations),
            "total_estimated_savings": self.total_estimated_savings,
        }


def create_optimization_advisor_agent(
    model: str = "anthropic/claude-sonnet-4-20250514",
    verbose: bool = False,
) -> Agent:
    """Create the optimization advisor CrewAI agent."""
    return Agent(
        role="OpenCode Optimization Advisor",
        goal="Suggest improvements for token usage, model selection, and permission tightening",
        backstory=(
            "You are a performance expert focused on reducing context costs, "
            "optimizing model selection, and tightening permissions in OpenCode "
            "configurations. You provide actionable recommendations with clear "
            "before/after comparisons."
        ),
        verbose=verbose,
        allow_delegation=False,
    )


def create_optimization_task(
    agent: Agent,
    config_path: str,
) -> Task:
    """Create the optimization task."""
    return Task(
        description=(
            f"Analyze the OpenCode configuration at {config_path} for optimization "
            "opportunities. Suggest improvements for token usage, model selection, "
            "and permission tightening."
        ),
        expected_output="JSON report with prioritized recommendations",
        agent=agent,
    )


def run_optimization(
    config_path: str,
) -> OptimizationResult:
    """Run optimization analysis.

    Args:
        config_path: Path to the OpenCode config file.

    Returns:
        OptimizationResult with prioritized recommendations.
    """
    result = OptimizationResult(config_path=config_path)

    # Read config
    config_result = read_config(config_path)
    if not config_result.success:
        return result

    config = config_result.config

    # Run all analyzers
    _optimize_permissions(config, result)
    _optimize_agents(config, result)
    _optimize_mcp(config, result)
    _optimize_skills(config, result)
    _optimize_models(config, result)

    # Sort by priority
    result.recommendations.sort(key=lambda r: r.priority)

    # Estimate total savings
    result.total_estimated_savings = _estimate_total_savings(result)

    return result


def _optimize_permissions(
    config: dict[str, Any],
    result: OptimizationResult,
) -> None:
    """Suggest permission optimizations."""
    perm_result = analyze_permissions(config)
    global_perms = config.get("permission", {})

    # Check for overly permissive bash
    if isinstance(global_perms.get("bash"), str) and global_perms["bash"] == "allow":
        result.recommendations.append(
            Recommendation(
                category="permissions",
                priority=1,
                title="Tighten bash permissions",
                description=(
                    "Bash is globally allowed. Restrict to specific commands "
                    "to reduce security risk."
                ),
                current_state='"bash": "allow"',
                suggested_state=(
                    '"bash": {"*": "ask", "git *": "allow", "npm *": "allow"}'
                ),
                estimated_impact="Improved security",
                effort="low",
            )
        )

    # Check for missing catch-all
    if isinstance(global_perms, dict) and "*" not in global_perms:
        result.recommendations.append(
            Recommendation(
                category="permissions",
                priority=2,
                title="Add catch-all permission rule",
                description=(
                    "No catch-all permission rule found. Add '*': 'ask' "
                    "as a default to prevent unintended tool access."
                ),
                current_state="No '*' rule",
                suggested_state='"*": "ask"',
                estimated_impact="Prevents unintended tool access",
                effort="low",
            )
        )

    # Check for denied tools that might be needed
    for tool, eff in perm_result.effective_matrix.items():
        if eff.action == "deny" and tool in ("read", "glob", "grep"):
            result.recommendations.append(
                Recommendation(
                    category="permissions",
                    priority=3,
                    title=f"Review '{tool}' denial",
                    description=(
                        f"Tool '{tool}' is denied. This may limit the agent's "
                        "ability to analyze the codebase."
                    ),
                    current_state=f'"{tool}": "deny"',
                    suggested_state=f'"{tool}": "allow"',
                    estimated_impact="Improved agent capability",
                    effort="low",
                )
            )


def _optimize_agents(
    config: dict[str, Any],
    result: OptimizationResult,
) -> None:
    """Suggest agent optimizations."""
    agent_result = analyze_agents(config)

    for name, info in agent_result.agents.items():
        # Check for missing model override
        if not info.model and info.is_builtin:
            result.recommendations.append(
                Recommendation(
                    category="agents",
                    priority=3,
                    title=f"Set model for agent '{name}'",
                    description=(
                        f"Agent '{name}' uses the default model. Consider "
                        "setting a specific model optimized for its purpose."
                    ),
                    current_state="No model override",
                    suggested_state='"model": "anthropic/claude-haiku-4-20250514"',
                    estimated_impact="Better cost/performance balance",
                    effort="low",
                )
            )

        # Check for high temperature on analysis agents
        if info.temperature and info.temperature > 0.5:
            if "plan" in name.lower() or "review" in name.lower():
                result.recommendations.append(
                    Recommendation(
                        category="agents",
                        priority=2,
                        title=f"Lower temperature for agent '{name}'",
                        description=(
                            f"Agent '{name}' has temperature {info.temperature}. "
                            "Analysis agents benefit from lower temperatures "
                            "for more deterministic output."
                        ),
                        current_state=f'"temperature": {info.temperature}',
                        suggested_state='"temperature": 0.1',
                        estimated_impact="More consistent analysis output",
                        effort="low",
                    )
                )

        # Check for disabled agents that may be referenced
        if info.disabled:
            result.recommendations.append(
                Recommendation(
                    category="agents",
                    priority=4,
                    title=f"Remove or enable agent '{name}'",
                    description=(
                        f"Agent '{name}' is disabled. If not referenced, "
                        "consider removing it to reduce config complexity."
                    ),
                    current_state='"disable": true',
                    suggested_state="Remove agent or set 'disable': false",
                    estimated_impact="Cleaner configuration",
                    effort="low",
                )
            )


def _optimize_mcp(
    config: dict[str, Any],
    result: OptimizationResult,
) -> None:
    """Suggest MCP optimizations."""
    mcp_result = analyze_mcp_servers(config)

    if mcp_result.total_estimated_tokens > 3000:
        result.recommendations.append(
            Recommendation(
                category="mcp",
                priority=1,
                title="Reduce MCP token cost",
                description=(
                    f"Total estimated MCP token cost is "
                    f"~{mcp_result.total_estimated_tokens} tokens. "
                    "Consider disabling unused servers."
                ),
                current_state=f"~{mcp_result.total_estimated_tokens} tokens",
                suggested_state="< 2000 tokens",
                estimated_impact="Reduced context usage per session",
                effort="medium",
            )
        )

    # Check for disabled servers
    for name, server in mcp_result.servers.items():
        if not server.enabled:
            result.recommendations.append(
                Recommendation(
                    category="mcp",
                    priority=4,
                    title=f"Remove disabled MCP server '{name}'",
                    description=(
                        f"Server '{name}' is disabled. Remove it to reduce "
                        "config complexity."
                    ),
                    current_state=f'"enabled": false',
                    suggested_state="Remove server entry",
                    estimated_impact="Cleaner configuration",
                    effort="low",
                )
            )


def _optimize_skills(
    config: dict[str, Any],
    result: OptimizationResult,
) -> None:
    """Suggest skill optimizations."""
    skill_result = analyze_skills(config=config)

    # Check for skills with deny permissions
    for name, skill in skill_result.skills.items():
        for agent, status in skill.permission_status.items():
            if status == "deny":
                result.recommendations.append(
                    Recommendation(
                        category="skills",
                        priority=3,
                        title=f"Review skill '{name}' denied for '{agent}'",
                        description=(
                            f"Skill '{name}' is denied for agent '{agent}'. "
                            "If the agent needs this skill, update permissions."
                        ),
                        current_state=f'"{name}": deny for {agent}',
                        suggested_state=f'"{name}": allow for {agent}',
                        estimated_impact="Improved agent capability",
                        effort="low",
                    )
                )

    # Check for duplicate skills
    if any("Duplicate" in i for i in skill_result.issues):
        result.recommendations.append(
            Recommendation(
                category="skills",
                priority=2,
                title="Resolve duplicate skill names",
                description=(
                    "Duplicate skill names found. Skills must have unique "
                    "names across all search paths."
                ),
                current_state="Duplicate skill names",
                suggested_state="Unique skill names",
                estimated_impact="Prevents skill loading conflicts",
                effort="medium",
            )
        )


def _optimize_models(
    config: dict[str, Any],
    result: OptimizationResult,
) -> None:
    """Suggest model optimizations."""
    # Check for missing small_model
    if "small_model" not in config:
        result.recommendations.append(
            Recommendation(
                category="models",
                priority=3,
                title="Configure small_model",
                description=(
                    "No small_model configured. Use a faster, cheaper model "
                    "for title generation and summaries."
                ),
                current_state="No small_model",
                suggested_state=(
                    '"small_model": "anthropic/claude-haiku-4-20250514"'
                ),
                estimated_impact="Reduced cost for metadata operations",
                effort="low",
            )
        )

    # Check if primary model is a high-cost model without small_model
    model = config.get("model", "")
    if "opus" in model.lower() and "small_model" not in config:
        result.recommendations.append(
            Recommendation(
                category="models",
                priority=2,
                title="Pair high-cost model with small_model",
                description=(
                    f"Using '{model}' as primary model without a small_model. "
                    "Consider adding a cheaper model for metadata operations."
                ),
                current_state=f'"model": "{model}"',
                suggested_state=(
                    f'"model": "{model}", '
                    '"small_model": "anthropic/claude-haiku-4-20250514"'
                ),
                estimated_impact="Reduced cost for title/summary generation",
                effort="low",
            )
        )


def _estimate_total_savings(result: OptimizationResult) -> str:
    """Estimate total savings from all recommendations."""
    high_priority = sum(
        1 for r in result.recommendations if r.priority <= 2
    )
    medium_priority = sum(
        1 for r in result.recommendations if r.priority == 3
    )

    if high_priority >= 2:
        return "Significant — multiple high-priority optimizations available"
    elif high_priority == 1:
        return "Moderate — one high-priority optimization available"
    elif medium_priority >= 1:
        return "Minor — medium-priority optimizations available"
    else:
        return "Minimal — configuration is well-optimized"
