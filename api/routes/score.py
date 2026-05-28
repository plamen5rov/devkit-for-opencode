"""Score route — POST /api/score"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import ScoreRequest
from api.utils import resolve_config_from_request
from devkit.agents.orchestrator import run_orchestration

router = APIRouter(prefix="/score", tags=["score"])


@router.post("")
async def get_score(req: ScoreRequest):
    """Calculate health score for an OpenCode config."""
    config_path = resolve_config_from_request(req.config_path, req.config_content)
    if not config_path:
        raise HTTPException(
            status_code=400,
            detail="No OpenCode config found. Specify config_path, paste JSON content, or place opencode.json in .opencode/",
        )

    try:
        result = run_orchestration(str(config_path))
        score = result.summary.get("health_score", 0)

        response = {
            "health_score": score,
            "summary": result.summary,
        }

        if req.detailed:
            response["breakdown"] = {
                "issues": result.summary.get("total_issues", 0),
                "warnings": result.summary.get("total_warnings", 0),
                "agents": result.summary.get("agent_count", 0),
                "skills": result.summary.get("skill_count", 0),
                "mcp_servers": result.summary.get("mcp_count", 0),
                "commands": result.summary.get("command_count", 0),
                "mcp_token_estimate": result.summary.get("mcp_token_estimate", 0),
            }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Score calculation failed: {str(e)}")
