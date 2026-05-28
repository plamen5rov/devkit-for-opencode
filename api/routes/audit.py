"""Audit route — POST /api/audit"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import AuditRequest
from api.utils import resolve_config_from_request
from devkit.tasks.security_scan import run_security_scan

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("")
async def run_audit(req: AuditRequest):
    """Run security audit on an OpenCode config."""
    config_path = resolve_config_from_request(req.config_path, req.config_content)
    if not config_path:
        raise HTTPException(
            status_code=400,
            detail="No OpenCode config found. Specify config_path, paste JSON content, or place opencode.json in .opencode/",
        )

    try:
        result = run_security_scan(str(config_path))
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")
