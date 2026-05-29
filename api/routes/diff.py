"""Diff route — POST /api/diff, POST /api/diff/compare"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import DiffRequest, DiffCompareRequest
from api.utils import resolve_config_from_request
from devkit.tools.config_diff import (
    diff_config_files,
    diff_config_strings,
    diff_config_against_history,
)

router = APIRouter(prefix="/diff", tags=["diff"])


@router.post("")
async def run_diff(req: DiffRequest):
    """Compare two OpenCode configs."""
    if req.from_content and req.to_content:
        try:
            result = diff_config_strings(
                from_json=req.from_content,
                to_json=req.to_content,
                from_label="from",
                to_label="to",
            )
            return result.to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Diff failed: {str(e)}")

    if req.from_path and req.to_path:
        try:
            result = diff_config_files(
                from_path=req.from_path,
                to_path=req.to_path,
            )
            return result.to_dict()
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Diff failed: {str(e)}")

    raise HTTPException(
        status_code=400,
        detail="Provide from_content+to_content or from_path+to_path",
    )


@router.post("/compare")
async def run_diff_compare(req: DiffCompareRequest):
    """Compare a config against a historical analysis record."""
    config_path = resolve_config_from_request(req.config_path, req.config_content)
    if not config_path:
        raise HTTPException(
            status_code=400,
            detail="No config provided. Specify config_content or config_path.",
        )

    config_json = config_path.read_text(encoding="utf-8")

    try:
        result = diff_config_against_history(
            config_json=config_json,
            record_id=req.record_id,
            db_path=req.db_path,
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis record #{req.record_id} not found or has no raw report data",
            )
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diff comparison failed: {str(e)}")
