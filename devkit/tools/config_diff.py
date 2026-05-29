"""Config Diff Tool — Compare two OpenCode configs and report differences.

Supports:
- Comparing two config files or inline JSON blobs
- Diffing against a historical analysis record (by record ID)
- Section-grouped output with added/removed/changed fields
- Markdown diff report generation
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from devkit.tools.config_reader import read_config


KNOWN_SECTIONS = [
    "model", "small_model", "permission", "agent", "mcp",
    "plugin", "share", "snapshot", "autoupdate", "tools",
    "command", "skill", "theme", "keys", "$schema",
]


@dataclass
class DiffEntry:
    """A single field-level difference."""

    path: str
    left_value: Any
    right_value: Any
    change_type: str  # "added", "removed", "changed"
    section: str  # top-level section this belongs to

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "left_value": self.left_value,
            "right_value": self.right_value,
            "change_type": self.change_type,
            "section": self.section,
        }


@dataclass
class ConfigDiff:
    """Result of comparing two OpenCode configs."""

    from_label: str  # label for the left/source config
    to_label: str  # label for the right/target config
    entries: list[DiffEntry] = field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0
    changed_count: int = 0
    total_changes: int = 0
    from_config: dict[str, Any] = field(default_factory=dict)
    to_config: dict[str, Any] = field(default_factory=dict)
    parse_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_label": self.from_label,
            "to_label": self.to_label,
            "entries": [e.to_dict() for e in self.entries],
            "added_count": self.added_count,
            "removed_count": self.removed_count,
            "changed_count": self.changed_count,
            "total_changes": self.total_changes,
            "from_config": self.from_config,
            "to_config": self.to_config,
            "parse_errors": self.parse_errors,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Config Diff Report",
            "",
            f"**From:** `{self.from_label}`",
            f"**To:** `{self.to_label}`",
            "",
        ]

        if self.parse_errors:
            lines.extend([
                "## Parse Errors",
                "",
            ])
            for err in self.parse_errors:
                lines.append(f"- {err}")
            lines.append("")

        lines.extend([
            f"| Type | Count |",
            f"|------|-------|",
            f"| Added | {self.added_count} |",
            f"| Removed | {self.removed_count} |",
            f"| Changed | {self.changed_count} |",
            f"| **Total** | **{self.total_changes}** |",
            "",
        ])

        sections = _group_by_section(self.entries)
        for section_name, entries in sections.items():
            lines.extend([
                f"## {section_name}",
                f"",
                f"| Path | Left Value | Right Value | Type |",
                f"|------|------------|-------------|------|",
            ])
            for entry in entries:
                left = _format_value(entry.left_value) if entry.change_type != "added" else "—"
                right = _format_value(entry.right_value) if entry.change_type != "removed" else "—"
                lines.append(
                    f"| `{entry.path}` | `{left}` | `{right}` | {entry.change_type} |"
                )
            lines.append("")

        if not self.entries:
            lines.append("No differences found — configs are identical.")

        return "\n".join(lines)


def diff_configs(
    from_config: dict[str, Any],
    to_config: dict[str, Any],
    from_label: str = "from",
    to_label: str = "to",
) -> ConfigDiff:
    """Compare two config dictionaries and return a ConfigDiff.

    Args:
        from_config: The source/left config dict.
        to_config: The target/right config dict.
        from_label: Label for the source config.
        to_label: Label for the target config.

    Returns:
        ConfigDiff with all differences.
    """
    entries: list[DiffEntry] = []

    _deep_diff("", from_config, to_config, entries)

    added = sum(1 for e in entries if e.change_type == "added")
    removed = sum(1 for e in entries if e.change_type == "removed")
    changed = sum(1 for e in entries if e.change_type == "changed")

    return ConfigDiff(
        from_label=from_label,
        to_label=to_label,
        entries=entries,
        added_count=added,
        removed_count=removed,
        changed_count=changed,
        total_changes=len(entries),
        from_config=from_config,
        to_config=to_config,
    )


def diff_config_files(
    from_path: str,
    to_path: str,
) -> ConfigDiff:
    """Compare two config files by path.

    Args:
        from_path: Path to the source config file.
        to_path: Path to the target config file.

    Returns:
        ConfigDiff with all differences.
    """
    from_result = read_config(from_path)
    to_result = read_config(to_path)

    return diff_configs(
        from_config=from_result.config or {},
        to_config=to_result.config or {},
        from_label=str(from_path),
        to_label=str(to_path),
    )


def diff_config_strings(
    from_json: str,
    to_json: str,
    from_label: str = "from",
    to_label: str = "to",
) -> ConfigDiff:
    """Compare two config JSON strings.

    Args:
        from_json: Source config as JSON string.
        to_json: Target config as JSON string.
        from_label: Label for the source config.
        to_label: Label for the target config.

    Returns:
        ConfigDiff with all differences.
    """
    from_config, from_err = _parse_jsonc(from_json)
    to_config, to_err = _parse_jsonc(to_json)

    result = diff_configs(
        from_config=from_config,
        to_config=to_config,
        from_label=from_label,
        to_label=to_label,
    )

    parse_errors = []
    if from_err:
        parse_errors.append(f"[from] {from_err}")
    if to_err:
        parse_errors.append(f"[to] {to_err}")
    result.parse_errors = parse_errors

    return result


def diff_config_against_history(
    config_json: str,
    record_id: int,
    db_path: Optional[str] = None,
) -> Optional[ConfigDiff]:
    """Compare a config against a historical analysis record.

    Args:
        config_json: Current config as JSON string.
        record_id: ID of the historical analysis record.
        db_path: Path to the history database.

    Returns:
        ConfigDiff or None if record not found.
    """
    from devkit.memory.history import AnalysisHistoryStore

    db_path = db_path or str(
        Path.home() / ".local" / "share" / "devkit" / "history.db"
    )

    store = AnalysisHistoryStore(Path(db_path))
    record = store.get_record(record_id)

    if not record or not record.raw_report:
        return None

    try:
        raw = json.loads(record.raw_report)
    except json.JSONDecodeError:
        return None

    from_config = raw.get("from_config", {})
    if not from_config:
        from_config = _extract_config_from_report(raw)

    current_config, err = _parse_jsonc(config_json)
    result = diff_configs(
        from_config=from_config,
        to_config=current_config,
        from_label=f"record #{record_id} ({record.timestamp[:10]})",
        to_label="current",
    )
    if err:
        result.parse_errors.append(f"[to] {err}")
    return result


def _deep_diff(
    prefix: str,
    left: Any,
    right: Any,
    entries: list[DiffEntry],
) -> None:
    """Recursively diff two JSON values."""
    if prefix:
        section = prefix.split(".")[0]
    else:
        section = "root"

    if isinstance(left, dict) and isinstance(right, dict):
        all_keys = set(left.keys()) | set(right.keys())
        for key in sorted(all_keys):
            child_prefix = f"{prefix}.{key}" if prefix else key
            if key not in left:
                entries.append(DiffEntry(
                    path=child_prefix,
                    left_value=None,
                    right_value=right[key],
                    change_type="added",
                    section=_find_section(child_prefix),
                ))
            elif key not in right:
                entries.append(DiffEntry(
                    path=child_prefix,
                    left_value=left[key],
                    right_value=None,
                    change_type="removed",
                    section=_find_section(child_prefix),
                ))
            else:
                _deep_diff(child_prefix, left[key], right[key], entries)

    elif isinstance(left, list) and isinstance(right, list):
        max_len = max(len(left), len(right))
        for i in range(max_len):
            child_prefix = f"{prefix}[{i}]"
            if i >= len(left):
                entries.append(DiffEntry(
                    path=child_prefix,
                    left_value=None,
                    right_value=right[i],
                    change_type="added",
                    section=_find_section(prefix),
                ))
            elif i >= len(right):
                entries.append(DiffEntry(
                    path=child_prefix,
                    left_value=left[i],
                    right_value=None,
                    change_type="removed",
                    section=_find_section(prefix),
                ))
            else:
                _deep_diff(child_prefix, left[i], right[i], entries)

    elif left != right:
        entries.append(DiffEntry(
            path=prefix,
            left_value=left,
            right_value=right,
            change_type="changed",
            section=_find_section(prefix),
        ))


def _find_section(path: str) -> str:
    """Extract the top-level section name from a dot path."""
    if not path:
        return "root"
    first = path.split(".")[0].split("[")[0]
    if first in KNOWN_SECTIONS:
        return first
    return "other"


def _group_by_section(entries: list[DiffEntry]) -> dict[str, list[DiffEntry]]:
    """Group diff entries by their section name in a stable order."""
    order = {s: i for i, s in enumerate(KNOWN_SECTIONS + ["other"])}
    groups: dict[str, list[DiffEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.section, []).append(entry)
    return dict(sorted(groups.items(), key=lambda x: order.get(x[0], 99)))


def _parse_jsonc(raw: str) -> tuple[dict[str, Any], Optional[str]]:
    """Parse a JSON/JSONC string into a dict.

    Returns:
        Tuple of (parsed_config, error_message_or_None).
        On parse failure, returns ({}, error_message).
    """
    import re
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
    lines = raw.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        if "//" in line:
            line = re.sub(r"(?<!:)//.*$", "", line)
        cleaned.append(line)
    raw = "\n".join(cleaned)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return {}, f"JSON parse error: {e}"


def _extract_config_from_report(raw_report: dict[str, Any]) -> dict[str, Any]:
    """Try to extract the original config from an analysis report."""
    if "config" in raw_report:
        return raw_report["config"]
    if "raw_analyses" in raw_report:
        ra = raw_report["raw_analyses"]
        if "config" in ra and isinstance(ra["config"], dict):
            return ra["config"]
    return {}


def _format_value(val: Any) -> str:
    """Format a value for markdown display."""
    if val is None:
        return "null"
    if isinstance(val, (dict, list)):
        s = json.dumps(val, indent=None)
        if len(s) > 60:
            return s[:57] + "..."
        return s
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val)
    if len(s) > 60:
        return s[:57] + "..."
    return s
