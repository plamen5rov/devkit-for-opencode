"""Recommendation Tracker — Track recommendation lifecycle.

Records: recommendation, status (open, applied, dismissed), date applied.
Links recommendations to analysis runs.
Generates "what changed since last analysis" report.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class RecommendationEntry:
    """A tracked recommendation."""

    id: int
    analysis_id: int
    category: str
    title: str
    description: str
    status: str  # "open", "applied", "dismissed"
    created_at: str
    applied_at: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "applied_at": self.applied_at,
            "notes": self.notes,
        }


class RecommendationTracker:
    """SQLite-backed recommendation tracker."""

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
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    applied_at TEXT,
                    notes TEXT,
                    FOREIGN KEY (analysis_id) REFERENCES analysis_records(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rec_status
                ON recommendations(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rec_analysis_id
                ON recommendations(analysis_id)
            """)

    def add_recommendations(
        self,
        analysis_id: int,
        recommendations: list[dict[str, Any]],
    ) -> list[int]:
        """Add recommendations from an analysis run.

        Args:
            analysis_id: ID of the analysis record.
            recommendations: List of recommendation dicts with 'category', 'title', 'description'.

        Returns:
            List of inserted recommendation IDs.
        """
        ids = []
        created_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            for rec in recommendations:
                cursor = conn.execute(
                    """
                    INSERT INTO recommendations (
                        analysis_id, category, title, description, status, created_at
                    ) VALUES (?, ?, ?, ?, 'open', ?)
                    """,
                    (
                        analysis_id,
                        rec.get("category", "unknown"),
                        rec.get("title", ""),
                        rec.get("description", ""),
                        created_at,
                    ),
                )
                ids.append(cursor.lastrowid)

        return ids

    def update_status(
        self,
        recommendation_id: int,
        status: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Update a recommendation's status.

        Args:
            recommendation_id: ID of the recommendation.
            status: New status ("open", "applied", "dismissed").
            notes: Optional notes about the status change.

        Returns:
            True if the update succeeded.
        """
        if status not in ("open", "applied", "dismissed"):
            return False

        applied_at = datetime.now().isoformat() if status == "applied" else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE recommendations
                SET status = ?, applied_at = ?, notes = ?
                WHERE id = ?
                """,
                (status, applied_at, notes, recommendation_id),
            )
            return cursor.rowcount > 0

    def get_recommendation(self, recommendation_id: int) -> Optional[RecommendationEntry]:
        """Get a single recommendation by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM recommendations WHERE id = ?",
                (recommendation_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_entry(row)

    def get_by_status(
        self,
        status: str,
        limit: int = 50,
    ) -> list[RecommendationEntry]:
        """Get recommendations by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM recommendations
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]

    def get_by_analysis(self, analysis_id: int) -> list[RecommendationEntry]:
        """Get recommendations from a specific analysis run."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM recommendations
                WHERE analysis_id = ?
                ORDER BY created_at DESC
                """,
                (analysis_id,),
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]

    def generate_diff_report(
        self,
        config_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate "what changed since last analysis" report.

        Compares the latest analysis recommendations with previous ones.

        Args:
            config_path: Optional config path to filter by.

        Returns:
            Dict with new, resolved, and persistent recommendations.
        """
        from devkit.memory.history import AnalysisHistoryStore

        store = AnalysisHistoryStore(self.db_path)

        # Get latest record
        latest = store.get_latest(config_path)
        if latest is None:
            return {
                "new": [],
                "resolved": [],
                "persistent": [],
                "message": "No analysis records found",
            }

        # Get latest recommendations
        latest_recs = self.get_by_analysis(latest.id)
        latest_titles = {r.title for r in latest_recs}

        # Get previous record
        records = store.query_by_config_path(config_path or "", limit=2)
        if len(records) < 2:
            return {
                "new": [r.to_dict() for r in latest_recs],
                "resolved": [],
                "persistent": [],
                "message": "Only one analysis record — all recommendations are new",
            }

        previous = records[1]  # Second most recent
        previous_recs = self.get_by_analysis(previous.id)
        previous_titles = {r.title for r in previous_recs}

        # Compare
        new_titles = latest_titles - previous_titles
        resolved_titles = previous_titles - latest_titles
        persistent_titles = latest_titles & previous_titles

        return {
            "new": [
                r.to_dict() for r in latest_recs if r.title in new_titles
            ],
            "resolved": [
                r.to_dict() for r in previous_recs if r.title in resolved_titles
            ],
            "persistent": [
                r.to_dict() for r in latest_recs if r.title in persistent_titles
            ],
            "summary": {
                "new_count": len(new_titles),
                "resolved_count": len(resolved_titles),
                "persistent_count": len(persistent_titles),
                "latest_health_score": latest.health_score,
                "previous_health_score": previous.health_score,
                "score_change": latest.health_score - previous.health_score,
            },
        }

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all recommendations."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_count,
                    SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied_count,
                    SUM(CASE WHEN status = 'dismissed' THEN 1 ELSE 0 END) as dismissed_count
                FROM recommendations
                """
            ).fetchone()
            return {
                "total": row[0],
                "open": row[1],
                "applied": row[2],
                "dismissed": row[3],
            }

    def clear_all(self) -> int:
        """Clear all recommendation records.

        Returns:
            Number of records deleted.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM recommendations")
            return cursor.rowcount

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> RecommendationEntry:
        """Convert a database row to a RecommendationEntry."""
        return RecommendationEntry(
            id=row["id"],
            analysis_id=row["analysis_id"],
            category=row["category"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            created_at=row["created_at"],
            applied_at=row["applied_at"],
            notes=row["notes"],
        )
