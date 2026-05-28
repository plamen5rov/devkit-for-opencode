"""Tests for the DevKit Orchestrator Agent."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from devkit.agents.orchestrator import (
    OrchestratorResult,
    run_orchestration,
    _build_summary,
    _calculate_health_score,
)


@pytest.fixture
def valid_config_file(tmp_path: Path) -> Path:
    """Create a temporary valid config file."""
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {
            "*": "ask",
            "bash": {
                "*": "ask",
                "git *": "allow",
                "npm *": "allow",
            },
            "edit": "allow",
        },
        "agent": {
            "build": {
                "mode": "primary",
                "model": "anthropic/claude-sonnet-4-20250514",
                "description": "Build agent",
            },
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def minimal_config_file(tmp_path: Path) -> Path:
    """Create a minimal config file."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


def test_run_orchestration_valid_config(valid_config_file: Path) -> None:
    """Test running orchestration with a valid config."""
    result = run_orchestration(str(valid_config_file))
    assert result.config_path == str(valid_config_file)
    assert result.config["model"] == "anthropic/claude-sonnet-4-20250514"
    assert result.permissions is not None
    assert result.agents is not None
    assert result.summary is not None


def test_run_orchestration_minimal_config(minimal_config_file: Path) -> None:
    """Test running orchestration with a minimal config."""
    result = run_orchestration(str(minimal_config_file))
    assert result.config_path == str(minimal_config_file)
    assert result.config["model"] == "anthropic/claude-sonnet-4-20250514"


def test_run_orchestration_missing_file() -> None:
    """Test running orchestration with a missing config."""
    result = run_orchestration("/nonexistent/opencode.json")
    assert not result.config
    assert len(result.issues) > 0
    assert any("not found" in i.lower() for i in result.issues)


def test_build_summary() -> None:
    """Test summary building."""
    result = OrchestratorResult(
        config_path="/test.json",
        config={"permission": {"*": "ask"}},
        issues=["issue1", "issue2"],
        warnings=["warn1"],
    )
    summary = _build_summary(result)
    assert summary["total_issues"] == 2
    assert summary["total_warnings"] == 1


def test_health_score_perfect() -> None:
    """Test perfect health score."""
    result = OrchestratorResult(
        config_path="/test.json",
        config={
            "permission": {"*": "ask"},
            "agent": {"build": {"mode": "primary", "description": "Build"}},
        },
        agents={"total_agents": 1},
        issues=[],
        warnings=[],
    )
    score = _calculate_health_score(result)
    assert score == 100


def test_health_score_issues() -> None:
    """Test health score deduction for issues."""
    result = OrchestratorResult(
        config_path="/test.json",
        config={"permission": {"*": "ask"}},
        issues=["issue1", "issue2", "issue3"],
        warnings=[],
    )
    score = _calculate_health_score(result)
    assert score < 100
    assert score >= 0


def test_health_score_warnings() -> None:
    """Test health score deduction for warnings."""
    result = OrchestratorResult(
        config_path="/test.json",
        config={"permission": {"*": "ask"}},
        issues=[],
        warnings=["w1", "w2", "w3", "w4", "w5", "w6"],
    )
    score = _calculate_health_score(result)
    assert score < 100


def test_health_score_high_mcp_tokens() -> None:
    """Test health score deduction for high MCP tokens."""
    result = OrchestratorResult(
        config_path="/test.json",
        config={"permission": {"*": "ask"}},
        issues=[],
        warnings=[],
    )
    result.mcp_servers = {"total_estimated_tokens": 6000}
    score = _calculate_health_score(result)
    assert score <= 90


def test_health_score_no_catchall() -> None:
    """Test health score deduction for missing catch-all permission."""
    result = OrchestratorResult(
        config_path="/test.json",
        config={"permission": {"bash": "allow"}},
        issues=[],
        warnings=[],
    )
    score = _calculate_health_score(result)
    assert score <= 95


def test_health_score_bounds() -> None:
    """Test health score stays within 0-100."""
    result = OrchestratorResult(
        config_path="/test.json",
        config={"permission": {}},
        issues=["i"] * 10,
        warnings=["w"] * 10,
    )
    score = _calculate_health_score(result)
    assert 0 <= score <= 100


def test_to_dict_serialization(valid_config_file: Path) -> None:
    """Test result serialization to dict."""
    result = run_orchestration(str(valid_config_file))
    d = result.to_dict()
    assert "config_path" in d
    assert "config" in d
    assert "permissions" in d
    assert "agents" in d
    assert "skills" in d
    assert "mcp_servers" in d
    assert "commands" in d
    assert "summary" in d
    assert "issues" in d
    assert "warnings" in d
