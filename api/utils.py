"""Utility functions shared across API routes."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from devkit.tools.config_reader import read_config


def detect_config() -> Optional[Path]:
    """Auto-detect OpenCode config file."""
    candidates = [
        Path(".opencode/opencode.json"),
        Path(".opencode/opencode.jsonc"),
        Path(os.path.expanduser("~/.config/opencode/opencode.json")),
        Path(os.path.expanduser("~/.config/opencode/opencode.jsonc")),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_config_path(config_path: Optional[str]) -> Optional[Path]:
    """Resolve config path from request or auto-detect."""
    if config_path:
        p = Path(config_path)
        if p.exists():
            return p
        return None
    return detect_config()


def strip_jsonc_comments(raw: str) -> str:
    """Strip comments from JSONC content."""
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
    lines = raw.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def validate_config_content(raw: str) -> dict:
    """Validate raw config content and return parsed result with errors."""
    errors = []
    cleaned = strip_jsonc_comments(raw)
    try:
        config = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {"valid": False, "errors": [f"JSON parse error: {e}"], "config": None}

    # Basic structural checks
    if not isinstance(config, dict):
        errors.append("Config must be a JSON object")
        return {"valid": False, "errors": errors, "config": None}

    # Check for known top-level fields
    known_fields = {
        "model", "small_model", "permission", "agent", "mcp",
        "plugin", "share", "snapshot", "autoupdate", "tools",
        "command", "skill", "theme", "keys",
    }
    unknown = set(config.keys()) - known_fields
    if unknown:
        errors.append(f"Unknown top-level fields: {', '.join(sorted(unknown))}")

    # Check model format
    model = config.get("model", "")
    if model and isinstance(model, str) and "/" not in model:
        errors.append(f"Model '{model}' missing provider prefix (e.g., 'anthropic/')")

    # Check permission structure
    perm = config.get("permission", {})
    if isinstance(perm, dict) and "*" not in perm:
        errors.append("No catch-all permission rule ('*') found")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "config": config,
    }
