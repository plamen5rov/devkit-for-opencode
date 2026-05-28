"""History routes — GET /api/history, DELETE /api/history/all, GET /api/history/{id}, GET /api/history/trend"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas import HistoryListResponse, TrendRecord, TrendResponse
from devkit.memory.history import AnalysisHistoryStore

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "devkit" / "history.db"

router = APIRouter(prefix="/history", tags=["history"])


def _get_store() -> AnalysisHistoryStore:
    if DEFAULT_DB_PATH.exists():
        return AnalysisHistoryStore(DEFAULT_DB_PATH)
    return None


@router.get("")
async def list_history(
    config_path: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
):
    """List analysis history records."""
    store = _get_store()
    if not store:
        return {"records": [], "total": 0}

    if config_path:
        records = store.query_by_config_path(config_path, limit=limit)
    else:
        records = store.get_latest()
        records = [records] if records else []
        records = records[:limit]

    return {
        "records": [r.to_dict() for r in records],
        "total": len(records),
    }


@router.get("/trend")
async def get_trend(
    config_path: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Get health score trend over time."""
    store = _get_store()
    if not store:
        return {"config_path": config_path, "data": []}

    trend_data = store.get_trend(config_path, limit=limit)
    return {
        "config_path": config_path,
        "data": [TrendRecord(**t) for t in trend_data],
    }


@router.delete("/all")
async def clear_history():
    """Clear all analysis history records."""
    store = _get_store()
    if not store:
        return {"deleted": 0}
    count = store.clear_all()
    return {"deleted": count}


@router.get("/{record_id}")
async def get_history_record(record_id: int):
    """Get a single analysis record by ID."""
    store = _get_store()
    if not store:
        raise HTTPException(status_code=404, detail="No history database found")

    record = store.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")

    return record.to_dict()
