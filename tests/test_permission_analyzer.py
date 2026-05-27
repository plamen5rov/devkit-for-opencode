"""Tests for the Permission Analyzer Tool."""

from __future__ import annotations

import pytest

from devkit.tools.permission_analyzer import (
    analyze_permissions,
    get_effective_permission,
    PermissionAnalysisResult,
)


@pytest.fixture
def permissive_config() -> dict:
    """Config with permissive permissions."""
    return {
        "permission": {
            "*": "ask",
            "bash": "allow",
            "edit": "allow",
            "read": "allow",
        },
    }


@pytest.fixture
def granular_config() -> dict:
    """Config with granular bash permissions."""
    return {
        "permission": {
            "*": "ask",
            "bash": {
                "*": "ask",
                "git *": "allow",
                "npm *": "allow",
                "rm *": "deny",
                "grep *": "allow",
            },
            "edit": {
                "*": "deny",
                "src/**/*.py": "allow",
            },
        },
    }


@pytest.fixture
def agent_override_config() -> dict:
    """Config with agent permission overrides."""
    return {
        "permission": {
            "*": "ask",
            "edit": "allow",
            "bash": "allow",
        },
        "agent": {
            "plan": {
                "permission": {
                    "edit": "deny",
                    "bash": "deny",
                },
            },
            "build": {
                "permission": {
                    "edit": "allow",
                    "bash": {
                        "*": "ask",
                        "git *": "allow",
                    },
                },
            },
        },
    }


def test_analyze_permissive_config(permissive_config: dict) -> None:
    """Test analyzing a permissive config."""
    result = analyze_permissions(permissive_config)
    assert result.effective_matrix["bash"].action == "allow"
    assert result.effective_matrix["edit"].action == "allow"
    assert result.effective_matrix["read"].action == "allow"


def test_analyze_granular_config(granular_config: dict) -> None:
    """Test analyzing granular permissions."""
    result = analyze_permissions(granular_config)
    assert result.effective_matrix["bash"].action == "ask"  # Granular default
    assert result.effective_matrix["edit"].action == "deny"  # Granular default
    assert len(result.all_entries) > 5  # Multiple granular entries


def test_agent_overrides(agent_override_config: dict) -> None:
    """Test agent permission overrides are captured."""
    result = analyze_permissions(agent_override_config)
    assert "plan" in result.agent_permissions
    assert "build" in result.agent_permissions
    assert result.agent_permissions["plan"]["edit"] == "deny"


def test_dangerous_bash_command_warning() -> None:
    """Test warning for dangerous bash commands allowed."""
    config = {
        "permission": {
            "bash": {
                "*": "ask",
                "rm *": "allow",
            },
        },
    }
    result = analyze_permissions(config)
    assert any("Dangerous bash command" in i for i in result.issues)


def test_doom_loop_warning() -> None:
    """Test warning for missing doom_loop protection."""
    config = {"permission": {"bash": "allow"}}
    result = analyze_permissions(config)
    assert any("doom_loop" in w for w in result.warnings)


def test_external_directory_warning() -> None:
    """Test warning for missing external_directory rules."""
    config = {"permission": {"bash": "allow"}}
    result = analyze_permissions(config)
    assert any("external_directory" in w for w in result.warnings)


def test_agent_weaker_override_warning() -> None:
    """Test warning when agent has weaker restrictions than global."""
    config = {
        "permission": {"edit": "deny"},
        "agent": {
            "relaxed": {
                "permission": {"edit": "allow"},
            },
        },
    }
    result = analyze_permissions(config)
    assert any("weaker edit restrictions" in w for w in result.warnings)


def test_get_effective_permission() -> None:
    """Test getting effective permission for specific tool."""
    config = {
        "permission": {
            "bash": {
                "*": "ask",
                "git *": "allow",
            },
        },
    }
    result = analyze_permissions(config)
    eff = get_effective_permission(result, "bash")
    assert eff.tool == "bash"
    assert eff.source.startswith("global")


def test_shorthand_permission() -> None:
    """Test shorthand permission syntax."""
    config = {"permission": "allow"}
    result = analyze_permissions(config)
    assert result.global_permissions == {"*": "allow"}


def test_deny_warning() -> None:
    """Test warning when a tool is denied."""
    config = {
        "permission": {
            "edit": "deny",
        },
    }
    result = analyze_permissions(config)
    assert any("denied" in w.lower() for w in result.warnings)


def test_empty_config() -> None:
    """Test analyzing empty config."""
    result = analyze_permissions({})
    assert result.effective_matrix["bash"].action == "allow"  # Default
    assert result.global_permissions == {}


def test_to_dict_serialization(permissive_config: dict) -> None:
    """Test result serialization to dict."""
    result = analyze_permissions(permissive_config)
    d = result.to_dict()
    assert "global_permissions" in d
    assert "agent_permissions" in d
    assert "effective_matrix" in d
    assert "total_rules" in d
    assert isinstance(d["total_rules"], int)
