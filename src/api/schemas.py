"""Pydantic response schemas for the ESG API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MetricDetail(BaseModel):
    raw: float
    score: float


class PillarDetail(BaseModel):
    score: float
    metrics: dict[str, MetricDetail]


class ESGScoreResponse(BaseModel):
    ticker: str
    company_name: str
    sector: str | None
    country: str | None
    environmental: float
    social: float
    governance: float
    total: float
    rating: str
    alert: str | None
    detail: dict[str, Any] | None = None
    updated_at: datetime | None = None


class ESGScoreListResponse(BaseModel):
    count: int
    companies: list[ESGScoreResponse]


class AlertResponse(BaseModel):
    ticker: str
    company_name: str
    total: float
    alert: str


class PipelineRunResponse(BaseModel):
    status: str
    companies_processed: int
    alerts: list[dict]


class RAGQueryRequest(BaseModel):
    question: str
    ticker: str | None = None


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = []


class HistoryPoint(BaseModel):
    recorded_at: datetime
    total_score: float
    environmental_score: float
    social_score: float
    governance_score: float
    rating: str


class CompanyHistoryResponse(BaseModel):
    ticker: str
    history: list[HistoryPoint]
