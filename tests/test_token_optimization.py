"""Tests for the Token Optimization Task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.tasks.token_optimization import (
    TokenRecommendation,
    TokenUsageReport,
    run_token_analysis,
)


@pytest.fixture
def heavy_config_file(tmp_path: Path) -> Path:
    """Create a config with high token usage."""
    config = {
        "model": "anthropic/claude-opus-4-20250514",
        "permission": {"*": "ask"},
        "mcp": {
            "github": {
                "type": "remote",
                "url": "https://github.example.com/mcp",
            },
            "jira": {
                "type": "remote",
                "url": "https://jira.example.com/mcp",
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
                "description": "Planning agent for complex tasks",
                "model": "anthropic/claude-opus-4-20250514",
                "permission": {"edit": "deny", "bash": "deny"},
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
def light_config_file(tmp_path: Path) -> Path:
    """Create a lightweight config."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


def test_token_analysis_heavy_config(heavy_config_file: Path) -> None:
    """Test token analysis with a heavy config."""
    report = run_token_analysis(str(heavy_config_file))
    assert report.config_path == str(heavy_config_file)
    assert report.total_estimated_tokens > 0
    assert report.mcp_tokens > 0
    assert len(report.recommendations) >= 1


def test_token_analysis_light_config(light_config_file: Path) -> None:
    """Test token analysis with a light config."""
    report = run_token_analysis(str(light_config_file))
    assert report.config_path == str(light_config_file)
    assert report.total_estimated_tokens >= 0
    assert report.mcp_tokens == 0


def test_token_analysis_missing_file() -> None:
    """Test token analysis with missing config."""
    report = run_token_analysis("/nonexistent/opencode.json")
    assert report.total_estimated_tokens == 0
    assert len(report.recommendations) == 0


def test_mcp_high_cost_recommendation(heavy_config_file: Path) -> None:
    """Test recommendation for high-cost MCP servers."""
    report = run_token_analysis(str(heavy_config_file))
    assert any(
        r.category == "mcp" and "high-cost" in r.title.lower()
        for r in report.recommendations
    )


def test_disabled_mcp_recommendation(heavy_config_file: Path) -> None:
    """Test recommendation for disabled MCP servers."""
    report = run_token_analysis(str(heavy_config_file))
    assert any(
        r.category == "mcp" and "disabled" in r.title.lower()
        for r in report.recommendations
    )


def test_agent_model_downgrade_recommendation(heavy_config_file: Path) -> None:
    """Test recommendation for agent model downgrade."""
    report = run_token_analysis(str(heavy_config_file))
    assert any(
        r.category == "agent" and "downgrade" in r.title.lower()
        for r in report.recommendations
    )


def test_disabled_agent_recommendation(heavy_config_file: Path) -> None:
    """Test recommendation for disabled agent removal."""
    report = run_token_analysis(str(heavy_config_file))
    assert any(
        r.category == "agent" and "disabled" in r.title.lower()
        for r in report.recommendations
    )


def test_report_to_dict(heavy_config_file: Path) -> None:
    """Test report serialization to dict."""
    report = run_token_analysis(str(heavy_config_file))
    d = report.to_dict()
    assert "config_path" in d
    assert "total_estimated_tokens" in d
    assert "mcp_tokens" in d
    assert "agent_tokens" in d
    assert "skill_tokens" in d
    assert "command_tokens" in d
    assert "recommendations" in d
    assert "breakdown" in d


def test_report_to_markdown(heavy_config_file: Path) -> None:
    """Test Markdown report generation."""
    report = run_token_analysis(str(heavy_config_file))
    md = report.to_markdown()
    assert "# Token Usage Report" in md
    assert "Total Estimated Tokens" in md
    assert "## Breakdown" in md
    assert "MCP Servers" in md


def test_report_to_markdown_with_recommendations(heavy_config_file: Path) -> None:
    """Test Markdown report with recommendations."""
    report = run_token_analysis(str(heavy_config_file))
    md = report.to_markdown()
    assert "## Recommendations" in md
    assert "Potential Savings" in md


def test_token_recommendation_to_dict() -> None:
    """Test TokenRecommendation serialization."""
    rec = TokenRecommendation(
        category="mcp",
        title="Test recommendation",
        description="Test description",
        current_tokens=500,
        estimated_savings=500,
        effort="low",
        action="Disable server",
    )
    d = rec.to_dict()
    assert d["category"] == "mcp"
    assert d["title"] == "Test recommendation"
    assert d["current_tokens"] == 500
    assert d["estimated_savings"] == 500
    assert d["effort"] == "low"
    assert d["action"] == "Disable server"


def test_report_breakdown(heavy_config_file: Path) -> None:
    """Test report breakdown includes all categories."""
    report = run_token_analysis(str(heavy_config_file))
    breakdown = report.breakdown
    assert "mcp_servers" in breakdown
    assert "agents" in breakdown
    assert "skills" in breakdown
    assert "commands" in breakdown


def test_recommendations_sorted_by_savings(heavy_config_file: Path) -> None:
    """Test recommendations are sorted by savings."""
    report = run_token_analysis(str(heavy_config_file))
    savings = [r.estimated_savings for r in report.recommendations]
    assert savings == sorted(savings, reverse=True)


def test_total_tokens_calculation(heavy_config_file: Path) -> None:
    """Test total tokens is sum of all categories."""
    report = run_token_analysis(str(heavy_config_file))
    expected = (
        report.mcp_tokens
        + report.agent_tokens
        + report.skill_tokens
        + report.command_tokens
    )
    assert report.total_estimated_tokens == expected
