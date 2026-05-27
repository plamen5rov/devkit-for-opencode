"""Tests for the Config Audit Agent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.agents.config_auditor import (
    AuditFinding,
    AuditResult,
    Severity,
    run_audit,
    _check_secrets,
)


@pytest.fixture
def secure_config_file(tmp_path: Path) -> Path:
    """Create a secure config file."""
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
            "doom_loop": "ask",
            "external_directory": {
                "~/projects/**": "ask",
            },
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def insecure_config_file(tmp_path: Path) -> Path:
    """Create an insecure config file with issues."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {
            "bash": "allow",
            "edit": "allow",
        },
        "mcp": {
            "my-server": {
                "type": "local",
                "command": ["npx", "server"],
                "environment": {
                    "API_KEY": "sk-12345-hardcoded",
                },
            },
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


def test_audit_secure_config(secure_config_file: Path) -> None:
    """Test auditing a secure config."""
    result = run_audit(str(secure_config_file))
    assert result.config_path == str(secure_config_file)
    assert result.error_count == 0
    # May have info-level findings for best practices
    assert all(f.severity != Severity.ERROR for f in result.findings)


def test_audit_insecure_config(insecure_config_file: Path) -> None:
    """Test auditing an insecure config."""
    result = run_audit(str(insecure_config_file))
    assert result.error_count > 0
    assert any(
        f.severity == Severity.ERROR and "hardcoded secret" in f.message.lower()
        for f in result.findings
    )


def test_audit_missing_file() -> None:
    """Test auditing a missing config file."""
    result = run_audit("/nonexistent/opencode.json")
    assert result.error_count > 0
    assert any(
        f.severity == Severity.ERROR and "not found" in f.message.lower()
        for f in result.findings
    )


def test_check_secrets_direct() -> None:
    """Test direct secret detection."""
    result = AuditResult(config_path="/test.json")
    config = {
        "api_key": "sk-12345",
        "safe_var": "{env:MY_VAR}",
        "nested": {
            "secret": "my-secret-value",
        },
    }
    _check_secrets(config, "", result)
    assert any("api_key" in f.message for f in result.findings)
    assert any("secret" in f.message for f in result.findings)


def test_check_secrets_env_ref() -> None:
    """Test that env references are not flagged."""
    result = AuditResult(config_path="/test.json")
    config = {
        "api_key": "{env:MY_API_KEY}",
        "token": "${MY_TOKEN}",
        "password": "$PASSWORD",
    }
    _check_secrets(config, "", result)
    assert len(result.findings) == 0


def test_check_secrets_empty_value() -> None:
    """Test that empty values are not flagged."""
    result = AuditResult(config_path="/test.json")
    config = {
        "api_key": "",
        "secret": None,
    }
    _check_secrets(config, "", result)
    assert len(result.findings) == 0


def test_check_secrets_in_list() -> None:
    """Test secret detection in lists."""
    result = AuditResult(config_path="/test.json")
    config = {
        "keys": [
            {"api_key": "sk-secret"},
            {"safe": "{env:KEY}"},
        ],
    }
    _check_secrets(config, "", result)
    assert any("api_key" in f.message for f in result.findings)


def test_audit_finding_to_dict() -> None:
    """Test AuditFinding serialization."""
    finding = AuditFinding(
        severity=Severity.ERROR,
        category="security",
        message="Hardcoded secret",
        path="mcp.server.environment.API_KEY",
        suggestion="Use {env:API_KEY}",
    )
    d = finding.to_dict()
    assert d["severity"] == "error"
    assert d["category"] == "security"
    assert d["message"] == "Hardcoded secret"
    assert d["path"] == "mcp.server.environment.API_KEY"
    assert d["suggestion"] == "Use {env:API_KEY}"


def test_audit_result_to_dict() -> None:
    """Test AuditResult serialization."""
    result = AuditResult(
        config_path="/test.json",
        findings=[
            AuditFinding(
                severity=Severity.ERROR,
                category="test",
                message="Test error",
            ),
        ],
        error_count=1,
        warning_count=0,
        info_count=0,
    )
    d = result.to_dict()
    assert d["config_path"] == "/test.json"
    assert d["error_count"] == 1
    assert d["total_findings"] == 1
    assert len(d["findings"]) == 1


def test_audit_best_practices_missing_model(tmp_path: Path) -> None:
    """Test warning for missing model."""
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps({"permission": {"*": "ask"}}))
    result = run_audit(str(config_file))
    assert any(
        f.severity == Severity.WARNING and "model" in f.message.lower()
        for f in result.findings
    )


def test_audit_best_practices_missing_schema(tmp_path: Path) -> None:
    """Test info for missing schema reference."""
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps({
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }))
    result = run_audit(str(config_file))
    assert any(
        f.severity == Severity.INFO and "schema" in f.message.lower()
        for f in result.findings
    )


def test_audit_best_practices_missing_share(tmp_path: Path) -> None:
    """Test info for missing share configuration."""
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps({
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }))
    result = run_audit(str(config_file))
    assert any(
        f.severity == Severity.INFO and "share" in f.message.lower()
        for f in result.findings
    )


def test_config_auditor_agent_creation() -> None:
    """Test creating the config auditor CrewAI agent."""
    from devkit.agents.config_auditor import create_config_auditor_agent
    agent = create_config_auditor_agent()
    assert agent.role == "OpenCode Configuration Auditor"


def test_audit_task_creation(tmp_path: Path) -> None:
    """Test creating the audit task."""
    from devkit.agents.config_auditor import (
        create_config_auditor_agent,
        create_audit_task,
    )
    agent = create_config_auditor_agent()
    config_file = tmp_path / "opencode.json"
    config_file.write_text("{}")
    task = create_audit_task(agent, str(config_file))
    assert task.agent == agent
    assert "Audit" in task.description
