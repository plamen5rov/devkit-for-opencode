"""Tests for the Agent Config Analyzer Tool."""

from __future__ import annotations

import pytest

from devkit.tools.agent_analyzer import analyze_agents, AgentAnalysisResult


@pytest.fixture
def basic_agents_config() -> dict:
    """Config with basic agent definitions."""
    return {
        "agent": {
            "build": {
                "mode": "primary",
                "model": "anthropic/claude-sonnet-4-20250514",
                "description": "Build agent for coding",
                "temperature": 0.3,
            },
            "plan": {
                "mode": "primary",
                "model": "anthropic/claude-haiku-4-20250514",
                "description": "Plan agent for analysis",
                "permission": {
                    "edit": "deny",
                    "bash": "deny",
                },
            },
            "code-reviewer": {
                "mode": "subagent",
                "model": "anthropic/claude-sonnet-4-20250514",
                "description": "Reviews code for quality",
                "permission": {
                    "edit": "deny",
                    "task": {
                        "*": "deny",
                        "explorer": "allow",
                    },
                },
            },
        },
    }


@pytest.fixture
def invalid_config() -> dict:
    """Config with invalid agent definitions."""
    return {
        "agent": {
            "bad-mode": {
                "mode": "invalid_mode",
                "description": "Agent with invalid mode",
            },
            "bad-temp": {
                "mode": "subagent",
                "description": "Agent with bad temperature",
                "temperature": 2.5,
            },
            "no-desc": {
                "mode": "primary",
            },
            "bad-model": {
                "mode": "subagent",
                "description": "Agent with bad model format",
                "model": "claude-sonnet-4",
            },
        },
    }


def test_analyze_basic_agents(basic_agents_config: dict) -> None:
    """Test analyzing basic agent definitions."""
    result = analyze_agents(basic_agents_config)
    assert len(result.agents) == 3
    assert result.agents["build"].mode == "primary"
    assert result.agents["build"].model == "anthropic/claude-sonnet-4-20250514"
    assert result.agents["build"].temperature == 0.3
    assert result.agents["plan"].permission["edit"] == "deny"


def test_builtin_agent_detection(basic_agents_config: dict) -> None:
    """Test builtin agent detection."""
    result = analyze_agents(basic_agents_config)
    assert result.agents["build"].is_builtin is True
    assert result.agents["plan"].is_builtin is True
    assert result.agents["code-reviewer"].is_builtin is False


def test_task_permissions(basic_agents_config: dict) -> None:
    """Test task permission extraction."""
    result = analyze_agents(basic_agents_config)
    assert "explorer" in result.agents["code-reviewer"].task_permissions
    assert result.agents["code-reviewer"].task_permissions["*"] == "deny"


def test_dependency_graph(basic_agents_config: dict) -> None:
    """Test dependency graph building."""
    result = analyze_agents(basic_agents_config)
    # code-reviewer has task permissions that should create dependencies
    deps = [d for d in result.dependencies if d.from_agent == "code-reviewer"]
    assert len(deps) > 0


def test_invalid_mode(invalid_config: dict) -> None:
    """Test detection of invalid mode."""
    result = analyze_agents(invalid_config)
    assert any("Invalid mode" in i for i in result.issues)


def test_bad_temperature(invalid_config: dict) -> None:
    """Test warning for bad temperature."""
    result = analyze_agents(invalid_config)
    assert any("Temperature" in w for w in result.warnings)


def test_missing_description(invalid_config: dict) -> None:
    """Test warning for missing description."""
    result = analyze_agents(invalid_config)
    assert any("No description" in w for w in result.warnings)


def test_bad_model_format(invalid_config: dict) -> None:
    """Test warning for missing provider prefix in model."""
    result = analyze_agents(invalid_config)
    assert any("provider prefix" in w for w in result.warnings)


def test_deprecated_tools_warning() -> None:
    """Test warning for deprecated tools field."""
    config = {
        "agent": {
            "legacy": {
                "mode": "subagent",
                "description": "Uses deprecated tools",
                "tools": {"bash": True, "edit": True},
            },
        },
    }
    result = analyze_agents(config)
    assert any("deprecated" in w.lower() for w in result.warnings)


def test_disabled_subagent_warning() -> None:
    """Test warning for disabled subagent."""
    config = {
        "agent": {
            "disabled-sub": {
                "mode": "subagent",
                "description": "Disabled subagent",
                "disable": True,
            },
        },
    }
    result = analyze_agents(config)
    assert any("Disabled subagent" in w for w in result.warnings)


def test_circular_dependency_warning() -> None:
    """Test warning for circular dependencies."""
    config = {
        "agent": {
            "agent-a": {
                "mode": "primary",
                "description": "Agent A",
                "permission": {"task": {"agent-b": "allow"}},
            },
            "agent-b": {
                "mode": "primary",
                "description": "Agent B",
                "permission": {"task": {"agent-a": "allow"}},
            },
        },
    }
    result = analyze_agents(config)
    assert any("circular" in w.lower() for w in result.warnings)


def test_empty_config() -> None:
    """Test analyzing empty config."""
    result = analyze_agents({})
    assert len(result.agents) == 0
    assert result.issues == []


def test_non_dict_agent_config() -> None:
    """Test non-dict agent config."""
    config = {"agent": "not-a-dict"}
    result = analyze_agents(config)
    assert any("not a dictionary" in i.lower() for i in result.issues)


def test_to_dict_serialization(basic_agents_config: dict) -> None:
    """Test result serialization to dict."""
    result = analyze_agents(basic_agents_config)
    d = result.to_dict()
    assert "agents" in d
    assert "dependencies" in d
    assert "total_agents" in d
    assert "total_dependencies" in d
    assert d["total_agents"] == 3


def test_negative_steps() -> None:
    """Test issue for negative steps."""
    config = {
        "agent": {
            "limited": {
                "mode": "primary",
                "description": "Limited agent",
                "steps": -5,
            },
        },
    }
    result = analyze_agents(config)
    assert any("Steps must be positive" in i for i in result.issues)


def test_override_builtin_warning() -> None:
    """Test warning for overriding builtin agent."""
    config = {
        "agent": {
            "build": {
                "mode": "primary",
                "description": "Custom build override",
                "model": "openai/gpt-4",
            },
        },
    }
    result = analyze_agents(config)
    assert any("overrides built-in" in w for w in result.warnings)
