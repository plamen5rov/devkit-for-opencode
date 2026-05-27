"""Tests for the Migration Assistant Task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.tasks.migration_assistant import (
    MigrationChange,
    MigrationReport,
    generate_migration_diff,
    run_migration_analysis,
)


@pytest.fixture
def legacy_tools_config(tmp_path: Path) -> Path:
    """Create a config with legacy tools field."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "tools": {
            "bash": True,
            "edit": True,
            "write": False,
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def legacy_boolean_tools_config(tmp_path: Path) -> Path:
    """Create a config with boolean tools field."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "tools": True,
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def legacy_model_config(tmp_path: Path) -> Path:
    """Create a config with legacy model format."""
    config = {
        "model": "claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def legacy_share_config(tmp_path: Path) -> Path:
    """Create a config with legacy share format."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "share": True,
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def legacy_plugin_config(tmp_path: Path) -> Path:
    """Create a config with @latest plugins."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "plugin": ["my-plugin@latest", "another-plugin@1.2.3"],
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def agent_tools_config(tmp_path: Path) -> Path:
    """Create a config with agent-level tools field."""
    config = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "agent": {
            "build": {
                "mode": "primary",
                "description": "Build",
                "tools": {
                    "bash": True,
                    "edit": True,
                },
            },
        },
    }
    config_file = tmp_path / "opencode.json"
    config_file.write_text(json.dumps(config))
    return config_file


def test_migration_legacy_tools(legacy_tools_config: Path) -> None:
    """Test migrating legacy tools field."""
    report = run_migration_analysis(str(legacy_tools_config))
    assert report.is_migrated
    assert report.required_count >= 1
    assert any(
        c.field.startswith("tools.") and c.severity == "required"
        for c in report.changes
    )
    # Verify tools field is removed
    assert "tools" not in report.migrated_config
    # Verify permission field exists
    assert "permission" in report.migrated_config


def test_migration_boolean_tools(legacy_boolean_tools_config: Path) -> None:
    """Test migrating boolean tools field."""
    report = run_migration_analysis(str(legacy_boolean_tools_config))
    assert report.is_migrated
    assert any(
        c.field == "tools" and c.severity == "required"
        for c in report.changes
    )
    assert "tools" not in report.migrated_config


def test_migration_legacy_model(legacy_model_config: Path) -> None:
    """Test migrating legacy model format."""
    report = run_migration_analysis(str(legacy_model_config))
    assert report.is_migrated
    assert any(
        c.field == "model" and "provider prefix" in c.reason
        for c in report.changes
    )
    assert report.migrated_config["model"] == "anthropic/claude-sonnet-4-20250514"


def test_migration_legacy_share(legacy_share_config: Path) -> None:
    """Test migrating legacy share format."""
    report = run_migration_analysis(str(legacy_share_config))
    assert report.is_migrated
    assert any(
        c.field == "share" and c.severity == "required"
        for c in report.changes
    )
    assert report.migrated_config["share"] == "auto"


def test_migration_latest_plugins(legacy_plugin_config: Path) -> None:
    """Test migrating @latest plugins."""
    report = run_migration_analysis(str(legacy_plugin_config))
    assert report.is_migrated
    assert any(
        c.field.startswith("plugin[") and "@latest" in str(c.old_value)
        for c in report.changes
    )


def test_migration_agent_tools(agent_tools_config: Path) -> None:
    """Test migrating agent-level tools field."""
    report = run_migration_analysis(str(agent_tools_config))
    assert report.is_migrated
    assert any(
        c.field.startswith("agent.") and "tools" in c.field
        for c in report.changes
    )
    # Verify agent tools field is removed
    assert "tools" not in report.migrated_config["agent"]["build"]
    # Verify permission field exists
    assert "permission" in report.migrated_config["agent"]["build"]


def test_migration_no_changes_needed() -> None:
    """Test migration with no changes needed."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config = {
            "model": "anthropic/claude-sonnet-4-20250514",
            "permission": {"*": "ask"},
            "share": "manual",
        }
        json.dump(config, f)
        path = Path(f.name)
    try:
        report = run_migration_analysis(str(path))
        assert not report.is_migrated
        assert len(report.changes) == 0
    finally:
        path.unlink()


def test_migration_missing_file() -> None:
    """Test migration with missing config."""
    report = run_migration_analysis("/nonexistent/opencode.json")
    assert not report.is_migrated
    assert len(report.changes) == 0


def test_migration_diff_save(legacy_tools_config: Path, tmp_path: Path) -> None:
    """Test saving migration diff to file."""
    output_path = tmp_path / "migrated.json"
    report, saved_path = generate_migration_diff(
        str(legacy_tools_config),
        str(output_path),
    )
    assert report.is_migrated
    assert saved_path is not None
    assert saved_path.exists()
    # Verify saved config is valid JSON
    migrated = json.loads(saved_path.read_text(encoding="utf-8"))
    assert "tools" not in migrated
    assert "permission" in migrated


def test_migration_diff_no_save(legacy_tools_config: Path) -> None:
    """Test migration diff without saving."""
    report, saved_path = generate_migration_diff(str(legacy_tools_config))
    assert report.is_migrated
    assert saved_path is None


def test_migration_change_to_dict() -> None:
    """Test MigrationChange serialization."""
    change = MigrationChange(
        field="tools.bash",
        old_value=True,
        new_value="permission.bash: allow",
        reason="Legacy tools deprecated",
        severity="required",
    )
    d = change.to_dict()
    assert d["field"] == "tools.bash"
    assert d["old_value"] is True
    assert d["new_value"] == "permission.bash: allow"
    assert d["severity"] == "required"


def test_migration_report_to_dict(legacy_tools_config: Path) -> None:
    """Test MigrationReport serialization."""
    report = run_migration_analysis(str(legacy_tools_config))
    d = report.to_dict()
    assert "config_path" in d
    assert "changes" in d
    assert "migrated_config" in d
    assert "is_migrated" in d
    assert "required_count" in d
    assert "recommended_count" in d
    assert "optional_count" in d


def test_migration_report_to_markdown(legacy_tools_config: Path) -> None:
    """Test Markdown migration report."""
    report = run_migration_analysis(str(legacy_tools_config))
    md = report.to_markdown()
    assert "# Migration Report" in md
    assert "Required" in md
    if report.changes:
        assert "## Changes" in md
        assert "Field" in md


def test_migration_severity_counts(legacy_tools_config: Path) -> None:
    """Test severity count calculation."""
    report = run_migration_analysis(str(legacy_tools_config))
    assert report.required_count == sum(
        1 for c in report.changes if c.severity == "required"
    )
    assert report.recommended_count == sum(
        1 for c in report.changes if c.severity == "recommended"
    )
    assert report.optional_count == sum(
        1 for c in report.changes if c.severity == "optional"
    )
