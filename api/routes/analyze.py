"""Analyze route — POST /api/analyze"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import AnalyzeRequest
from devkit.tasks.full_audit import create_full_audit_task

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("")
async def run_analyze(req: AnalyzeRequest):
    """Run full analysis pipeline on an OpenCode config."""
    config_path = None

    # Only accept inline content (no filesystem path access)
    if req.config_content:
        tmp = Path(tempfile.gettempdir()) / "devkit-inline-config.json"
        tmp.write_text(req.config_content, encoding="utf-8")
        config_path = tmp
    elif req.config_path:
        # Legacy support: still accept path but only from upload temp dir
        tmp = Path(req.config_path)
        if tmp.exists():
            config_path = tmp

    if not config_path:
        raise HTTPException(
            status_code=400,
            detail="No config provided. Paste JSON or upload a file.",
        )

    try:
        report = create_full_audit_task(str(config_path))
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
