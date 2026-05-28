"""Migration route — POST /api/migrate"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import MigrateRequest
from api.utils import resolve_config_from_request
from devkit.tasks.migration_assistant import run_migration_analysis

router = APIRouter(prefix="/migrate", tags=["migrate"])


@router.post("")
async def run_migrate(req: MigrateRequest):
    """Run migration analysis on an OpenCode config."""
    config_path = resolve_config_from_request(req.config_path, req.config_content)
    if not config_path:
        raise HTTPException(
            status_code=400,
            detail="No OpenCode config found. Specify config_path, paste JSON content, or place opencode.json in .opencode/",
        )

    try:
        result = run_migration_analysis(str(config_path))
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration analysis failed: {str(e)}")
