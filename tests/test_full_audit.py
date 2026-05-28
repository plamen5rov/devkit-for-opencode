"""Tests for the Full Config Audit Task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.tasks.full_audit import (
    FullAuditReport,
    create_full_audit_task,
    save_report,
)


@pytest.fixture
def valid_config_file(tmp_path: Path) -> Path:
    """Create a valid config file."""
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
            },
            "edit": "allow",
        },
        "agent": {
            "build": {
                "mode": "primary",
                "description": "Build agent",
            },
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def complex_config_file(tmp_path: Path) -> Path:
    """Create a complex config with MCPs, skills, commands."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {
            "*": "ask",
            "bash": "allow",
            "edit": "allow",
        },
        "mcp": {
            "sentry": {
                "type": "remote",
                "url": "https://mcp.sentry.dev/mcp",
                "oauth": {},
            },
        },
        "agent": {
            "build": {
                "mode": "primary",
                "description": "Build",
            },
            "plan": {
                "mode": "primary",
                "description": "Plan",
                "permission": {"edit": "deny", "bash": "deny"},
            },
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


def test_create_full_audit_valid(valid_config_file: Path) -> None:
    """Test creating a full audit with valid config."""
    report = create_full_audit_task(str(valid_config_file))
    assert report.config_path == str(valid_config_file)
    assert report.timestamp is not None
    assert report.orchestrator is not None
    assert report.audit is not None
    assert report.optimization is not None
    assert report.raw_analyses is not None


def test_create_full_audit_complex(complex_config_file: Path) -> None:
    """Test creating a full audit with complex config."""
    report = create_full_audit_task(str(complex_config_file))
    assert report.config_path == str(complex_config_file)
    assert report.orchestrator["summary"]["agent_count"] >= 2
    assert report.raw_analyses["mcp_servers"]["enabled_count"] >= 1


def test_create_full_audit_missing_file() -> None:
    """Test creating audit with missing config."""
    report = create_full_audit_task("/nonexistent/opencode.json")
    assert report.orchestrator.get("issues")
    assert len(report.orchestrator["issues"]) > 0


def test_report_to_dict(valid_config_file: Path) -> None:
    """Test report serialization to dict."""
    report = create_full_audit_task(str(valid_config_file))
    d = report.to_dict()
    assert "config_path" in d
    assert "timestamp" in d
    assert "orchestrator" in d
    assert "audit" in d
    assert "optimization" in d
    assert "raw_analyses" in d


def test_report_to_markdown(valid_config_file: Path) -> None:
    """Test markdown report generation."""
    report = create_full_audit_task(str(valid_config_file))
    md = report.to_markdown()
    assert "# OpenCode Config Audit Report" in md
    assert "## Summary" in md
    assert "Health Score" in md
    assert "## Detailed Analysis" in md


def test_report_to_markdown_with_findings(complex_config_file: Path) -> None:
    """Test markdown report with findings."""
    report = create_full_audit_task(str(complex_config_file))
    md = report.to_markdown()
    assert "## Audit Findings" in md or "## Optimization" in md


def test_save_report(valid_config_file: Path, tmp_path: Path) -> None:
    """Test saving report to files."""
    report = create_full_audit_task(str(valid_config_file))
    json_path, md_path = save_report(report, tmp_path)
    assert json_path.exists()
    assert md_path.exists()
    assert json_path.suffix == ".json"
    assert md_path.suffix == ".md"
    # Verify JSON is valid
    json.loads(json_path.read_text(encoding="utf-8"))
    # Verify markdown has content
    assert len(md_path.read_text(encoding="utf-8")) > 100


def test_save_report_default_dir(valid_config_file: Path) -> None:
    """Test saving report to default output directory."""
    import os
    report = create_full_audit_task(str(valid_config_file))
    try:
        json_path, md_path = save_report(report)
        assert json_path.exists()
        assert md_path.exists()
        assert json_path.parent.name == "output"
    finally:
        # Cleanup
        import shutil
        if Path("output").exists():
            shutil.rmtree("output")


def test_report_markdown_cached(valid_config_file: Path) -> None:
    """Test that markdown is cached after first generation."""
    report = create_full_audit_task(str(valid_config_file))
    md1 = report.to_markdown()
    md2 = report.to_markdown()
    assert md1 == md2
    assert report.markdown_report == md1


def test_full_audit_health_score(valid_config_file: Path) -> None:
    """Test health score is included in report."""
    report = create_full_audit_task(str(valid_config_file))
    summary = report.orchestrator.get("summary", {})
    assert "health_score" in summary
    assert 0 <= summary["health_score"] <= 100


def test_full_audit_recommendations(complex_config_file: Path) -> None:
    """Test recommendations are included."""
    report = create_full_audit_task(str(complex_config_file))
    recommendations = report.optimization.get("recommendations", [])
    # Complex config should trigger some recommendations
    assert len(recommendations) >= 1


def test_full_audit_raw_analyses(valid_config_file: Path) -> None:
    """Test raw analyses are populated."""
    report = create_full_audit_task(str(valid_config_file))
    raw = report.raw_analyses
    assert "permissions" in raw
    assert "agents" in raw
    assert "skills" in raw
    assert "mcp_servers" in raw
    assert "commands" in raw
