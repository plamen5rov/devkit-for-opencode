"""Tests for the Config Reader Tool."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from devkit.tools.config_reader import (
    ConfigReadResult,
    read_config,
    strip_jsonc_comments,
)


@pytest.fixture
def valid_json_config() -> Path:
    """Create a temporary valid JSON config file."""
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {
            "*": "ask",
            "bash": "allow",
            "edit": "allow",
        },
        "agent": {
            "build": {
                "mode": "primary",
                "model": "anthropic/claude-sonnet-4-20250514",
            },
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config, f)
        path = Path(f.name)
    yield path
    path.unlink()


@pytest.fixture
def valid_jsonc_config() -> Path:
    """Create a temporary valid JSONC config file."""
    content = """{
    // This is a comment
    "$schema": "https://opencode.ai/config.json",
    "model": "anthropic/claude-sonnet-4-20250514",
    /* Multi-line
       comment */
    "permission": {
        "*": "ask",
        "bash": "allow"
    }
}"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonc", delete=False) as f:
        f.write(content)
        path = Path(f.name)
    yield path
    path.unlink()


@pytest.fixture
def invalid_json_config() -> Path:
    """Create a temporary invalid JSON config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"model": "anthropic/claude", "permission": }')  # Missing value
        path = Path(f.name)
    yield path
    path.unlink()


def test_read_valid_json(valid_json_config: Path) -> None:
    """Test reading a valid JSON config file."""
    result = read_config(valid_json_config)
    assert result.success is True
    assert result.config["model"] == "anthropic/claude-sonnet-4-20250514"
    assert result.errors == []


def test_read_valid_jsonc(valid_jsonc_config: Path) -> None:
    """Test reading a valid JSONC config file with comments."""
    result = read_config(valid_jsonc_config)
    assert result.success is True
    assert result.config["model"] == "anthropic/claude-sonnet-4-20250514"
    assert result.errors == []


def test_read_invalid_json(invalid_json_config: Path) -> None:
    """Test reading an invalid JSON config file."""
    result = read_config(invalid_json_config)
    assert result.success is False
    assert len(result.errors) > 0
    assert "Invalid JSON" in result.errors[0]


def test_read_missing_file() -> None:
    """Test reading a missing config file."""
    result = read_config("/nonexistent/path/opencode.json")
    assert result.success is False
    assert "not found" in result.errors[0]


def test_missing_catchall_permission_warning(valid_json_config: Path) -> None:
    """Test warning for missing catch-all permission rule."""
    # Modify config to remove catch-all
    with open(valid_json_config) as f:
        config = json.load(f)
    del config["permission"]["*"]
    with open(valid_json_config, "w") as f:
        json.dump(config, f)

    result = read_config(valid_json_config)
    assert any("catch-all" in w for w in result.warnings)


def test_disabled_mcp_warning(valid_json_config: Path) -> None:
    """Test warning for disabled MCP server."""
    with open(valid_json_config) as f:
        config = json.load(f)
    config["mcp"] = {"test-server": {"type": "local", "command": ["npx", "test"], "enabled": False}}
    with open(valid_json_config, "w") as f:
        json.dump(config, f)

    result = read_config(valid_json_config)
    assert any("disabled" in w for w in result.warnings)


def test_disabled_agent_warning(valid_json_config: Path) -> None:
    """Test warning for disabled agent."""
    with open(valid_json_config) as f:
        config = json.load(f)
    config["agent"]["disabled-agent"] = {"mode": "subagent", "disable": True}
    with open(valid_json_config, "w") as f:
        json.dump(config, f)

    result = read_config(valid_json_config)
    assert any("disabled" in w for w in result.warnings)


def test_strip_jsonc_comments() -> None:
    """Test JSONC comment stripping."""
    content = """{
    // Single line comment
    "key": "value",
    /* Multi-line
       comment */
    "another": "test" // trailing comment
}"""
    result = strip_jsonc_comments(content)
    assert "//" not in result or '"//"' in result
    assert "/*" not in result
    assert "value" in result


def test_config_read_result_to_dict() -> None:
    """Test ConfigReadResult serialization."""
    result = ConfigReadResult(
        success=True,
        path="/test/path.json",
        config={"key": "value"},
        errors=[],
        warnings=["test warning"],
    )
    d = result.to_dict()
    assert d["success"] is True
    assert d["path"] == "/test/path.json"
    assert d["config"] == {"key": "value"}
    assert d["warnings"] == ["test warning"]
