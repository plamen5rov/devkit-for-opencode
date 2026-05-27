"""Permission Analyzer Tool — Analyzes OpenCode permission rules.

Evaluates permission precedence (global → agent → granular).
Reports effective permissions for any tool/action.
Outputs structured permission matrix.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Optional


# Known permission keys and the tools they gate
PERMISSION_TOOL_MAP = {
    "read": ["read"],
    "edit": ["write", "edit", "apply_patch"],
    "glob": ["glob"],
    "grep": ["grep"],
    "list": ["list"],
    "bash": ["bash"],
    "task": ["task"],
    "external_directory": ["external_directory"],
    "todowrite": ["todowrite", "todoread"],
    "webfetch": ["webfetch"],
    "websearch": ["websearch"],
    "lsp": ["lsp"],
    "skill": ["skill"],
    "question": ["question"],
    "doom_loop": ["doom_loop"],
}

VALID_ACTIONS = {"allow", "ask", "deny"}


@dataclass
class PermissionEntry:
    """A single permission rule."""

    tool: str
    pattern: str
    action: str
    source: str  # "global", "agent:<name>", or "granular"
    is_default: bool = False


@dataclass
class EffectivePermission:
    """Resolved permission for a specific tool."""

    tool: str
    action: str
    matched_pattern: str
    source: str
    chain: list[str] = field(default_factory=list)


@dataclass
class PermissionAnalysisResult:
    """Result of permission analysis."""

    global_permissions: dict[str, Any] = field(default_factory=dict)
    agent_permissions: dict[str, dict[str, Any]] = field(default_factory=dict)
    effective_matrix: dict[str, EffectivePermission] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    all_entries: list[PermissionEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_permissions": self.global_permissions,
            "agent_permissions": self.agent_permissions,
            "effective_matrix": {
                k: {
                    "tool": v.tool,
                    "action": v.action,
                    "matched_pattern": v.matched_pattern,
                    "source": v.source,
                    "chain": v.chain,
                }
                for k, v in self.effective_matrix.items()
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "total_rules": len(self.all_entries),
        }


def _match_pattern(pattern: str, value: str) -> bool:
    """Check if a value matches a permission pattern (supports * and ? wildcards)."""
    return fnmatch.fnmatch(value, pattern)


def _resolve_granular_permission(granular_config: dict[str, str], tool_value: str) -> tuple[str, str]:
    """Resolve a granular permission config to (action, matched_pattern).

    Uses last-match-wins semantics.
    """
    action = "ask"  # Default if no pattern matches
    matched = "*"
    for pattern, rule_action in granular_config.items():
        if _match_pattern(pattern, tool_value):
            action = rule_action
            matched = pattern
    return action, matched


def analyze_permissions(config: dict[str, Any]) -> PermissionAnalysisResult:
    """Analyze all permission rules in an OpenCode config.

    Args:
        config: Parsed OpenCode configuration.

    Returns:
        PermissionAnalysisResult with resolved permissions and issues.
    """
    result = PermissionAnalysisResult()

    # Extract global permissions
    raw_permissions = config.get("permission", {})
    if isinstance(raw_permissions, str):
        # Shorthand: "permission": "allow" means all tools allowed
        result.global_permissions = {"*": raw_permissions}
    else:
        result.global_permissions = dict(raw_permissions)

    # Extract agent permissions
    agents = config.get("agent", {})
    for agent_name, agent_config in agents.items():
        if isinstance(agent_config, dict) and "permission" in agent_config:
            result.agent_permissions[agent_name] = agent_config["permission"]

    # Build permission entries from global config
    for tool_or_pattern, rule in result.global_permissions.items():
        if tool_or_pattern == "external_directory":
            continue  # Handle separately
        if isinstance(rule, str):
            entry = PermissionEntry(
                tool=tool_or_pattern,
                pattern=tool_or_pattern,
                action=rule,
                source="global",
            )
            result.all_entries.append(entry)
        elif isinstance(rule, dict):
            # Granular permission
            for pattern, action in rule.items():
                entry = PermissionEntry(
                    tool=tool_or_pattern,
                    pattern=pattern,
                    action=action,
                    source="global",
                )
                result.all_entries.append(entry)

    # Build permission entries from agent configs
    for agent_name, perms in result.agent_permissions.items():
        for tool_or_pattern, rule in perms.items():
            if isinstance(rule, str):
                entry = PermissionEntry(
                    tool=tool_or_pattern,
                    pattern=tool_or_pattern,
                    action=rule,
                    source=f"agent:{agent_name}",
                )
                result.all_entries.append(entry)
            elif isinstance(rule, dict):
                for pattern, action in rule.items():
                    entry = PermissionEntry(
                        tool=tool_or_pattern,
                        pattern=pattern,
                        action=action,
                        source=f"agent:{agent_name}",
                    )
                    result.all_entries.append(entry)

    # Resolve effective permissions for all known tools
    for perm_key, tools in PERMISSION_TOOL_MAP.items():
        for tool in tools:
            chain = []
            final_action = "allow"  # Default
            final_pattern = "*"
            final_source = "default"

            # Check global permissions
            if perm_key in result.global_permissions:
                rule = result.global_permissions[perm_key]
                if isinstance(rule, str):
                    chain.append(f"global:{perm_key}={rule}")
                    final_action = rule
                    final_pattern = perm_key
                    final_source = "global"
                elif isinstance(rule, dict):
                    action, matched = _resolve_granular_permission(rule, tool)
                    chain.append(f"global:{perm_key}.{matched}={action}")
                    final_action = action
                    final_pattern = matched
                    final_source = "global"

            result.effective_matrix[tool] = EffectivePermission(
                tool=tool,
                action=final_action,
                matched_pattern=final_pattern,
                source=final_source,
                chain=chain,
            )

    # Check for issues
    _check_issues(result, config)

    return result


def _check_issues(result: PermissionAnalysisResult, config: dict[str, Any]) -> None:
    """Check for permission-related issues and warnings."""
    # Check for overly permissive bash rules
    bash_config = result.global_permissions.get("bash", {})
    if isinstance(bash_config, str) and bash_config == "allow":
        result.warnings.append("Bash is globally allowed without restrictions")
    elif isinstance(bash_config, dict):
        if "*" in bash_config and bash_config["*"] == "allow":
            result.warnings.append("Bash catch-all rule allows all commands")
        dangerous_patterns = ["rm *", "rmdir *", "pkill *", "kill *", "chmod *", "chown *"]
        for pattern in dangerous_patterns:
            if pattern in bash_config and bash_config[pattern] == "allow":
                result.issues.append(f"Dangerous bash command allowed: {pattern}")

    # Check for doom_loop protection
    if "doom_loop" not in result.global_permissions:
        result.warnings.append("No explicit doom_loop protection configured (defaults to 'ask')")

    # Check for external_directory restrictions
    if "external_directory" not in result.global_permissions:
        result.warnings.append("No external_directory rules configured (defaults to 'ask')")

    # Check for agent permission overrides that weaken global rules
    global_edit = result.global_permissions.get("edit", "allow")
    for agent_name, agent_perms in result.agent_permissions.items():
        agent_edit = agent_perms.get("edit", None)
        if agent_edit and isinstance(global_edit, str) and isinstance(agent_edit, str):
            action_order = {"deny": 0, "ask": 1, "allow": 2}
            if action_order.get(agent_edit, 1) > action_order.get(global_edit, 1):
                result.warnings.append(
                    f"Agent '{agent_name}' has weaker edit restrictions than global "
                    f"(global={global_edit}, agent={agent_edit})"
                )

    # Check for deny rules that might break expected functionality
    for tool, eff in result.effective_matrix.items():
        if eff.action == "deny" and eff.source != "default":
            result.warnings.append(f"Tool '{tool}' is denied via {eff.source}")


def get_effective_permission(
    result: PermissionAnalysisResult,
    tool: str,
    value: str = "",
) -> EffectivePermission:
    """Get the effective permission for a specific tool and value.

    Args:
        result: Permission analysis result.
        tool: Tool name (e.g., "bash", "edit", "read").
        value: Specific value to match (e.g., bash command, file path).

    Returns:
        EffectivePermission with resolved action and chain.
    """
    if tool in result.effective_matrix:
        return result.effective_matrix[tool]

    # Try to resolve from raw config
    for perm_key, rule in result.global_permissions.items():
        if isinstance(rule, dict):
            action, matched = _resolve_granular_permission(rule, value)
            return EffectivePermission(
                tool=tool,
                action=action,
                matched_pattern=matched,
                source=f"global:{perm_key}",
                chain=[f"{perm_key}.{matched}={action}"],
            )

    return EffectivePermission(
        tool=tool,
        action="allow",
        matched_pattern="*",
        source="default",
        chain=["default=allow"],
    )
