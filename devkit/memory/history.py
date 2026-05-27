"""Analysis History Store — Stores analysis results over time.

Uses SQLite for persistent storage. Records: timestamp, config path,
findings, scores. Supports querying by date range, severity, config path.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class AnalysisRecord:
    """A single analysis record."""

    id: int
    timestamp: str
    config_path: str
    health_score: int
    risk_score: int
    issue_count: int
    warning_count: int
    mcp_token_estimate: int
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    raw_report: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "config_path": self.config_path,
            "health_score": self.health_score,
            "risk_score": self.risk_score,
            "issue_count": self.issue_count,
            "warning_count": self.warning_count,
            "mcp_token_estimate": self.mcp_token_estimate,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "raw_report": self.raw_report,
        }


class AnalysisHistoryStore:
    """SQLite-backed analysis history store."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path("memory/history.db")
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    config_path TEXT NOT NULL,
                    health_score INTEGER NOT NULL DEFAULT 0,
                    risk_score INTEGER NOT NULL DEFAULT 0,
                    issue_count INTEGER NOT NULL DEFAULT 0,
                    warning_count INTEGER NOT NULL DEFAULT 0,
                    mcp_token_estimate INTEGER NOT NULL DEFAULT 0,
                    findings TEXT DEFAULT '[]',
                    recommendations TEXT DEFAULT '[]',
                    raw_report TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON analysis_records(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_path
                ON analysis_records(config_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_health_score
                ON analysis_records(health_score)
            """)

    def record_analysis(
        self,
        config_path: str,
        health_score: int = 0,
        risk_score: int = 0,
        issue_count: int = 0,
        warning_count: int = 0,
        mcp_token_estimate: int = 0,
        findings: Optional[list[dict[str, Any]]] = None,
        recommendations: Optional[list[dict[str, Any]]] = None,
        raw_report: Optional[str] = None,
    ) -> int:
        """Record an analysis result.

        Args:
            config_path: Path to the analyzed config.
            health_score: Health score (0-100).
            risk_score: Security risk score (0-100).
            issue_count: Number of issues found.
            warning_count: Number of warnings found.
            mcp_token_estimate: Estimated MCP token cost.
            findings: List of finding dicts.
            recommendations: List of recommendation dicts.
            raw_report: Optional raw report content.

        Returns:
            The ID of the inserted record.
        """
        timestamp = datetime.now().isoformat()
        findings_json = json.dumps(findings or [])
        recommendations_json = json.dumps(recommendations or [])

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_records (
                    timestamp, config_path, health_score, risk_score,
                    issue_count, warning_count, mcp_token_estimate,
                    findings, recommendations, raw_report
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    config_path,
                    health_score,
                    risk_score,
                    issue_count,
                    warning_count,
                    mcp_token_estimate,
                    findings_json,
                    recommendations_json,
                    raw_report,
                ),
            )
            return cursor.lastrowid

    def get_record(self, record_id: int) -> Optional[AnalysisRecord]:
        """Get a single analysis record by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM analysis_records WHERE id = ?",
                (record_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_record(row)

    def query_by_date_range(
        self,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> list[AnalysisRecord]:
        """Query records by date range.

        Args:
            start_date: ISO format start date (e.g., "2024-01-01").
            end_date: ISO format end date (e.g., "2024-12-31").

        Returns:
            List of matching records.
        """
        if end_date is None:
            end_date = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM analysis_records
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
                """,
                (start_date, end_date),
            ).fetchall()
            return [self._row_to_record(r) for r in rows]

    def query_by_config_path(
        self,
        config_path: str,
        limit: int = 10,
    ) -> list[AnalysisRecord]:
        """Query records by config path.

        Args:
            config_path: Path to filter by.
            limit: Maximum number of records to return.

        Returns:
            List of matching records.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM analysis_records
                WHERE config_path = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (config_path, limit),
            ).fetchall()
            return [self._row_to_record(r) for r in rows]

    def query_by_severity(
        self,
        severity: str,
        limit: int = 10,
    ) -> list[AnalysisRecord]:
        """Query records containing findings of a specific severity.

        Args:
            severity: Severity level to filter by (e.g., "critical", "high").
            limit: Maximum number of records to return.

        Returns:
            List of matching records.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT * FROM analysis_records
                WHERE findings LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (f'%"severity": "{severity}"%', limit),
            ).fetchall()
            return [self._row_to_record(r) for r in rows]

    def get_latest(self, config_path: Optional[str] = None) -> Optional[AnalysisRecord]:
        """Get the most recent analysis record.

        Args:
            config_path: Optional config path to filter by.

        Returns:
            The most recent record, or None if no records exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if config_path:
                row = conn.execute(
                    """
                    SELECT * FROM analysis_records
                    WHERE config_path = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (config_path,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM analysis_records
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """
                ).fetchone()
            if row is None:
                return None
            return self._row_to_record(row)

    def get_trend(
        self,
        config_path: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get health score trend over time.

        Args:
            config_path: Optional config path to filter by.
            limit: Maximum number of data points.

        Returns:
            List of {timestamp, health_score, risk_score} dicts.
        """
        with sqlite3.connect(self.db_path) as conn:
            if config_path:
                rows = conn.execute(
                    """
                    SELECT timestamp, health_score, risk_score
                    FROM analysis_records
                    WHERE config_path = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (config_path, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT timestamp, health_score, risk_score
                    FROM analysis_records
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [
                {
                    "timestamp": r[0],
                    "health_score": r[1],
                    "risk_score": r[2],
                }
                for r in rows
            ]

    def delete_record(self, record_id: int) -> bool:
        """Delete a single analysis record.

        Args:
            record_id: ID of the record to delete.

        Returns:
            True if a record was deleted.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM analysis_records WHERE id = ?",
                (record_id,),
            )
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        """Clear all analysis records.

        Returns:
            Number of records deleted.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM analysis_records")
            return cursor.rowcount

    def count(self, config_path: Optional[str] = None) -> int:
        """Count analysis records.

        Args:
            config_path: Optional config path to filter by.

        Returns:
            Number of matching records.
        """
        with sqlite3.connect(self.db_path) as conn:
            if config_path:
                row = conn.execute(
                    "SELECT COUNT(*) FROM analysis_records WHERE config_path = ?",
                    (config_path,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM analysis_records").fetchone()
            return row[0] if row else 0

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> AnalysisRecord:
        """Convert a database row to an AnalysisRecord."""
        return AnalysisRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            config_path=row["config_path"],
            health_score=row["health_score"],
            risk_score=row["risk_score"],
            issue_count=row["issue_count"],
            warning_count=row["warning_count"],
            mcp_token_estimate=row["mcp_token_estimate"],
            findings=json.loads(row["findings"]),
            recommendations=json.loads(row["recommendations"]),
            raw_report=row["raw_report"],
        )
