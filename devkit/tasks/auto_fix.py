"""Auto-Remediation — Generate config patches for common issues.

Supports: permission tightening, deprecated field updates, model optimization,
MCP server cleanup, and agent configuration fixes.

Safety: preview mode, dry-run, user confirmation required.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class Patch:
    """A single configuration patch."""

    id: str
    description: str
    category: str
    severity: str  # required, recommended, optional
    before: Any
    after: Any
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "before": self.before,
            "after": self.after,
            "path": self.path,
        }


@dataclass
class RemediationResult:
    """Result of auto-remediation."""

    config_path: str
    patches: list[Patch] = field(default_factory=list)
    migrated_config: Optional[dict[str, Any]] = None
    dry_run: bool = True
    applied_count: int = 0
    skipped_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "patches": [p.to_dict() for p in self.patches],
            "total_patches": len(self.patches),
            "applied": self.applied_count,
            "skipped": self.skipped_count,
            "dry_run": self.dry_run,
            "migrated_config": self.migrated_config,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Auto-Remediation Report\n",
            f"**Config:** {self.config_path}\n",
            f"**Patches:** {len(self.patches)}\n",
            f"**Dry Run:** {self.dry_run}\n",
        ]

        if self.patches:
            lines.append("\n## Patches\n")
            for i, patch in enumerate(self.patches, 1):
                lines.append(f"### {i}. {patch.description}\n")
                lines.append(f"- **Category:** {patch.category}")
                lines.append(f"- **Severity:** {patch.severity}")
                lines.append(f"- **Path:** `{patch.path}`")
                lines.append(f"- **Before:** `{json.dumps(patch.before)}`")
                lines.append(f"- **After:** `{json.dumps(patch.after)}`")
                lines.append("")

        return "\n".join(lines)


def generate_patches(
    config: dict[str, Any],
    config_path: str,
    dry_run: bool = True,
    categories: Optional[list[str]] = None,
) -> RemediationResult:
    """Generate patches for common config issues.

    Args:
        config: The OpenCode configuration.
        config_path: Path to the config file.
        dry_run: If True, only generate patches without applying.
        categories: Filter by patch categories (None = all).

    Returns:
        RemediationResult with generated patches and optionally applied config.
    """
    result = RemediationResult(
        config_path=config_path,
        dry_run=dry_run,
    )

    migrated = copy.deepcopy(config)
    patch_id = 0

    # Permission patches
    if categories is None or "permission" in categories:
        for patch in _patch_permissions(config, migrated):
            patch_id += 1
            patch.id = f"perm-{patch_id}"
            result.patches.append(patch)

    # Deprecated field patches
    if categories is None or "deprecated" in categories:
        for patch in _patch_deprecated_fields(config, migrated):
            patch_id += 1
            patch.id = f"deprecated-{patch_id}"
            result.patches.append(patch)

    # Model optimization patches
    if categories is None or "model" in categories:
        for patch in _patch_model(config, migrated):
            patch_id += 1
            patch.id = f"model-{patch_id}"
            result.patches.append(patch)

    # MCP cleanup patches
    if categories is None or "mcp" in categories:
        for patch in _patch_mcp(config, migrated):
            patch_id += 1
            patch.id = f"mcp-{patch_id}"
            result.patches.append(patch)

    # Agent fix patches
    if categories is None or "agent" in categories:
        for patch in _patch_agents(config, migrated):
            patch_id += 1
            patch.id = f"agent-{patch_id}"
            result.patches.append(patch)

    # Apply patches if not dry run
    if not dry_run:
        result.migrated_config = migrated
        result.applied_count = len(result.patches)
    else:
        result.migrated_config = migrated  # Still show what it would look like
        result.skipped_count = len(result.patches)

    # Sort by severity
    severity_order = {"required": 0, "recommended": 1, "optional": 2}
    result.patches.sort(key=lambda p: severity_order.get(p.severity, 99))

    return result


def apply_patches_to_file(
    config_path: str,
    output_path: Optional[str] = None,
    dry_run: bool = True,
    categories: Optional[list[str]] = None,
) -> RemediationResult:
    """Generate and optionally apply patches to a config file.

    Args:
        config_path: Path to the config file.
        output_path: Output path for patched config (default: overwrite).
        dry_run: If True, only generate patches.
        categories: Filter by patch categories.

    Returns:
        RemediationResult with patches and applied config.
    """
    path = Path(config_path)
    if not path.exists():
        return RemediationResult(config_path=config_path, dry_run=dry_run)

    config = json.loads(path.read_text())
    result = generate_patches(config, config_path, dry_run, categories)

    if not dry_run and result.migrated_config:
        target = Path(output_path) if output_path else path
        target.write_text(json.dumps(result.migrated_config, indent=2) + "\n")

    return result


def _patch_permissions(
    config: dict[str, Any],
    migrated: dict[str, Any],
) -> list[Patch]:
    """Generate permission tightening patches."""
    patches = []

    # Add catch-all if missing
    global_perms = config.get("permission", {})
    if isinstance(global_perms, dict) and "*" not in global_perms:
        patches.append(Patch(
            id="",
            description="Add catch-all permission rule",
            category="permission",
            severity="required",
            before=None,
            after={"*": "ask"},
            path="permission.*",
        ))
        migrated.setdefault("permission", {})["*"] = "ask"

    # Remove globally allowed bash
    if isinstance(global_perms, dict) and global_perms.get("bash") == "allow":
        patches.append(Patch(
            id="",
            description="Remove globally allowed bash",
            category="permission",
            severity="recommended",
            before="allow",
            after="ask",
            path="permission.bash",
        ))
        migrated["permission"]["bash"] = "ask"

    # Remove globally allowed edit
    if isinstance(global_perms, dict) and global_perms.get("edit") == "allow":
        patches.append(Patch(
            id="",
            description="Remove globally allowed edit",
            category="permission",
            severity="recommended",
            before="allow",
            after="ask",
            path="permission.edit",
        ))
        migrated["permission"]["edit"] = "ask"

    return patches


def _patch_deprecated_fields(
    config: dict[str, Any],
    migrated: dict[str, Any],
) -> list[Patch]:
    """Generate patches for deprecated fields."""
    patches = []

    # Remove legacy tools field
    if "tools" in config:
        patches.append(Patch(
            id="",
            description="Remove deprecated 'tools' field",
            category="deprecated",
            severity="required",
            before=config["tools"],
            after=None,
            path="tools",
        ))
        migrated.pop("tools", None)

    # Convert boolean share to string
    if isinstance(config.get("share"), bool):
        old_value = config["share"]
        new_value = "manual" if old_value else "disabled"
        patches.append(Patch(
            id="",
            description=f"Convert boolean share to string ('{new_value}')",
            category="deprecated",
            severity="required",
            before=old_value,
            after=new_value,
            path="share",
        ))
        migrated["share"] = new_value

    return patches


def _patch_model(
    config: dict[str, Any],
    migrated: dict[str, Any],
) -> list[Patch]:
    """Generate model optimization patches."""
    patches = []

    # Add provider prefix if missing
    model = config.get("model", "")
    if model and "/" not in model:
        new_model = f"anthropic/{model}"
        patches.append(Patch(
            id="",
            description=f"Add provider prefix to model ('{new_model}')",
            category="model",
            severity="required",
            before=model,
            after=new_model,
            path="model",
        ))
        migrated["model"] = new_model

    # Add small_model if missing
    if "small_model" not in config:
        patches.append(Patch(
            id="",
            description="Add small_model for cost-efficient operations",
            category="model",
            severity="optional",
            before=None,
            after="anthropic/claude-haiku-4-20250313",
            path="small_model",
        ))
        migrated["small_model"] = "anthropic/claude-haiku-4-20250313"

    return patches


def _patch_mcp(
    config: dict[str, Any],
    migrated: dict[str, Any],
) -> list[Patch]:
    """Generate MCP cleanup patches."""
    patches = []

    mcp_servers = config.get("mcp", {}).get("servers", {})
    if isinstance(mcp_servers, dict):
        for name, server in mcp_servers.items():
            if isinstance(server, dict) and not server.get("enabled", True):
                patches.append(Patch(
                    id="",
                    description=f"Remove disabled MCP server '{name}'",
                    category="mcp",
                    severity="optional",
                    before=server,
                    after=None,
                    path=f"mcp.servers.{name}",
                ))
                migrated["mcp"]["servers"].pop(name, None)

            # Check for hardcoded secrets in headers
            if isinstance(server, dict) and "headers" in server:
                headers = server["headers"]
                if isinstance(headers, dict):
                    for key, value in headers.items():
                        if isinstance(value, str) and any(
                            p in key.lower() for p in ["secret", "key", "token"]
                        ):
                            if not value.startswith(("{env:", "${", "$")):
                                patches.append(Patch(
                                    id="",
                                    description=f"Replace hardcoded secret in MCP server '{name}' header '{key}'",
                                    category="mcp",
                                    severity="required",
                                    before=value[:10] + "...",
                                    after="{env:MCP_SECRET}",
                                    path=f"mcp.servers.{name}.headers.{key}",
                                ))
                                migrated["mcp"]["servers"][name]["headers"][key] = "{env:MCP_SECRET}"

    return patches


def _patch_agents(
    config: dict[str, Any],
    migrated: dict[str, Any],
) -> list[Patch]:
    """Generate agent configuration patches."""
    patches = []

    agents = config.get("agent", {})
    if isinstance(agents, dict):
        for name, agent_config in agents.items():
            if not isinstance(agent_config, dict):
                continue

            # Fix invalid temperature
            temp = agent_config.get("temperature")
            if temp is not None and (temp < 0 or temp > 1):
                patches.append(Patch(
                    id="",
                    description=f"Fix invalid temperature for agent '{name}' ({temp} → 0.7)",
                    category="agent",
                    severity="recommended",
                    before=temp,
                    after=0.7,
                    path=f"agent.{name}.temperature",
                ))
                migrated["agent"][name]["temperature"] = 0.7

            # Fix invalid top_p
            top_p = agent_config.get("top_p")
            if top_p is not None and (top_p < 0 or top_p > 1):
                patches.append(Patch(
                    id="",
                    description=f"Fix invalid top_p for agent '{name}' ({top_p} → 1.0)",
                    category="agent",
                    severity="recommended",
                    before=top_p,
                    after=1.0,
                    path=f"agent.{name}.top_p",
                ))
                migrated["agent"][name]["top_p"] = 1.0

            # Remove deprecated tools field
            if "tools" in agent_config:
                patches.append(Patch(
                    id="",
                    description=f"Remove deprecated 'tools' field from agent '{name}'",
                    category="agent",
                    severity="required",
                    before=agent_config["tools"],
                    after=None,
                    path=f"agent.{name}.tools",
                ))
                migrated["agent"][name].pop("tools", None)

    return patches
