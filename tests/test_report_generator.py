"""Tests for the Report Generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.output.report_generator import ReportGenerator


@pytest.fixture
def sample_data() -> dict:
    """Sample analysis data for testing."""
    return {
        "summary": {
            "health_score": 85,
            "risk_score": 90,
            "total_issues": 2,
            "total_warnings": 3,
        },
        "findings": [
            {"severity": "error", "category": "security", "message": "Hardcoded secret found"},
            {"severity": "warning", "category": "permissions", "message": "Overly permissive bash rule"},
            {"severity": "info", "category": "best-practice", "message": "Consider adding schema"},
        ],
        "recommendations": [
            {"category": "mcp", "title": "Disable high-cost server", "description": "Saves ~500 tokens/session"},
            {"category": "permissions", "title": "Tighten bash rules", "description": "Remove glob patterns"},
        ],
        "trends": [
            {"timestamp": "2024-01-01T00:00:00", "health_score": 80, "risk_score": 85},
            {"timestamp": "2024-01-02T00:00:00", "health_score": 85, "risk_score": 90},
        ],
        "raw": {"model": "anthropic/claude-sonnet-4-20250514"},
    }


@pytest.fixture
def generator(tmp_path: Path) -> ReportGenerator:
    """Create a report generator with temp output dir."""
    return ReportGenerator(output_dir=tmp_path)


def test_generate_json(generator: ReportGenerator, sample_data: dict, tmp_path: Path) -> None:
    """Test generating JSON report."""
    filepath = generator.generate_json(sample_data)
    assert filepath.exists()
    assert filepath.suffix == ".json"

    content = json.loads(filepath.read_text())
    assert content["summary"]["health_score"] == 85
    assert len(content["findings"]) == 3


def test_generate_markdown(generator: ReportGenerator, sample_data: dict, tmp_path: Path) -> None:
    """Test generating Markdown report."""
    filepath = generator.generate_markdown(sample_data)
    assert filepath.exists()
    assert filepath.suffix == ".md"

    content = filepath.read_text()
    assert "# DevKit Analysis Report" in content
    assert "## Summary" in content
    assert "**Health Score:** 85/100" in content
    assert "## Findings" in content
    assert "Hardcoded secret found" in content
    assert "## Recommendations" in content
    assert "Disable high-cost server" in content
    assert "## Score Trends" in content
    assert "## Raw Data" in content


def test_generate_html(generator: ReportGenerator, sample_data: dict, tmp_path: Path) -> None:
    """Test generating HTML report."""
    filepath = generator.generate_html(sample_data)
    assert filepath.exists()
    assert filepath.suffix == ".html"

    content = filepath.read_text()
    assert "<!DOCTYPE html>" in content
    assert "DevKit Analysis Report" in content
    assert "Health Score: 85/100" in content
    assert "Risk Score: 90/100" in content
    assert "Hardcoded secret found" in content
    assert "Disable high-cost server" in content


def test_generate_with_prefix(generator: ReportGenerator, sample_data: dict) -> None:
    """Test custom filename prefix."""
    filepath = generator.generate(sample_data, prefix="audit")
    assert filepath.name.startswith("audit_")


def test_generate_empty_data(generator: ReportGenerator, tmp_path: Path) -> None:
    """Test generating report with empty data."""
    filepath = generator.generate_json({})
    assert filepath.exists()
    content = json.loads(filepath.read_text())
    assert content == {}


def test_generate_markdown_empty(generator: ReportGenerator, tmp_path: Path) -> None:
    """Test generating Markdown with empty data."""
    filepath = generator.generate_markdown({})
    content = filepath.read_text()
    assert "# DevKit Analysis Report" in content
    assert "## Summary" not in content
    assert "## Findings" not in content


def test_generate_html_empty(generator: ReportGenerator, tmp_path: Path) -> None:
    """Test generating HTML with empty data."""
    filepath = generator.generate_html({})
    content = filepath.read_text()
    assert "<!DOCTYPE html>" in content
    assert "Health Score: 0/100" in content


def test_generate_multiple_reports(generator: ReportGenerator, sample_data: dict) -> None:
    """Test generating multiple reports creates unique files."""
    import time

    path1 = generator.generate_json(sample_data)
    time.sleep(1.1)  # Ensure different timestamp
    path2 = generator.generate_json(sample_data)

    assert path1 != path2
    assert path1.exists()
    assert path2.exists()


def test_output_dir_created(tmp_path: Path) -> None:
    """Test that output directory is created if it doesn't exist."""
    nested_dir = tmp_path / "nested" / "output"
    gen = ReportGenerator(output_dir=nested_dir)
    assert nested_dir.exists()

    filepath = gen.generate_json({"test": True})
    assert filepath.exists()


def test_generate_with_format_method(generator: ReportGenerator, sample_data: dict) -> None:
    """Test generate() method with different formats."""
    json_path = generator.generate(sample_data, fmt="json")
    assert json_path.suffix == ".json"

    md_path = generator.generate(sample_data, fmt="markdown")
    assert md_path.suffix == ".md"

    html_path = generator.generate(sample_data, fmt="html")
    assert html_path.suffix == ".html"


def test_markdown_findings_table(generator: ReportGenerator, tmp_path: Path) -> None:
    """Test Markdown findings table formatting."""
    data = {
        "findings": [
            {"severity": "error", "category": "sec", "message": "Test"},
        ],
    }
    filepath = generator.generate_markdown(data)
    content = filepath.read_text()
    assert "| Severity | Category | Message |" in content
    assert "| error | sec | Test |" in content


def test_markdown_recommendations(generator: ReportGenerator, tmp_path: Path) -> None:
    """Test Markdown recommendations formatting."""
    data = {
        "recommendations": [
            {"category": "mcp", "title": "Optimize", "description": "Save tokens"},
        ],
    }
    filepath = generator.generate_markdown(data)
    content = filepath.read_text()
    assert "### 1. Optimize" in content
    assert "**Category:** mcp" in content
    assert "Save tokens" in content


def test_markdown_trends_table(generator: ReportGenerator, tmp_path: Path) -> None:
    """Test Markdown trends table formatting."""
    data = {
        "trends": [
            {"timestamp": "2024-01-01T00:00:00", "health_score": 80, "risk_score": 85},
        ],
    }
    filepath = generator.generate_markdown(data)
    content = filepath.read_text()
    assert "| Date | Health Score | Risk Score |" in content
    assert "2024-01-01" in content
