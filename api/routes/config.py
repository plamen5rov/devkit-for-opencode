"""Config routes — POST /api/config/upload, POST /api/config/validate"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from api.schemas import ConfigValidateRequest
from api.utils import validate_config_content

router = APIRouter(prefix="/config", tags=["config"])


@router.post("/upload")
async def upload_config(file: UploadFile):
    """Upload an opencode.json file and validate it."""
    if not file.filename or not file.filename.endswith((".json", ".jsonc")):
        raise HTTPException(status_code=400, detail="File must be .json or .jsonc")

    content = await file.read()
    raw = content.decode("utf-8")
    result = validate_config_content(raw)

    return {
        "filename": file.filename,
        "valid": result["valid"],
        "errors": result["errors"],
        "config": result["config"],
    }


@router.post("/validate")
async def validate_config(req: ConfigValidateRequest):
    """Validate a config file by path."""
    if not req.config_path:
        raise HTTPException(status_code=400, detail="config_path is required")

    path = Path(req.config_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.config_path}")

    raw = path.read_text(encoding="utf-8")
    result = validate_config_content(raw)

    return {
        "path": req.config_path,
        "valid": result["valid"],
        "errors": result["errors"],
        "config": result["config"],
    }
