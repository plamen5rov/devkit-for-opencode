"""Agent Config Analyzer Tool — Analyzes OpenCode agent definitions.

Extracts agent modes, models, prompts, permissions.
Detects misconfigurations (missing models, invalid modes, disabled with references).
Reports agent dependency graph (who invokes whom via task permissions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


VALID_MODES = {"primary", "subagent", "all"}
BUILTIN_AGENTS = {"build", "plan", "general", "explore", "scout"}
HIDDEN_SYSTEM_AGENTS = {"compaction", "title", "summary"}


@dataclass
class AgentInfo:
    """Parsed agent information."""

    name: str
    mode: str = "all"
    model: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    steps: Optional[int] = None
    disabled: bool = False
    hidden: bool = False
    color: Optional[str] = None
    permission: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] = field(default_factory=dict)
    task_permissions: dict[str, str] = field(default_factory=dict)
    is_builtin: bool = False
    is_hidden_system: bool = False
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class AgentDependency:
    """Dependency between agents."""

    from_agent: str
    to_agent: str
    permission: str  # "allow", "ask", "deny"
    pattern: str


@dataclass
class AgentAnalysisResult:
    """Result of agent analysis."""

    agents: dict[str, AgentInfo] = field(default_factory=dict)
    dependencies: list[AgentDependency] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": {
                name: {
                    "name": a.name,
                    "mode": a.mode,
                    "model": a.model,
                    "description": a.description,
                    "temperature": a.temperature,
                    "disabled": a.disabled,
                    "hidden": a.hidden,
                    "is_builtin": a.is_builtin,
                    "is_hidden_system": a.is_hidden_system,
                    "issues": a.issues,
                    "warnings": a.warnings,
                }
                for name, a in self.agents.items()
            },
            "dependencies": [
                {
                    "from_agent": d.from_agent,
                    "to_agent": d.to_agent,
                    "permission": d.permission,
                    "pattern": d.pattern,
                }
                for d in self.dependencies
            ],
            "issues": self.issues,
            "warnings": self.warnings,
            "total_agents": len(self.agents),
            "total_dependencies": len(self.dependencies),
        }


def analyze_agents(config: dict[str, Any]) -> AgentAnalysisResult:
    """Analyze all agent definitions in an OpenCode config.

    Args:
        config: Parsed OpenCode configuration.

    Returns:
        AgentAnalysisResult with parsed agents, dependencies, and issues.
    """
    result = AgentAnalysisResult()

    raw_agents = config.get("agent", {})
    if not isinstance(raw_agents, dict):
        result.issues.append("Agent config is not a dictionary")
        return result

    for name, agent_config in raw_agents.items():
        if not isinstance(agent_config, dict):
            result.issues.append(f"Agent '{name}' config is not a dictionary")
            continue

        info = _parse_agent(name, agent_config)
        result.agents[name] = info
        result.issues.extend(info.issues)
        result.warnings.extend(info.warnings)

    # Build dependency graph from task permissions
    _build_dependencies(result)

    # Cross-agent checks
    _cross_agent_checks(result)

    return result


def _parse_agent(name: str, config: dict[str, Any]) -> AgentInfo:
    """Parse a single agent definition."""
    info = AgentInfo(name=name)

    info.mode = config.get("mode", "all")
    info.model = config.get("model")
    info.description = config.get("description")
    info.prompt = config.get("prompt")
    info.temperature = config.get("temperature")
    info.top_p = config.get("top_p")
    info.steps = config.get("steps")
    info.disabled = config.get("disable", False)
    info.hidden = config.get("hidden", False)
    info.color = config.get("color")

    if "permission" in config:
        info.permission = dict(config["permission"])
        # Extract task permissions
        if "task" in info.permission:
            task_config = info.permission["task"]
            if isinstance(task_config, dict):
                info.task_permissions = task_config
            elif isinstance(task_config, str):
                info.task_permissions = {"*": task_config}

    if "tools" in config:
        info.tools = dict(config["tools"])

    # Check if builtin or hidden system agent
    info.is_builtin = name in BUILTIN_AGENTS
    info.is_hidden_system = name in HIDDEN_SYSTEM_AGENTS

    # Validate
    _validate_agent(info)

    return info


def _validate_agent(info: AgentInfo) -> None:
    """Validate an agent definition and populate issues/warnings."""
    # Check mode validity
    if info.mode not in VALID_MODES:
        info.issues.append(
            f"Invalid mode '{info.mode}' — must be one of {VALID_MODES}"
        )

    # Check temperature range
    if info.temperature is not None:
        if not (0.0 <= info.temperature <= 1.0):
            info.warnings.append(
                f"Temperature {info.temperature} outside typical range [0.0, 1.0]"
            )

    # Check top_p range
    if info.top_p is not None:
        if not (0.0 <= info.top_p <= 1.0):
            info.warnings.append(
                f"Top_p {info.top_p} outside typical range [0.0, 1.0]"
            )

    # Check steps is positive
    if info.steps is not None and info.steps <= 0:
        info.issues.append(f"Steps must be positive, got {info.steps}")

    # Check for deprecated tools field
    if info.tools:
        info.warnings.append(
            "Uses deprecated 'tools' field — prefer 'permission' for fine-grained control"
        )

    # Check disabled subagent with task references
    if info.disabled and info.mode == "subagent":
        info.warnings.append(
            "Disabled subagent cannot be invoked — remove or enable"
        )

    # Check for missing description
    if not info.description and not info.is_hidden_system:
        info.warnings.append("No description — agents should have a clear purpose")

    # Check model format
    if info.model and "/" not in info.model:
        info.warnings.append(
            f"Model '{info.model}' may be missing provider prefix (expected 'provider/model')"
        )


def _build_dependencies(result: AgentAnalysisResult) -> None:
    """Build agent dependency graph from task permissions."""
    for name, agent_info in result.agents.items():
        for pattern, permission in agent_info.task_permissions.items():
            # Resolve pattern to actual agents
            for target_name in result.agents:
                if target_name == name:
                    continue
                if _matches_pattern(target_name, pattern):
                    result.dependencies.append(
                        AgentDependency(
                            from_agent=name,
                            to_agent=target_name,
                            permission=permission,
                            pattern=pattern,
                        )
                    )


def _matches_pattern(name: str, pattern: str) -> bool:
    """Check if an agent name matches a permission pattern."""
    import fnmatch
    return fnmatch.fnmatch(name, pattern)


def _cross_agent_checks(result: AgentAnalysisResult) -> None:
    """Cross-agent validation checks."""
    # Check for circular dependencies
    visited = set()
    for dep in result.dependencies:
        if dep.permission == "deny":
            continue
        edge = (dep.from_agent, dep.to_agent)
        reverse = (dep.to_agent, dep.from_agent)
        if reverse in visited:
            result.warnings.append(
                f"Potential circular dependency: {dep.from_agent} <-> {dep.to_agent}"
            )
        visited.add(edge)

    # Check for agents with no task access
    for name, info in result.agents.items():
        if info.mode == "primary" and info.task_permissions:
            denied_all = all(
                p == "deny" for p in info.task_permissions.values()
            )
            if denied_all:
                result.warnings.append(
                    f"Primary agent '{name}' has all subagents denied — cannot delegate"
                )

    # Check for duplicate agent names with builtins
    for name, info in result.agents.items():
        if info.is_builtin and not info.is_hidden_system:
            result.warnings.append(
                f"Custom agent '{name}' overrides built-in agent — this may cause conflicts"
            )
