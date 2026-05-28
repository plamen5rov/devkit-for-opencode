"""Analyze route — POST /api/analyze"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import AnalyzeRequest
from devkit.memory.history import AnalysisHistoryStore
from devkit.memory.recommendations import RecommendationTracker
from devkit.tasks.full_audit import create_full_audit_task

router = APIRouter(prefix="/analyze", tags=["analyze"])

HISTORY_DB_PATH = Path.home() / ".local" / "share" / "devkit" / "history.db"


@router.post("")
async def run_analyze(req: AnalyzeRequest):
    """Run full analysis pipeline on an OpenCode config."""
    config_path = None
    config_path_str = "inline-config"

    if req.config_content:
        tmp = Path(tempfile.gettempdir()) / "devkit-inline-config.json"
        tmp.write_text(req.config_content, encoding="utf-8")
        config_path = tmp
        config_path_str = str(tmp)
    elif req.config_path:
        tmp = Path(req.config_path)
        if tmp.exists():
            config_path = tmp
            config_path_str = str(tmp)

    if not config_path:
        raise HTTPException(
            status_code=400,
            detail="No config provided. Paste JSON or upload a file.",
        )

    try:
        report = create_full_audit_task(str(config_path))
        result = report.to_dict()

        summary = result.get("orchestrator", {}).get("summary", {})
        audit = result.get("audit", {})
        optimization = result.get("optimization", {})

        try:
            store = AnalysisHistoryStore(HISTORY_DB_PATH)
            record_id = store.record_analysis(
                config_path=config_path_str,
                health_score=summary.get("health_score", 0),
                risk_score=summary.get("risk_score", audit.get("risk_score", 0)),
                issue_count=summary.get("total_issues", len(audit.get("findings", []))),
                warning_count=summary.get("total_warnings", 0),
                mcp_token_estimate=summary.get("mcp_token_estimate", 0),
                findings=audit.get("findings", []),
                recommendations=optimization.get("recommendations", []),
                raw_report=json.dumps(result),
            )
            recs = optimization.get("recommendations", [])
            if record_id > 0 and recs:
                rec_tracker = RecommendationTracker(HISTORY_DB_PATH)
                rec_tracker.add_recommendations(
                    analysis_id=record_id,
                    recommendations=recs,
                )
        except Exception:
            pass

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
