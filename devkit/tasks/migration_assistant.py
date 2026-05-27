"""Migration Assistant Task — Help migrate between OpenCode versions.

Detects deprecated config fields (e.g., tools boolean → permission).
Suggests updated config syntax.
Generates migration diff.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from devkit.tools.config_reader import read_config


@dataclass
class MigrationChange:
    """A single migration change."""

    field: str
    old_value: Any
    new_value: Any
    reason: str
    severity: str  # "required", "recommended", "optional"

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "severity": self.severity,
        }


@dataclass
class MigrationReport:
    """Result of migration analysis."""

    config_path: str
    source_version: str = "unknown"
    target_version: str = "latest"
    changes: list[MigrationChange] = field(default_factory=list)
    migrated_config: dict[str, Any] = field(default_factory=dict)
    is_migrated: bool = False
    required_count: int = 0
    recommended_count: int = 0
    optional_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "source_version": self.source_version,
            "target_version": self.target_version,
            "changes": [c.to_dict() for c in self.changes],
            "migrated_config": self.migrated_config,
            "is_migrated": self.is_migrated,
            "required_count": self.required_count,
            "recommended_count": self.recommended_count,
            "optional_count": self.optional_count,
        }

    def to_markdown(self) -> str:
        """Generate a Markdown migration report."""
        lines = [
            "# Migration Report",
            f"",
            f"**Config:** `{self.config_path}`",
            f"**Source Version:** {self.source_version}",
            f"**Target Version:** {self.target_version}",
            f"**Status:** {'Migrated' if self.is_migrated else 'No changes needed'}",
            f"",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| Required | {self.required_count} |",
            f"| Recommended | {self.recommended_count} |",
            f"| Optional | {self.optional_count} |",
            f"",
        ]

        if self.changes:
            lines.extend([
                "## Changes",
                f"",
                f"| Field | Old Value | New Value | Reason | Severity |",
                f"|-------|-----------|-----------|--------|----------|",
            ])
            for change in self.changes:
                old = json.dumps(change.old_value) if not isinstance(change.old_value, str) else change.old_value
                new = json.dumps(change.new_value) if not isinstance(change.new_value, str) else change.new_value
                lines.append(
                    f"| `{change.field}` | `{old}` | `{new}` "
                    f"| {change.reason} | {change.severity} |"
                )
            lines.append("")

        return "\n".join(lines)


def run_migration_analysis(
    config_path: str,
) -> MigrationReport:
    """Run migration analysis.

    Args:
        config_path: Path to the OpenCode config file.

    Returns:
        MigrationReport with changes and migrated config.
    """
    report = MigrationReport(config_path=config_path)

    # Read config - use raw content even if schema validation fails
    config_result = read_config(config_path)
    if not config_result.raw_content:
        return report

    # Parse raw config (ignore schema errors for migration)
    import re
    import json as json_mod
    raw = config_result.raw_content
    # Strip comments for JSONC
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
    lines = raw.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        cleaned.append(line)
    raw = "\n".join(cleaned)

    try:
        config = json_mod.loads(raw)
    except json_mod.JSONDecodeError:
        return report

    migrated = copy.deepcopy(config)

    # Run migration checks
    _migrate_tools_to_permission(config, migrated, report)
    _migrate_legacy_models(config, migrated, report)
    _migrate_deprecated_fields(config, migrated, report)
    _migrate_share_config(config, migrated, report)
    _migrate_plugin_config(config, migrated, report)

    # Count by severity
    report.required_count = sum(
        1 for c in report.changes if c.severity == "required"
    )
    report.recommended_count = sum(
        1 for c in report.changes if c.severity == "recommended"
    )
    report.optional_count = sum(
        1 for c in report.changes if c.severity == "optional"
    )

    report.migrated_config = migrated
    report.is_migrated = len(report.changes) > 0

    return report


def _migrate_tools_to_permission(
    config: dict[str, Any],
    migrated: dict[str, Any],
    report: MigrationReport,
) -> None:
    """Migrate legacy tools boolean to permission system."""
    # Top-level tools field (deprecated)
    if "tools" in config:
        tools_config = config["tools"]
        if isinstance(tools_config, dict):
            # Convert to permission format
            if "permission" not in migrated:
                migrated["permission"] = {}

            permission = migrated["permission"]

            for tool, enabled in tools_config.items():
                if tool in ("read", "edit", "glob", "grep", "bash", "lsp", "skill", "question", "webfetch", "websearch"):
                    old_value = tools_config[tool]
                    new_value = "allow" if enabled else "deny"
                    if tool not in permission:
                        permission[tool] = new_value
                        report.changes.append(
                            MigrationChange(
                                field=f"tools.{tool}",
                                old_value=old_value,
                                new_value=f"permission.{tool}: {new_value}",
                                reason=(
                                    f"Legacy 'tools.{tool}: {old_value}' "
                                    f"migrated to permission system"
                                ),
                                severity="required",
                            )
                        )

            # Remove old tools field
            if "tools" in migrated:
                del migrated["tools"]
                report.changes.append(
                    MigrationChange(
                        field="tools",
                        old_value="(legacy tools config)",
                        new_value="(removed, migrated to permission)",
                        reason="Legacy 'tools' field deprecated, use 'permission' instead",
                        severity="required",
                    )
                )

        elif isinstance(tools_config, bool):
            # Boolean tools config (very old format)
            if "permission" not in migrated:
                migrated["permission"] = {}
            migrated["permission"]["*"] = "allow" if tools_config else "ask"
            del migrated["tools"]
            report.changes.append(
                MigrationChange(
                    field="tools",
                    old_value=tools_config,
                    new_value=f"permission.*: {'allow' if tools_config else 'ask'}",
                    reason="Boolean 'tools' field deprecated, use granular permissions",
                    severity="required",
                )
            )

    # Agent-level tools field (deprecated)
    agents = config.get("agent", {})
    if isinstance(agents, dict):
        for name, agent_config in agents.items():
            if isinstance(agent_config, dict) and "tools" in agent_config:
                agent_tools = agent_config["tools"]
                if isinstance(agent_tools, dict):
                    if "permission" not in migrated.get("agent", {}).get(name, {}):
                        if "agent" not in migrated:
                            migrated["agent"] = {}
                        if name not in migrated["agent"]:
                            migrated["agent"][name] = copy.deepcopy(agent_config)
                        if "permission" not in migrated["agent"][name]:
                            migrated["agent"][name]["permission"] = {}

                    for tool, enabled in agent_tools.items():
                        new_value = "allow" if enabled else "deny"
                        migrated["agent"][name]["permission"][tool] = new_value
                        report.changes.append(
                            MigrationChange(
                                field=f"agent.{name}.tools.{tool}",
                                old_value=enabled,
                                new_value=f"permission.{tool}: {new_value}",
                                reason=(
                                    f"Legacy agent tools field migrated to "
                                    f"permission system"
                                ),
                                severity="required",
                            )
                        )

                    if "tools" in migrated.get("agent", {}).get(name, {}):
                        del migrated["agent"][name]["tools"]


def _migrate_legacy_models(
    config: dict[str, Any],
    migrated: dict[str, Any],
    report: MigrationReport,
) -> None:
    """Migrate legacy model formats."""
    model = config.get("model", "")
    if model and "/" not in model:
        # Try to infer provider
        model_lower = model.lower()
        if "claude" in model_lower:
            new_model = f"anthropic/{model}"
        elif "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            new_model = f"openai/{model}"
        elif "gemini" in model_lower:
            new_model = f"google/{model}"
        else:
            new_model = model  # Can't infer, leave as-is

        if new_model != model:
            migrated["model"] = new_model
            report.changes.append(
                MigrationChange(
                    field="model",
                    old_value=model,
                    new_value=new_model,
                    reason="Model missing provider prefix",
                    severity="recommended",
                )
            )


def _migrate_deprecated_fields(
    config: dict[str, Any],
    migrated: dict[str, Any],
    report: MigrationReport,
) -> None:
    """Migrate other deprecated fields."""
    # Check for old "context_length" field (if it existed)
    if "context_length" in config:
        del migrated["context_length"]
        report.changes.append(
            MigrationChange(
                field="context_length",
                old_value=config["context_length"],
                new_value="(removed)",
                reason="context_length is no longer supported",
                severity="required",
            )
        )

    # Check for old "temperature" at top level (should be in agent)
    if "temperature" in config:
        del migrated["temperature"]
        report.changes.append(
            MigrationChange(
                field="temperature",
                old_value=config["temperature"],
                new_value="(moved to agent config)",
                reason="Top-level temperature deprecated, use agent.temperature",
                severity="recommended",
            )
        )


def _migrate_share_config(
    config: dict[str, Any],
    migrated: dict[str, Any],
    report: MigrationReport,
) -> None:
    """Migrate legacy share configuration."""
    share = config.get("share")
    if isinstance(share, bool):
        new_share = "auto" if share else "disabled"
        migrated["share"] = new_share
        report.changes.append(
            MigrationChange(
                field="share",
                old_value=share,
                new_value=new_share,
                reason="Boolean share deprecated, use string values",
                severity="required",
            )
        )


def _migrate_plugin_config(
    config: dict[str, Any],
    migrated: dict[str, Any],
    report: MigrationReport,
) -> None:
    """Migrate plugin configuration."""
    plugins = config.get("plugin", [])
    if isinstance(plugins, list):
        for i, plugin in enumerate(plugins):
            if isinstance(plugin, str) and "@latest" in plugin:
                report.changes.append(
                    MigrationChange(
                        field=f"plugin[{i}]",
                        old_value=plugin,
                        new_value=plugin.replace("@latest", "@<version>"),
                        reason=(
                            "Using @latest is discouraged; pin to specific version "
                            "for reproducibility"
                        ),
                        severity="recommended",
                    )
                )


def generate_migration_diff(
    config_path: str,
    output_path: Optional[str] = None,
) -> tuple[MigrationReport, Optional[Path]]:
    """Run migration analysis and optionally save the migrated config.

    Args:
        config_path: Path to the OpenCode config file.
        output_path: Path to save migrated config (default: None).

    Returns:
        Tuple of (MigrationReport, output_path).
    """
    report = run_migration_analysis(config_path)

    saved_path = None
    if output_path and report.is_migrated:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report.migrated_config, indent=2),
            encoding="utf-8",
        )
        saved_path = path

    return report, saved_path
