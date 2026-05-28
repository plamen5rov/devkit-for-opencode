"""Analyze route — POST /api/analyze"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import AnalyzeRequest
from api.utils import resolve_config_path
from devkit.tasks.full_audit import create_full_audit_task

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("")
async def run_analyze(req: AnalyzeRequest):
    """Run full analysis pipeline on an OpenCode config."""
    config_path = resolve_config_path(req.config_path)
    if not config_path:
        raise HTTPException(
            status_code=400,
            detail="No OpenCode config found. Specify config_path or place opencode.json in .opencode/",
        )

    try:
        report = create_full_audit_task(str(config_path))
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
