"""Graph route — POST /api/graph"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import GraphRequest
from devkit.tools.config_diff import _parse_jsonc
from devkit.tools.config_reader import read_config
from devkit.tools.graph_builder import build_config_graph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("")
async def run_graph(req: GraphRequest):
    try:
        if req.config_content:
            config_data, parse_err = _parse_jsonc(req.config_content)
            if parse_err:
                raise HTTPException(status_code=400, detail=f"Failed to parse config: {parse_err}")
        elif req.config_path:
            result = read_config(req.config_path)
            if not result.success:
                raise HTTPException(status_code=400, detail="; ".join(result.errors))
            config_data = result.config
        else:
            raise HTTPException(status_code=400, detail="Provide config_content or config_path")

        label = req.label or "opencode.json"
        graph = build_config_graph(config_data, config_label=label)
        return graph.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
