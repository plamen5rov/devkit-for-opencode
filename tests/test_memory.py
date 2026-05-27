"""Tests for the Analysis History Store and Recommendation Tracker."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from devkit.memory.history import AnalysisHistoryStore, AnalysisRecord
from devkit.memory.recommendations import RecommendationEntry, RecommendationTracker


@pytest.fixture
def store(tmp_path: Path) -> AnalysisHistoryStore:
    """Create a temporary analysis history store."""
    db_path = tmp_path / "history.db"
    return AnalysisHistoryStore(db_path)


@pytest.fixture
def tracker(tmp_path: Path) -> RecommendationTracker:
    """Create a temporary recommendation tracker."""
    db_path = tmp_path / "history.db"
    return RecommendationTracker(db_path)


@pytest.fixture
def store_with_data(store: AnalysisHistoryStore) -> AnalysisHistoryStore:
    """Create a store with sample data."""
    store.record_analysis(
        config_path="/test/opencode.json",
        health_score=80,
        risk_score=90,
        issue_count=2,
        warning_count=3,
        mcp_token_estimate=500,
        findings=[{"severity": "high", "message": "Test finding"}],
        recommendations=[{"category": "mcp", "title": "Disable server"}],
    )
    store.record_analysis(
        config_path="/test/opencode.json",
        health_score=85,
        risk_score=92,
        issue_count=1,
        warning_count=2,
        mcp_token_estimate=400,
        findings=[{"severity": "medium", "message": "Another finding"}],
        recommendations=[{"category": "agent", "title": "Lower temperature"}],
    )
    store.record_analysis(
        config_path="/other/opencode.json",
        health_score=70,
        risk_score=80,
        issue_count=5,
        warning_count=4,
        mcp_token_estimate=1200,
    )
    return store


# --- AnalysisHistoryStore Tests ---

def test_record_and_retrieve(store: AnalysisHistoryStore) -> None:
    """Test recording and retrieving an analysis."""
    record_id = store.record_analysis(
        config_path="/test/opencode.json",
        health_score=85,
        risk_score=90,
        issue_count=2,
        warning_count=3,
        mcp_token_estimate=500,
    )
    assert record_id > 0

    record = store.get_record(record_id)
    assert record is not None
    assert record.config_path == "/test/opencode.json"
    assert record.health_score == 85
    assert record.risk_score == 90
    assert record.issue_count == 2


def test_record_with_findings(store: AnalysisHistoryStore) -> None:
    """Test recording findings and recommendations."""
    findings = [{"severity": "high", "message": "Test"}]
    recs = [{"category": "mcp", "title": "Optimize"}]

    record_id = store.record_analysis(
        config_path="/test/opencode.json",
        findings=findings,
        recommendations=recs,
    )
    record = store.get_record(record_id)
    assert record is not None
    assert record.findings == findings
    assert record.recommendations == recs


def test_query_by_date_range(store_with_data: AnalysisHistoryStore) -> None:
    """Test querying by date range."""
    records = store_with_data.query_by_date_range("2000-01-01", "2099-12-31")
    assert len(records) == 3

    # Query with narrow range (should return nothing)
    records = store_with_data.query_by_date_range("2000-01-01", "2000-01-02")
    assert len(records) == 0


def test_query_by_config_path(store_with_data: AnalysisHistoryStore) -> None:
    """Test querying by config path."""
    records = store_with_data.query_by_config_path("/test/opencode.json")
    assert len(records) == 2
    assert all(r.config_path == "/test/opencode.json" for r in records)

    records = store_with_data.query_by_config_path("/other/opencode.json")
    assert len(records) == 1


def test_query_by_severity(store_with_data: AnalysisHistoryStore) -> None:
    """Test querying by severity."""
    records = store_with_data.query_by_severity("high")
    assert len(records) >= 1
    assert any(
        any(f.get("severity") == "high" for f in r.findings)
        for r in records
    )


def test_get_latest(store_with_data: AnalysisHistoryStore) -> None:
    """Test getting the latest record."""
    latest = store_with_data.get_latest()
    assert latest is not None
    assert latest.config_path == "/other/opencode.json"  # Most recent

    latest_test = store_with_data.get_latest("/test/opencode.json")
    assert latest_test is not None
    assert latest_test.config_path == "/test/opencode.json"


def test_get_latest_empty(store: AnalysisHistoryStore) -> None:
    """Test getting latest from empty store."""
    assert store.get_latest() is None


def test_get_trend(store_with_data: AnalysisHistoryStore) -> None:
    """Test getting health score trend."""
    trend = store_with_data.get_trend("/test/opencode.json")
    assert len(trend) == 2
    assert all("health_score" in t for t in trend)
    assert all("risk_score" in t for t in trend)
    assert all("timestamp" in t for t in trend)


def test_get_trend_all(store_with_data: AnalysisHistoryStore) -> None:
    """Test getting trend for all configs."""
    trend = store_with_data.get_trend()
    assert len(trend) == 3


def test_delete_record(store: AnalysisHistoryStore) -> None:
    """Test deleting a record."""
    record_id = store.record_analysis(config_path="/test.json", health_score=80)
    assert store.delete_record(record_id) is True
    assert store.get_record(record_id) is None


def test_delete_nonexistent_record(store: AnalysisHistoryStore) -> None:
    """Test deleting a nonexistent record."""
    assert store.delete_record(999) is False


def test_clear_all(store_with_data: AnalysisHistoryStore) -> None:
    """Test clearing all records."""
    count = store_with_data.clear_all()
    assert count == 3
    assert store_with_data.count() == 0


def test_count(store_with_data: AnalysisHistoryStore) -> None:
    """Test counting records."""
    assert store_with_data.count() == 3
    assert store_with_data.count("/test/opencode.json") == 2
    assert store_with_data.count("/other/opencode.json") == 1
    assert store_with_data.count("/nonexistent.json") == 0


def test_record_to_dict(store: AnalysisHistoryStore) -> None:
    """Test AnalysisRecord serialization."""
    record_id = store.record_analysis(
        config_path="/test.json",
        health_score=85,
        findings=[{"severity": "high"}],
    )
    record = store.get_record(record_id)
    assert record is not None
    d = record.to_dict()
    assert d["config_path"] == "/test.json"
    assert d["health_score"] == 85
    assert d["findings"] == [{"severity": "high"}]


# --- RecommendationTracker Tests ---

def test_add_recommendations(tracker: RecommendationTracker) -> None:
    """Test adding recommendations."""
    recs = [
        {"category": "mcp", "title": "Disable server", "description": "High cost"},
        {"category": "agent", "title": "Lower temperature", "description": "Too random"},
    ]
    ids = tracker.add_recommendations(analysis_id=1, recommendations=recs)
    assert len(ids) == 2
    assert all(i > 0 for i in ids)


def test_update_status(tracker: RecommendationTracker) -> None:
    """Test updating recommendation status."""
    ids = tracker.add_recommendations(analysis_id=1, recommendations=[
        {"category": "mcp", "title": "Test rec", "description": "Test"},
    ])
    rec_id = ids[0]

    assert tracker.update_status(rec_id, "applied", notes="Done") is True
    rec = tracker.get_recommendation(rec_id)
    assert rec is not None
    assert rec.status == "applied"
    assert rec.applied_at is not None
    assert rec.notes == "Done"


def test_update_status_invalid(tracker: RecommendationTracker) -> None:
    """Test updating with invalid status."""
    ids = tracker.add_recommendations(analysis_id=1, recommendations=[
        {"category": "mcp", "title": "Test rec", "description": "Test"},
    ])
    assert tracker.update_status(ids[0], "invalid_status") is False


def test_get_by_status(tracker: RecommendationTracker) -> None:
    """Test getting recommendations by status."""
    tracker.add_recommendations(analysis_id=1, recommendations=[
        {"category": "mcp", "title": "Rec 1", "description": ""},
        {"category": "agent", "title": "Rec 2", "description": ""},
    ])
    open_recs = tracker.get_by_status("open")
    assert len(open_recs) == 2

    tracker.update_status(open_recs[0].id, "applied")
    assert len(tracker.get_by_status("open")) == 1
    assert len(tracker.get_by_status("applied")) == 1


def test_get_by_analysis(tracker: RecommendationTracker) -> None:
    """Test getting recommendations by analysis ID."""
    tracker.add_recommendations(analysis_id=1, recommendations=[
        {"category": "mcp", "title": "Rec 1", "description": ""},
    ])
    tracker.add_recommendations(analysis_id=2, recommendations=[
        {"category": "agent", "title": "Rec 2", "description": ""},
    ])

    recs_1 = tracker.get_by_analysis(1)
    assert len(recs_1) == 1
    assert recs_1[0].title == "Rec 1"

    recs_2 = tracker.get_by_analysis(2)
    assert len(recs_2) == 1
    assert recs_2[0].title == "Rec 2"


def test_get_recommendation(tracker: RecommendationTracker) -> None:
    """Test getting a single recommendation."""
    ids = tracker.add_recommendations(analysis_id=1, recommendations=[
        {"category": "mcp", "title": "Test", "description": "Desc"},
    ])
    rec = tracker.get_recommendation(ids[0])
    assert rec is not None
    assert rec.category == "mcp"
    assert rec.title == "Test"
    assert rec.description == "Desc"


def test_get_nonexistent_recommendation(tracker: RecommendationTracker) -> None:
    """Test getting a nonexistent recommendation."""
    assert tracker.get_recommendation(999) is None


def test_generate_diff_report(
    store_with_data: AnalysisHistoryStore,
    tracker: RecommendationTracker,
) -> None:
    """Test generating diff report between analyses."""
    # Add recommendations for both analyses
    records = store_with_data.query_by_config_path("/test/opencode.json")
    assert len(records) >= 2

    tracker.add_recommendations(analysis_id=records[1].id, recommendations=[
        {"category": "mcp", "title": "Old rec", "description": ""},
        {"category": "agent", "title": "Persistent rec", "description": ""},
    ])
    tracker.add_recommendations(analysis_id=records[0].id, recommendations=[
        {"category": "agent", "title": "Persistent rec", "description": ""},
        {"category": "skill", "title": "New rec", "description": ""},
    ])

    report = tracker.generate_diff_report("/test/opencode.json")
    assert "new" in report
    assert "resolved" in report
    assert "persistent" in report
    assert "summary" in report
    assert any(r["title"] == "New rec" for r in report["new"])
    assert any(r["title"] == "Old rec" for r in report["resolved"])
    assert any(r["title"] == "Persistent rec" for r in report["persistent"])


def test_diff_report_no_records(store: AnalysisHistoryStore, tracker: RecommendationTracker) -> None:
    """Test diff report with no records."""
    report = tracker.generate_diff_report()
    assert "No analysis records found" in report["message"]


def test_diff_report_single_record(
    store: AnalysisHistoryStore,
    tracker: RecommendationTracker,
) -> None:
    """Test diff report with only one record."""
    record_id = store.record_analysis(
        config_path="/test.json",
        health_score=80,
        findings=[],
        recommendations=[{"category": "mcp", "title": "Only rec"}],
    )
    tracker.add_recommendations(analysis_id=record_id, recommendations=[
        {"category": "mcp", "title": "Only rec", "description": ""},
    ])
    report = tracker.generate_diff_report()
    assert "Only one analysis record" in report["message"]
    assert len(report["new"]) == 1


def test_get_summary(tracker: RecommendationTracker) -> None:
    """Test getting recommendation summary."""
    tracker.add_recommendations(analysis_id=1, recommendations=[
        {"category": "mcp", "title": "Rec 1", "description": ""},
        {"category": "agent", "title": "Rec 2", "description": ""},
        {"category": "skill", "title": "Rec 3", "description": ""},
    ])
    # Update one to applied, one to dismissed
    open_recs = tracker.get_by_status("open")
    tracker.update_status(open_recs[0].id, "applied")
    tracker.update_status(open_recs[1].id, "dismissed")

    summary = tracker.get_summary()
    assert summary["total"] == 3
    assert summary["open"] == 1
    assert summary["applied"] == 1
    assert summary["dismissed"] == 1


def test_recommendation_entry_to_dict() -> None:
    """Test RecommendationEntry serialization."""
    entry = RecommendationEntry(
        id=1,
        analysis_id=42,
        category="mcp",
        title="Test",
        description="Desc",
        status="open",
        created_at="2024-01-01T00:00:00",
    )
    d = entry.to_dict()
    assert d["id"] == 1
    assert d["analysis_id"] == 42
    assert d["category"] == "mcp"
    assert d["status"] == "open"
