"""Recommendation routes — GET /api/recommendations, PATCH /api/recommendations/{id}"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas import (
    RecommendationItem,
    RecommendationListResponse,
    RecommendationSummaryResponse,
    RecommendationUpdateRequest,
)
from devkit.memory.recommendations import RecommendationTracker

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "devkit" / "history.db"

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _get_tracker() -> RecommendationTracker:
    if DEFAULT_DB_PATH.exists():
        return RecommendationTracker(DEFAULT_DB_PATH)
    return None


@router.get("")
async def list_recommendations(
    status: Optional[str] = Query(None, pattern="^(open|applied|dismissed)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """List recommendations, optionally filtered by status."""
    tracker = _get_tracker()
    if not tracker:
        return {"recommendations": [], "summary": {"total": 0, "open": 0, "applied": 0, "dismissed": 0}}

    if status:
        entries = tracker.get_by_status(status, limit=limit)
    else:
        entries = []
        for s in ["open", "applied", "dismissed"]:
            entries.extend(tracker.get_by_status(s, limit=limit))

    summary = tracker.get_summary()

    return {
        "recommendations": [RecommendationItem(**e.to_dict()) for e in entries],
        "summary": summary,
    }


@router.get("/summary")
async def get_recommendation_summary():
    """Get recommendation summary counts."""
    tracker = _get_tracker()
    if not tracker:
        return {"total": 0, "open": 0, "applied": 0, "dismissed": 0}

    return tracker.get_summary()


@router.patch("/{recommendation_id}")
async def update_recommendation(recommendation_id: int, req: RecommendationUpdateRequest):
    """Update a recommendation's status."""
    tracker = _get_tracker()
    if not tracker:
        raise HTTPException(status_code=404, detail="No recommendation database found")

    entry = tracker.get_recommendation(recommendation_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")

    success = tracker.update_status(recommendation_id, req.status, req.notes)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update recommendation")

    updated = tracker.get_recommendation(recommendation_id)
    return updated.to_dict()
