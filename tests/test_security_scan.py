"""Tests for the Security Scan Task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.tasks.security_scan import (
    SecurityFinding,
    SecurityScanResult,
    SecuritySeverity,
    run_security_scan,
)


@pytest.fixture
def secure_config_file(tmp_path: Path) -> Path:
    """Create a secure config file."""
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
            "edit": {
                "*": "ask",
                "src/**/*.py": "allow",
            },
            "doom_loop": "ask",
            "external_directory": {
                "~/projects/specific/**": "ask",
            },
        },
        "share": "manual",
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def insecure_config_file(tmp_path: Path) -> Path:
    """Create an insecure config file."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {
            "bash": "allow",
            "edit": "allow",
            "doom_loop": "allow",
            "external_directory": {
                "~/**": "allow",
            },
        },
        "mcp": {
            "my-server": {
                "type": "remote",
                "url": "http://insecure.example.com/mcp",
                "environment": {
                    "API_KEY": "sk-real-secret-key-12345",
                },
            },
        },
        "plugin": ["my-plugin@latest"],
        "share": "auto",
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


def test_security_scan_secure_config(secure_config_file: Path) -> None:
    """Test scanning a secure config."""
    result = run_security_scan(str(secure_config_file))
    assert result.config_path == str(secure_config_file)
    assert result.critical_count == 0
    assert result.high_count == 0
    assert result.risk_score >= 80


def test_security_scan_insecure_config(insecure_config_file: Path) -> None:
    """Test scanning an insecure config."""
    result = run_security_scan(str(insecure_config_file))
    assert result.critical_count >= 1
    assert result.high_count >= 1
    assert result.risk_score < 50


def test_security_scan_missing_file() -> None:
    """Test scanning a missing config file."""
    result = run_security_scan("/nonexistent/opencode.json")
    assert len(result.findings) >= 1
    assert any(f.severity == SecuritySeverity.HIGH for f in result.findings)
    assert result.risk_score == 0


def test_hardcoded_secret_detection(insecure_config_file: Path) -> None:
    """Test detection of hardcoded secrets."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.CRITICAL
        and "Hardcoded" in f.title
        for f in result.findings
    )


def test_bash_globally_allowed(insecure_config_file: Path) -> None:
    """Test detection of globally allowed bash."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.HIGH
        and "Bash globally allowed" in f.title
        for f in result.findings
    )


def test_doom_loop_disabled(insecure_config_file: Path) -> None:
    """Test detection of disabled doom_loop."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.MEDIUM
        and "Doom loop" in f.title
        for f in result.findings
    )


def test_insecure_mcp_url(insecure_config_file: Path) -> None:
    """Test detection of insecure MCP URL."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.HIGH
        and "Insecure MCP URL" in f.title
        for f in result.findings
    )


def test_hardcoded_mcp_credential(insecure_config_file: Path) -> None:
    """Test detection of hardcoded MCP credential."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.CRITICAL
        and "Hardcoded credential in MCP" in f.title
        for f in result.findings
    )


def test_broad_external_directory(insecure_config_file: Path) -> None:
    """Test detection of broad external directory access."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.MEDIUM
        and "Broad external directory" in f.title
        for f in result.findings
    )


def test_unpinned_plugin(insecure_config_file: Path) -> None:
    """Test detection of unpinned plugin version."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.LOW
        and "Unpinned plugin" in f.title
        for f in result.findings
    )


def test_auto_share(insecure_config_file: Path) -> None:
    """Test detection of auto-sharing."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.LOW
        and "Auto-sharing" in f.title
        for f in result.findings
    )


def test_env_ref_not_flagged(secure_config_file: Path) -> None:
    """Test that env references are not flagged as secrets."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
        "mcp": {
            "secure-server": {
                "type": "remote",
                "url": "https://secure.example.com/mcp",
                "environment": {
                    "API_KEY": "{env:MY_API_KEY}",
                    "TOKEN": "${MY_TOKEN}",
                    "SECRET": "$MY_SECRET",
                },
            },
        },
    }
    import json as json_module
    config_file = secure_config_file
    config_file.write_text(json_module.dumps(config))
    result = run_security_scan(str(config_file))
    assert not any(
        "Hardcoded" in f.title and "secure-server" in f.location
        for f in result.findings
    )


def test_risk_score_calculation() -> None:
    """Test risk score calculation."""
    from devkit.tasks.security_scan import _calculate_risk_score
    result = SecurityScanResult(config_path="/test.json")
    result.critical_count = 1
    result.high_count = 1
    score = _calculate_risk_score(result)
    assert score == 60  # 100 - 25 - 15


def test_risk_score_bounds() -> None:
    """Test risk score stays within bounds."""
    from devkit.tasks.security_scan import _calculate_risk_score
    result = SecurityScanResult(config_path="/test.json")
    result.critical_count = 10
    result.high_count = 10
    result.medium_count = 10
    result.low_count = 10
    result.info_count = 10
    score = _calculate_risk_score(result)
    assert 0 <= score <= 100


def test_finding_to_dict() -> None:
    """Test SecurityFinding serialization."""
    finding = SecurityFinding(
        severity=SecuritySeverity.HIGH,
        category="bash",
        title="Test finding",
        description="Test description",
        location="permission.bash",
        remediation="Fix it",
        cve_reference="CVE-2024-1234",
    )
    d = finding.to_dict()
    assert d["severity"] == "high"
    assert d["category"] == "bash"
    assert d["title"] == "Test finding"
    assert d["location"] == "permission.bash"
    assert d["remediation"] == "Fix it"
    assert d["cve_reference"] == "CVE-2024-1234"


def test_result_to_dict() -> None:
    """Test SecurityScanResult serialization."""
    result = SecurityScanResult(
        config_path="/test.json",
        findings=[
            SecurityFinding(
                severity=SecuritySeverity.HIGH,
                category="test",
                title="Test",
                description="Test",
            ),
        ],
        critical_count=0,
        high_count=1,
        risk_score=85,
    )
    d = result.to_dict()
    assert d["config_path"] == "/test.json"
    assert d["high_count"] == 1
    assert d["risk_score"] == 85
    assert d["total_findings"] == 1


def test_result_to_markdown(insecure_config_file: Path) -> None:
    """Test Markdown report generation."""
    result = run_security_scan(str(insecure_config_file))
    md = result.to_markdown()
    assert "# Security Scan Report" in md
    assert "Risk Score" in md
    assert "Critical" in md
    assert "## Findings" in md


def test_edit_globally_allowed(insecure_config_file: Path) -> None:
    """Test detection of globally allowed edit."""
    result = run_security_scan(str(insecure_config_file))
    assert any(
        f.severity == SecuritySeverity.MEDIUM
        and "Edit globally allowed" in f.title
        for f in result.findings
    )


def test_agent_permission_weakening() -> None:
    """Test detection of agent permission weakening."""
    import json as json_module
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config = {
            "permission": {"edit": "deny"},
            "agent": {
                "relaxed": {
                    "permission": {"edit": "allow"},
                },
            },
        }
        json_module.dump(config, f)
        path = Path(f.name)
    try:
        result = run_security_scan(str(path))
        assert any(
            f.severity == SecuritySeverity.MEDIUM
            and "weaker edit" in f.title.lower()
            for f in result.findings
        )
    finally:
        path.unlink()
