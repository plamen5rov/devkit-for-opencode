"""Config Reader Tool — Reads and parses OpenCode configuration files.

Supports both JSON and JSONC (JSON with comments) formats.
Validates against the OpenCode config schema.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft7Validator, ValidationError


# Minimal OpenCode config schema (covers top-level fields)
OPENCODE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "$schema": {"type": "string"},
        "model": {"type": "string"},
        "small_model": {"type": "string"},
        "plugin": {"type": "array", "items": {"type": "string"}},
        "permission": {
            "oneOf": [
                {"type": "string", "enum": ["allow", "ask", "deny"]},
                {"type": "object"},
            ]
        },
        "agent": {"type": "object"},
        "mcp": {"type": "object"},
        "command": {"type": "object"},
        "tools": {"type": "object"},
        "share": {"type": "string", "enum": ["manual", "auto", "disabled"]},
        "snapshot": {"type": "boolean"},
        "autoupdate": {"type": "string"},
    },
    "additionalProperties": True,
}


@dataclass
class ConfigReadResult:
    """Result of reading and parsing an OpenCode config file."""

    success: bool
    path: str
    config: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "path": self.path,
            "config": self.config,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def strip_jsonc_comments(content: str) -> str:
    """Remove single-line (//) and multi-line (/* */) comments from JSONC content."""
    # Remove multi-line comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove single-line comments (but not inside strings)
    lines = content.split("\n")
    cleaned_lines = []
    for line in lines:
        # Simple heuristic: if // appears before any quote, it's a comment
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        # Remove trailing // comments (naive but works for most configs)
        if "//" in line:
            # Check if // is inside a string (between quotes)
            in_string = False
            comment_start = -1
            for i, char in enumerate(line):
                if char == '"' and (i == 0 or line[i - 1] != "\\"):
                    in_string = not in_string
                elif not in_string and line[i : i + 2] == "//":
                    comment_start = i
                    break
            if comment_start > 0:
                line = line[:comment_start].rstrip()
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def detect_config_paths() -> list[Path]:
    """Auto-detect OpenCode config files in standard locations."""
    candidates = [
        Path(".opencode/opencode.json"),
        Path(".opencode/opencode.jsonc"),
        Path(os.path.expanduser("~/.config/opencode/opencode.json")),
        Path(os.path.expanduser("~/.config/opencode/opencode.jsonc")),
    ]
    return [p for p in candidates if p.exists()]


def read_config(path: str | Path) -> ConfigReadResult:
    """Read and parse an OpenCode config file.

    Args:
        path: Path to the config file (JSON or JSONC).

    Returns:
        ConfigReadResult with parsed config, errors, and warnings.
    """
    config_path = Path(path)
    result = ConfigReadResult(success=False, path=str(config_path))

    if not config_path.exists():
        result.errors.append(f"Config file not found: {config_path}")
        return result

    try:
        raw_content = config_path.read_text(encoding="utf-8")
        result.raw_content = raw_content
    except Exception as e:
        result.errors.append(f"Failed to read file: {e}")
        return result

    # Parse JSON or JSONC
    try:
        if config_path.suffix == ".jsonc":
            cleaned = strip_jsonc_comments(raw_content)
            config = json.loads(cleaned)
        else:
            config = json.loads(raw_content)
    except json.JSONDecodeError as e:
        result.errors.append(f"Invalid JSON: {e}")
        return result

    result.config = config

    # Validate against schema
    validator = Draft7Validator(OPENCODE_SCHEMA)
    schema_errors = list(validator.iter_errors(config))
    for error in schema_errors:
        path_str = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        result.errors.append(f"Schema error at {path_str}: {error.message}")

    # Check for common issues
    if "permission" in config and isinstance(config["permission"], dict):
        if "*" not in config["permission"]:
            result.warnings.append(
                "No catch-all permission rule ('*') found. "
                "Tools not explicitly listed may use defaults."
            )

    if "mcp" in config and isinstance(config["mcp"], dict):
        for name, mcp_config in config["mcp"].items():
            if isinstance(mcp_config, dict) and mcp_config.get("enabled") is False:
                result.warnings.append(f"MCP server '{name}' is disabled")

    if "agent" in config and isinstance(config["agent"], dict):
        for name, agent_config in config["agent"].items():
            if isinstance(agent_config, dict) and agent_config.get("disable") is True:
                result.warnings.append(f"Agent '{name}' is disabled")

    result.success = len(result.errors) == 0
    return result


def read_all_configs() -> list[ConfigReadResult]:
    """Read all detected OpenCode config files."""
    paths = detect_config_paths()
    if not paths:
        return [ConfigReadResult(success=False, path="none", errors=["No config files found"])]
    return [read_config(p) for p in paths]
