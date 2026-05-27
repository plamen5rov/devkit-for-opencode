"""Tests for the MCP Server Analyzer Tool."""

from __future__ import annotations

import pytest

from devkit.tools.mcp_analyzer import analyze_mcp_servers


@pytest.fixture
def local_mcp_config() -> dict:
    """Config with local MCP server."""
    return {
        "mcp": {
            "my-local-server": {
                "type": "local",
                "command": ["npx", "-y", "my-mcp-server"],
                "enabled": True,
                "environment": {"MY_VAR": "value"},
            },
        },
    }


@pytest.fixture
def remote_mcp_config() -> dict:
    """Config with remote MCP server."""
    return {
        "mcp": {
            "sentry": {
                "type": "remote",
                "url": "https://mcp.sentry.dev/mcp",
                "oauth": {},
                "enabled": True,
            },
        },
    }


@pytest.fixture
def mixed_mcp_config() -> dict:
    """Config with multiple MCP servers."""
    return {
        "mcp": {
            "local-server": {
                "type": "local",
                "command": ["npx", "local-mcp"],
                "enabled": True,
            },
            "remote-server": {
                "type": "remote",
                "url": "https://api.example.com/mcp",
                "enabled": True,
                "headers": {"Authorization": "Bearer token"},
            },
            "disabled-server": {
                "type": "remote",
                "url": "https://disabled.example.com/mcp",
                "enabled": False,
            },
        },
    }


def test_analyze_local_mcp(local_mcp_config: dict) -> None:
    """Test analyzing a local MCP server."""
    result = analyze_mcp_servers(local_mcp_config)
    assert len(result.servers) == 1
    server = result.servers["my-local-server"]
    assert server.server_type == "local"
    assert server.command == ["npx", "-y", "my-mcp-server"]
    assert server.enabled is True
    assert server.environment == {"MY_VAR": "value"}


def test_analyze_remote_mcp(remote_mcp_config: dict) -> None:
    """Test analyzing a remote MCP server."""
    result = analyze_mcp_servers(remote_mcp_config)
    assert len(result.servers) == 1
    server = result.servers["sentry"]
    assert server.server_type == "remote"
    assert server.url == "https://mcp.sentry.dev/mcp"
    assert server.oauth_enabled is True
    assert result.oauth_count == 1


def test_analyze_mixed_mcp(mixed_mcp_config: dict) -> None:
    """Test analyzing multiple MCP servers."""
    result = analyze_mcp_servers(mixed_mcp_config)
    assert len(result.servers) == 3
    assert result.enabled_count == 2
    assert result.disabled_count == 1


def test_missing_command_local() -> None:
    """Test issue for local server missing command."""
    config = {
        "mcp": {
            "bad-local": {
                "type": "local",
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("missing 'command'" in i for i in result.issues)


def test_missing_url_remote() -> None:
    """Test issue for remote server missing URL."""
    config = {
        "mcp": {
            "bad-remote": {
                "type": "remote",
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("missing 'url'" in i for i in result.issues)


def test_oauth_disabled_warning() -> None:
    """Test warning for explicitly disabled OAuth."""
    config = {
        "mcp": {
            "no-oauth": {
                "type": "remote",
                "url": "https://api.example.com/mcp",
                "oauth": False,
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("OAuth explicitly disabled" in w for w in result.warnings)


def test_high_token_warning() -> None:
    """Test warning for high token cost."""
    config = {
        "mcp": {
            "github-mcp": {
                "type": "remote",
                "url": "https://github.example.com/mcp",
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("High estimated token" in w for w in result.warnings)


def test_hardcoded_secret_detection() -> None:
    """Test detection of hardcoded secrets in environment."""
    config = {
        "mcp": {
            "my-server": {
                "type": "local",
                "command": ["npx", "server"],
                "environment": {
                    "API_KEY": "sk-12345-hardcoded",
                    "SAFE_VAR": "{env:MY_VAR}",
                },
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("hardcoded secret" in i.lower() for i in result.issues)


def test_duplicate_command_warning() -> None:
    """Test warning for duplicate commands."""
    config = {
        "mcp": {
            "server-a": {
                "type": "local",
                "command": ["npx", "same-server"],
            },
            "server-b": {
                "type": "local",
                "command": ["npx", "same-server"],
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("same command" in w.lower() for w in result.warnings)


def test_high_total_token_warning() -> None:
    """Test warning for high total token cost."""
    config = {
        "mcp": {
            f"server-{i}": {
                "type": "remote",
                "url": f"https://server-{i}.example.com/mcp",
            }
            for i in range(15)  # 15 * 500 = 7500 tokens
        },
    }
    result = analyze_mcp_servers(config)
    assert any("high" in w.lower() for w in result.warnings)


def test_disabled_servers_warning(mixed_mcp_config: dict) -> None:
    """Test warning for disabled servers."""
    result = analyze_mcp_servers(mixed_mcp_config)
    assert any("Disabled servers" in w for w in result.warnings)


def test_empty_config() -> None:
    """Test analyzing empty config."""
    result = analyze_mcp_servers({})
    assert len(result.servers) == 0
    assert result.total_estimated_tokens == 0


def test_non_dict_mcp_config() -> None:
    """Test non-dict MCP config."""
    config = {"mcp": "not-a-dict"}
    result = analyze_mcp_servers(config)
    assert any("not a dictionary" in i.lower() for i in result.issues)


def test_to_dict_serialization(mixed_mcp_config: dict) -> None:
    """Test result serialization to dict."""
    result = analyze_mcp_servers(mixed_mcp_config)
    d = result.to_dict()
    assert "servers" in d
    assert "total_estimated_tokens" in d
    assert "enabled_count" in d
    assert "disabled_count" in d
    assert "oauth_count" in d
    assert d["enabled_count"] == 2
    assert d["disabled_count"] == 1


def test_url_format_warning() -> None:
    """Test warning for URL without http/https prefix."""
    config = {
        "mcp": {
            "bad-url": {
                "type": "remote",
                "url": "api.example.com/mcp",
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("http/https prefix" in w for w in result.warnings)


def test_timeout_warnings() -> None:
    """Test timeout warnings."""
    config = {
        "mcp": {
            "low-timeout": {
                "type": "local",
                "command": ["npx", "server"],
                "timeout": 500,
            },
            "high-timeout": {
                "type": "local",
                "command": ["npx", "server2"],
                "timeout": 60000,
            },
        },
    }
    result = analyze_mcp_servers(config)
    assert any("Low timeout" in w for w in result.warnings)
    assert any("High timeout" in w for w in result.warnings)
