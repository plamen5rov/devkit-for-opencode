"""Tests for the Optimization Advisor Agent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.agents.optimization_advisor import (
    OptimizationResult,
    Recommendation,
    run_optimization,
)


@pytest.fixture
def unoptimized_config_file(tmp_path: Path) -> Path:
    """Create an unoptimized config file."""
    config = {
        "model": "anthropic/claude-opus-4-20250514",
        "permission": {
            "bash": "allow",
            "edit": "allow",
        },
        "mcp": {
            "server-1": {
                "type": "remote",
                "url": "https://server1.example.com/mcp",
            },
            "server-2": {
                "type": "remote",
                "url": "https://server2.example.com/mcp",
            },
            "server-3": {
                "type": "remote",
                "url": "https://server3.example.com/mcp",
            },
            "server-4": {
                "type": "remote",
                "url": "https://server4.example.com/mcp",
            },
            "server-5": {
                "type": "remote",
                "url": "https://server5.example.com/mcp",
            },
            "server-6": {
                "type": "remote",
                "url": "https://server6.example.com/mcp",
            },
            "server-7": {
                "type": "remote",
                "url": "https://server7.example.com/mcp",
            },
            "disabled-server": {
                "type": "remote",
                "url": "https://disabled.example.com/mcp",
                "enabled": False,
            },
        },
        "agent": {
            "planner": {
                "mode": "primary",
                "description": "Planning agent",
                "temperature": 0.8,
            },
            "disabled-agent": {
                "mode": "subagent",
                "description": "Disabled agent",
                "disable": True,
            },
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def optimized_config_file(tmp_path: Path) -> Path:
    """Create an optimized config file."""
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": "anthropic/claude-sonnet-4-20250514",
        "small_model": "anthropic/claude-haiku-4-20250514",
        "share": "manual",
        "permission": {
            "*": "ask",
            "bash": {
                "*": "ask",
                "git *": "allow",
                "npm *": "allow",
            },
            "edit": "allow",
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


def test_optimization_unoptimized_config(unoptimized_config_file: Path) -> None:
    """Test optimizing an unoptimized config."""
    result = run_optimization(str(unoptimized_config_file))
    assert result.config_path == str(unoptimized_config_file)
    assert len(result.recommendations) >= 3
    # Should have high-priority recommendations
    assert any(r.priority <= 2 for r in result.recommendations)


def test_optimization_optimized_config(optimized_config_file: Path) -> None:
    """Test optimizing an already optimized config."""
    result = run_optimization(str(optimized_config_file))
    # Should have fewer recommendations
    assert len(result.recommendations) < 5


def test_optimization_missing_file() -> None:
    """Test optimizing a missing config file."""
    result = run_optimization("/nonexistent/opencode.json")
    assert len(result.recommendations) == 0


def test_bash_permission_recommendation(tmp_path: Path) -> None:
    """Test recommendation for overly permissive bash."""
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps({
        "permission": {"bash": "allow"},
    }))
    result = run_optimization(str(config_file))
    assert any(
        r.category == "permissions" and "Tighten bash" in r.title
        for r in result.recommendations
    )


def test_catchall_recommendation(tmp_path: Path) -> None:
    """Test recommendation for missing catch-all."""
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps({
        "permission": {"bash": "ask"},
    }))
    result = run_optimization(str(config_file))
    assert any(
        r.category == "permissions" and "catch-all" in r.title.lower()
        for r in result.recommendations
    )


def test_model_recommendation(tmp_path: Path) -> None:
    """Test recommendation for missing small_model."""
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps({
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }))
    result = run_optimization(str(config_file))
    assert any(
        r.category == "models" and "small_model" in r.title.lower()
        for r in result.recommendations
    )


def test_opus_model_recommendation(tmp_path: Path) -> None:
    """Test recommendation for opus model without small_model."""
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps({
        "model": "anthropic/claude-opus-4-20250514",
        "permission": {"*": "ask"},
    }))
    result = run_optimization(str(config_file))
    assert any(
        r.category == "models" and "high-cost" in r.title.lower()
        for r in result.recommendations
    )


def test_temperature_recommendation(unoptimized_config_file: Path) -> None:
    """Test recommendation for high temperature on analysis agent."""
    result = run_optimization(str(unoptimized_config_file))
    assert any(
        r.category == "agents" and "temperature" in r.title.lower()
        for r in result.recommendations
    )


def test_disabled_agent_recommendation(unoptimized_config_file: Path) -> None:
    """Test recommendation for disabled agent."""
    result = run_optimization(str(unoptimized_config_file))
    assert any(
        r.category == "agents" and "disabled" in r.title.lower()
        for r in result.recommendations
    )


def test_mcp_token_recommendation(unoptimized_config_file: Path) -> None:
    """Test recommendation for high MCP token cost."""
    result = run_optimization(str(unoptimized_config_file))
    assert any(
        r.category == "mcp" and "token" in r.title.lower()
        for r in result.recommendations
    )


def test_disabled_mcp_recommendation(unoptimized_config_file: Path) -> None:
    """Test recommendation for disabled MCP server."""
    result = run_optimization(str(unoptimized_config_file))
    assert any(
        r.category == "mcp" and "disabled" in r.title.lower()
        for r in result.recommendations
    )


def test_recommendation_to_dict() -> None:
    """Test Recommendation serialization."""
    rec = Recommendation(
        category="test",
        priority=1,
        title="Test recommendation",
        description="Test description",
        current_state="before",
        suggested_state="after",
        estimated_impact="high",
        effort="low",
    )
    d = rec.to_dict()
    assert d["category"] == "test"
    assert d["priority"] == 1
    assert d["title"] == "Test recommendation"
    assert d["effort"] == "low"


def test_optimization_result_to_dict() -> None:
    """Test OptimizationResult serialization."""
    result = OptimizationResult(
        config_path="/test.json",
        recommendations=[
            Recommendation(
                category="test",
                priority=1,
                title="Test",
                description="Test",
                current_state="before",
                suggested_state="after",
                estimated_impact="high",
                effort="low",
            ),
        ],
        total_estimated_savings="Significant",
    )
    d = result.to_dict()
    assert d["config_path"] == "/test.json"
    assert d["total_recommendations"] == 1
    assert d["total_estimated_savings"] == "Significant"


def test_recommendations_sorted_by_priority() -> None:
    """Test that recommendations are sorted by priority."""
    config = {
        "model": "anthropic/claude-opus-4-20250514",
        "permission": {"bash": "allow"},
    }
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config, f)
        path = Path(f.name)
    try:
        result = run_optimization(str(path))
        priorities = [r.priority for r in result.recommendations]
        assert priorities == sorted(priorities)
    finally:
        path.unlink()


def test_optimization_advisor_agent_creation() -> None:
    """Test creating the optimization advisor CrewAI agent."""
    from devkit.agents.optimization_advisor import (
        create_optimization_advisor_agent,
    )
    agent = create_optimization_advisor_agent()
    assert agent.role == "OpenCode Optimization Advisor"


def test_optimization_task_creation(tmp_path: Path) -> None:
    """Test creating the optimization task."""
    from devkit.agents.optimization_advisor import (
        create_optimization_advisor_agent,
        create_optimization_task,
    )
    agent = create_optimization_advisor_agent()
    config_file = tmp_path / "opencode.json"
    config_file.write_text("{}")
    task = create_optimization_task(agent, str(config_file))
    assert task.agent == agent
    assert "optimization" in task.description.lower()
