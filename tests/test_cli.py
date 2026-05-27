"""Tests for the CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devkit.cli import (
    cmd_analyze,
    cmd_audit,
    cmd_history,
    cmd_migrate,
    cmd_score,
    detect_config,
    format_table,
    main,
    parse_args,
)


@pytest.fixture
def valid_config(tmp_path: Path) -> Path:
    """Create a valid test config."""
    config = tmp_path / "opencode.json"
    config.write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }))
    return config


@pytest.fixture
def mock_report():
    """Create a mock audit report."""
    report = MagicMock()
    report.to_dict.return_value = {
        "health_score": 85,
        "summary": {
            "health_score": 85,
            "total_issues": 2,
            "total_warnings": 3,
            "agent_count": 1,
            "skill_count": 2,
            "mcp_count": 1,
            "command_count": 3,
            "mcp_token_estimate": 500,
        },
    }
    report.to_markdown.return_value = "# Audit Report\n\nHealth Score: 85/100"
    report.summary = {
        "health_score": 85,
        "total_issues": 2,
        "total_warnings": 3,
        "agent_count": 1,
        "skill_count": 2,
        "mcp_count": 1,
        "command_count": 3,
        "mcp_token_estimate": 500,
    }
    return report


@pytest.fixture
def mock_security_result():
    """Create a mock security scan result."""
    result = MagicMock()
    result.to_dict.return_value = {
        "risk_score": 90,
        "findings": [],
    }
    result.to_markdown.return_value = "# Security Scan\n\nRisk Score: 90/100"
    return result


@pytest.fixture
def mock_orchestration_result():
    """Create a mock orchestration result."""
    result = MagicMock()
    result.summary = {
        "health_score": 85,
        "total_issues": 2,
        "total_warnings": 3,
        "agent_count": 1,
        "skill_count": 2,
        "mcp_count": 1,
        "command_count": 3,
        "mcp_token_estimate": 500,
    }
    return result


@pytest.fixture
def mock_migration_result():
    """Create a mock migration result."""
    result = MagicMock()
    result.to_dict.return_value = {
        "changes": [],
        "migrated": True,
    }
    result.to_markdown.return_value = "# Migration Report\n\nNo changes needed"
    result.migrated_config = {"$schema": "https://opencode.ai/config.json"}
    return result


# --- parse_args tests ---

def test_parse_args_no_command():
    """Test parsing with no command."""
    args = parse_args([])
    assert args.command is None


def test_parse_args_analyze():
    """Test parsing analyze command."""
    args = parse_args(["analyze", "--config-path", "/test.json", "--format", "markdown"])
    assert args.command == "analyze"
    assert args.config_path == "/test.json"
    assert args.output_format == "markdown"


def test_parse_args_audit():
    """Test parsing audit command."""
    args = parse_args(["audit", "--config-path", "/test.json", "--fix"])
    assert args.command == "audit"
    assert args.fix is True


def test_parse_args_score():
    """Test parsing score command."""
    args = parse_args(["score", "--config-path", "/test.json", "--detailed"])
    assert args.command == "score"
    assert args.detailed is True


def test_parse_args_history():
    """Test parsing history command."""
    args = parse_args(["history", "--limit", "5", "--format", "json"])
    assert args.command == "history"
    assert args.limit == 5
    assert args.output_format == "json"


def test_parse_args_migrate():
    """Test parsing migrate command."""
    args = parse_args(["migrate", "--config-path", "/test.json", "--diff"])
    assert args.command == "migrate"
    assert args.diff is True


def test_parse_args_verbose():
    """Test verbose flag."""
    args = parse_args(["analyze", "--verbose"])
    assert args.verbose is True


# --- format_table tests ---

def test_format_table():
    """Test table formatting."""
    output = format_table(["Name", "Value"], [["a", "1"], ["b", "2"]])
    assert "Name" in output
    assert "Value" in output
    assert "a" in output
    assert "b" in output


def test_format_table_empty():
    """Test empty table."""
    output = format_table(["Name"], [])
    assert "No data" in output


# --- detect_config tests ---

def test_detect_config_no_config():
    """Test detection when no config exists."""
    with patch("pathlib.Path.exists", return_value=False):
        assert detect_config() is None


# --- cmd_analyze tests ---

@patch("devkit.tasks.full_audit.create_full_audit_task")
def test_cmd_analyze_json(mock_task, valid_config, mock_report, capsys):
    """Test analyze command with JSON output."""
    mock_task.return_value = mock_report
    args = parse_args(["analyze", "--config-path", str(valid_config), "--format", "json"])
    rc = cmd_analyze(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "health_score" in captured.out


@patch("devkit.tasks.full_audit.create_full_audit_task")
def test_cmd_analyze_markdown(mock_task, valid_config, mock_report, capsys):
    """Test analyze command with Markdown output."""
    mock_task.return_value = mock_report
    args = parse_args(["analyze", "--config-path", str(valid_config), "--format", "markdown"])
    rc = cmd_analyze(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "# Audit Report" in captured.out


@patch("devkit.tasks.full_audit.create_full_audit_task")
def test_cmd_analyze_table(mock_task, valid_config, mock_report, capsys):
    """Test analyze command with table output."""
    mock_task.return_value = mock_report
    args = parse_args(["analyze", "--config-path", str(valid_config), "--format", "table"])
    rc = cmd_analyze(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "Health Score:" in captured.out
    assert "Issues" in captured.out


def test_cmd_analyze_no_config(capsys):
    """Test analyze with no config."""
    args = parse_args(["analyze"])
    with patch("devkit.cli.detect_config", return_value=None):
        rc = cmd_analyze(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "No OpenCode config found" in captured.out


# --- cmd_audit tests ---

@patch("devkit.tasks.security_scan.run_security_scan")
def test_cmd_audit_json(mock_scan, valid_config, mock_security_result, capsys):
    """Test audit command with JSON output."""
    mock_scan.return_value = mock_security_result
    args = parse_args(["audit", "--config-path", str(valid_config), "--format", "json"])
    rc = cmd_audit(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "risk_score" in captured.out


@patch("devkit.tasks.security_scan.run_security_scan")
def test_cmd_audit_markdown(mock_scan, valid_config, mock_security_result, capsys):
    """Test audit command with Markdown output."""
    mock_scan.return_value = mock_security_result
    args = parse_args(["audit", "--config-path", str(valid_config), "--format", "markdown"])
    rc = cmd_audit(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "# Security Scan" in captured.out


# --- cmd_score tests ---

@patch("devkit.agents.orchestrator.run_orchestration")
def test_cmd_score_json(mock_orch, valid_config, mock_orchestration_result, capsys):
    """Test score command with JSON output."""
    mock_orch.return_value = mock_orchestration_result
    args = parse_args(["score", "--config-path", str(valid_config), "--format", "json"])
    rc = cmd_score(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "health_score" in captured.out


@patch("devkit.agents.orchestrator.run_orchestration")
def test_cmd_score_detailed_json(mock_orch, valid_config, mock_orchestration_result, capsys):
    """Test score command with detailed JSON output."""
    mock_orch.return_value = mock_orchestration_result
    args = parse_args(["score", "--config-path", str(valid_config), "--format", "json", "--detailed"])
    rc = cmd_score(args)
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "breakdown" in data
    assert "issues" in data["breakdown"]


@patch("devkit.agents.orchestrator.run_orchestration")
def test_cmd_score_table(mock_orch, valid_config, mock_orchestration_result, capsys):
    """Test score command with table output."""
    mock_orch.return_value = mock_orchestration_result
    args = parse_args(["score", "--config-path", str(valid_config), "--format", "table", "--detailed"])
    rc = cmd_score(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "Health Score:" in captured.out
    assert "Factor" in captured.out


# --- cmd_history tests ---

def test_cmd_history_no_db(capsys, tmp_path):
    """Test history with no database."""
    db_path = tmp_path / "nonexistent.db"
    args = parse_args(["history", "--db-path", str(db_path)])
    rc = cmd_history(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No analysis history found" in captured.out


def test_cmd_history_empty_db(capsys, tmp_path):
    """Test history with empty database."""
    from devkit.memory.history import AnalysisHistoryStore

    db_path = tmp_path / "history.db"
    AnalysisHistoryStore(db_path)
    args = parse_args(["history", "--db-path", str(db_path)])
    rc = cmd_history(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No analysis records found" in captured.out


def test_cmd_history_with_data(capsys, tmp_path):
    """Test history with data."""
    from devkit.memory.history import AnalysisHistoryStore

    db_path = tmp_path / "history.db"
    store = AnalysisHistoryStore(db_path)
    store.record_analysis(config_path="/test.json", health_score=85)

    args = parse_args(["history", "--db-path", str(db_path), "--format", "json"])
    rc = cmd_history(args)
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 1
    assert data[0]["config_path"] == "/test.json"


def test_cmd_history_table(capsys, tmp_path):
    """Test history with table output."""
    from devkit.memory.history import AnalysisHistoryStore

    db_path = tmp_path / "history.db"
    store = AnalysisHistoryStore(db_path)
    store.record_analysis(config_path="/test.json", health_score=85)

    args = parse_args(["history", "--db-path", str(db_path), "--format", "table"])
    rc = cmd_history(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "Config Path" in captured.out
    assert "/test.json" in captured.out


# --- cmd_migrate tests ---

@patch("devkit.tasks.migration_assistant.run_migration_analysis")
def test_cmd_migrate_markdown(mock_migrate, valid_config, mock_migration_result, capsys):
    """Test migrate command with Markdown output."""
    mock_migrate.return_value = mock_migration_result
    args = parse_args(["migrate", "--config-path", str(valid_config)])
    rc = cmd_migrate(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "# Migration Report" in captured.out


@patch("devkit.tasks.migration_assistant.run_migration_analysis")
def test_cmd_migrate_json(mock_migrate, valid_config, mock_migration_result, capsys):
    """Test migrate command with JSON output."""
    mock_migrate.return_value = mock_migration_result
    args = parse_args(["migrate", "--config-path", str(valid_config), "--format", "json"])
    rc = cmd_migrate(args)
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "changes" in data


@patch("devkit.tasks.migration_assistant.run_migration_analysis")
def test_cmd_migrate_with_diff(mock_migrate, valid_config, mock_migration_result, capsys):
    """Test migrate command with diff flag."""
    mock_migrate.return_value = mock_migration_result
    args = parse_args(["migrate", "--config-path", str(valid_config), "--format", "markdown", "--diff"])
    rc = cmd_migrate(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "Migrated Config" in captured.out
    assert "$schema" in captured.out


# --- main tests ---

def test_main_no_command(capsys):
    """Test main with no command."""
    with patch("devkit.cli.parse_args") as mock_parse:
        args = parse_args([])
        mock_parse.return_value = args
        rc = main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "Usage:" in captured.out
    assert "Commands:" in captured.out


@patch("devkit.cli.cmd_analyze")
def test_main_analyze(mock_cmd):
    """Test main dispatches to analyze."""
    mock_cmd.return_value = 0
    with patch("devkit.cli.parse_args") as mock_parse:
        mock_parse.return_value = parse_args(["analyze"])
        rc = main()
    assert rc == 0
    mock_cmd.assert_called_once()


def test_main_unknown_command(capsys):
    """Test main with unknown command."""
    with patch("devkit.cli.parse_args") as mock_parse:
        args = parse_args([])
        args.command = "unknown"
        mock_parse.return_value = args
        rc = main()
    assert rc == 1
    captured = capsys.readouterr()
    assert "Unknown command" in captured.out
