"""MCP Server Analyzer Tool — Analyzes OpenCode MCP server configurations.

Enumerates local and remote MCP servers.
Checks OAuth status, enabled/disabled state.
Reports tool count and estimated token cost per server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# Estimated token costs for common MCP server types
# Based on typical tool description sizes
MCP_TOKEN_ESTIMATES = {
    "sentry": 800,
    "context7": 400,
    "github": 2500,
    "linear": 600,
    "slack": 500,
    "jira": 1200,
    "vercel": 700,
    "cloudflare": 500,
    "stripe": 900,
    "default-local": 300,
    "default-remote": 500,
}


@dataclass
class MCPServerInfo:
    """Parsed MCP server information."""

    name: str
    server_type: str = "local"  # "local" or "remote"
    enabled: bool = True
    url: Optional[str] = None
    command: Optional[list[str]] = None
    environment: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    oauth_enabled: bool = False
    oauth_config: Optional[dict[str, Any]] = None
    timeout: int = 5000
    estimated_tokens: int = 0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MCPAnalysisResult:
    """Result of MCP analysis."""

    servers: dict[str, MCPServerInfo] = field(default_factory=dict)
    total_estimated_tokens: int = 0
    enabled_count: int = 0
    disabled_count: int = 0
    oauth_count: int = 0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "servers": {
                name: {
                    "name": s.name,
                    "type": s.server_type,
                    "enabled": s.enabled,
                    "url": s.url,
                    "command": s.command,
                    "oauth_enabled": s.oauth_enabled,
                    "estimated_tokens": s.estimated_tokens,
                    "issues": s.issues,
                    "warnings": s.warnings,
                }
                for name, s in self.servers.items()
            },
            "total_estimated_tokens": self.total_estimated_tokens,
            "enabled_count": self.enabled_count,
            "disabled_count": self.disabled_count,
            "oauth_count": self.oauth_count,
            "issues": self.issues,
            "warnings": self.warnings,
        }


def analyze_mcp_servers(config: dict[str, Any]) -> MCPAnalysisResult:
    """Analyze all MCP server configurations.

    Args:
        config: Parsed OpenCode configuration.

    Returns:
        MCPAnalysisResult with parsed servers and analysis.
    """
    result = MCPAnalysisResult()

    raw_mcp = config.get("mcp", {})
    if not isinstance(raw_mcp, dict):
        result.issues.append("MCP config is not a dictionary")
        return result

    for name, server_config in raw_mcp.items():
        if not isinstance(server_config, dict):
            result.issues.append(f"MCP server '{name}' config is not a dictionary")
            continue

        info = _parse_mcp_server(name, server_config)
        result.servers[name] = info

        if info.enabled:
            result.enabled_count += 1
            result.total_estimated_tokens += info.estimated_tokens
        else:
            result.disabled_count += 1

        if info.oauth_enabled:
            result.oauth_count += 1

        result.issues.extend(info.issues)
        result.warnings.extend(info.warnings)

    # Cross-server checks
    _cross_server_checks(result)

    return result


def _parse_mcp_server(name: str, config: dict[str, Any]) -> MCPServerInfo:
    """Parse a single MCP server definition."""
    info = MCPServerInfo(name=name)

    info.server_type = config.get("type", "local")
    info.enabled = config.get("enabled", True)
    info.url = config.get("url")
    info.command = config.get("command")
    info.environment = config.get("environment", {}) or {}
    info.headers = config.get("headers", {}) or {}
    info.timeout = config.get("timeout", 5000)

    # OAuth detection
    oauth_config = config.get("oauth")
    if oauth_config is not None:
        info.oauth_enabled = True
        info.oauth_config = oauth_config if isinstance(oauth_config, dict) else None
        if oauth_config is False:
            info.oauth_enabled = False
            info.warnings.append("OAuth explicitly disabled")

    # Estimate tokens
    info.estimated_tokens = _estimate_tokens(name, info)

    # Validate
    _validate_mcp_server(info)

    return info


def _estimate_tokens(name: str, info: MCPServerInfo) -> int:
    """Estimate token cost for an MCP server."""
    # Check known server types
    name_lower = name.lower()
    for key, tokens in MCP_TOKEN_ESTIMATES.items():
        if key in name_lower:
            return tokens

    # Default estimates based on type
    if info.server_type == "local":
        return MCP_TOKEN_ESTIMATES["default-local"]
    return MCP_TOKEN_ESTIMATES["default-remote"]


def _validate_mcp_server(info: MCPServerInfo) -> None:
    """Validate an MCP server definition."""
    # Local servers need command
    if info.server_type == "local" and not info.command:
        info.issues.append("Local MCP server missing 'command' field")

    # Remote servers need URL
    if info.server_type == "remote" and not info.url:
        info.issues.append("Remote MCP server missing 'url' field")

    # Validate URL format
    if info.url and not info.url.startswith(("http://", "https://")):
        info.warnings.append(f"URL '{info.url}' may be missing http/https prefix")

    # High token cost warning
    if info.estimated_tokens > 1000:
        info.warnings.append(
            f"High estimated token cost: ~{info.estimated_tokens} tokens"
        )

    # Timeout warning
    if info.timeout < 1000:
        info.warnings.append(f"Low timeout ({info.timeout}ms) may cause failures")
    elif info.timeout > 30000:
        info.warnings.append(f"High timeout ({info.timeout}ms) may delay startup")


def _cross_server_checks(result: MCPAnalysisResult) -> None:
    """Cross-server validation checks."""
    # Check for duplicate commands
    commands = {}
    for name, server in result.servers.items():
        if server.command:
            cmd_key = " ".join(server.command)
            if cmd_key in commands:
                result.warnings.append(
                    f"Servers '{name}' and '{commands[cmd_key]}' use the same command"
                )
            else:
                commands[cmd_key] = name

    # Check total token cost
    if result.total_estimated_tokens > 5000:
        result.warnings.append(
            f"Total estimated MCP token cost ({result.total_estimated_tokens}) "
            "is high — consider disabling unused servers"
        )

    # Check for disabled servers that may be referenced
    disabled_servers = [
        name for name, s in result.servers.items() if not s.enabled
    ]
    if disabled_servers:
        result.warnings.append(
            f"Disabled servers: {', '.join(disabled_servers)} — remove if not needed"
        )

    # Check for environment variables with hardcoded secrets
    for name, server in result.servers.items():
        for key, value in server.environment.items():
            if any(secret in key.lower() for secret in ["key", "token", "secret", "password"]):
                if value and not value.startswith("{env:"):
                    result.issues.append(
                        f"Possible hardcoded secret in '{name}' environment: {key}"
                    )
