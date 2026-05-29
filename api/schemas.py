"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Request schemas ---

class AnalyzeRequest(BaseModel):
    config_content: str


class AuditRequest(BaseModel):
    config_path: Optional[str] = None
    config_content: Optional[str] = None
    verbose: bool = False


class ScoreRequest(BaseModel):
    config_path: Optional[str] = None
    config_content: Optional[str] = None
    detailed: bool = False
    verbose: bool = False


class MigrateRequest(BaseModel):
    config_path: Optional[str] = None
    config_content: Optional[str] = None
    verbose: bool = False


class ConfigValidateRequest(BaseModel):
    config_path: Optional[str] = None


class RecommendationUpdateRequest(BaseModel):
    status: str = Field(pattern="^(open|applied|dismissed)$")
    notes: Optional[str] = None


# --- Response schemas ---

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    python_version: str


class HistoryListResponse(BaseModel):
    records: list[dict[str, Any]]
    total: int


class TrendRecord(BaseModel):
    timestamp: str
    health_score: int
    risk_score: int


class TrendResponse(BaseModel):
    config_path: Optional[str] = None
    data: list[TrendRecord]


class RecommendationItem(BaseModel):
    id: int
    analysis_id: int
    category: str
    title: str
    description: str
    status: str
    created_at: str
    applied_at: Optional[str] = None
    notes: Optional[str] = None


class RecommendationListResponse(BaseModel):
    recommendations: list[RecommendationItem]
    summary: dict[str, int]


class RecommendationSummaryResponse(BaseModel):
    total: int
    open: int
    applied: int
    dismissed: int


class DiffRequest(BaseModel):
    from_content: Optional[str] = None
    to_content: Optional[str] = None
    from_path: Optional[str] = None
    to_path: Optional[str] = None


class DiffCompareRequest(BaseModel):
    config_path: Optional[str] = None
    config_content: Optional[str] = None
    record_id: int
    db_path: Optional[str] = None


class GraphRequest(BaseModel):
    config_content: Optional[str] = None
    config_path: Optional[str] = None
    label: Optional[str] = None
