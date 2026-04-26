"""FastAPI route definitions for the ESG Workflow API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.api.schemas import (
    AlertResponse,
    CompanyHistoryResponse,
    ESGScoreListResponse,
    ESGScoreResponse,
    HistoryPoint,
    PipelineRunResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from src.ingestion.pipeline import ingest_company
from src.scoring.database import get_session
from src.scoring.engine import score_from_dict
from src.scoring.models import CompanyESGRecord, ScoreHistory

logger = logging.getLogger(__name__)
router = APIRouter()


def _record_to_response(r: CompanyESGRecord, include_detail: bool = False) -> ESGScoreResponse:
    return ESGScoreResponse(
        ticker=r.ticker,
        company_name=r.company_name,
        sector=r.sector,
        country=r.country,
        environmental=r.environmental_score,
        social=r.social_score,
        governance=r.governance_score,
        total=r.total_score,
        rating=r.rating,
        alert=r.alert,
        detail=r.metric_detail if include_detail else None,
        updated_at=r.updated_at,
    )


@router.get("/companies", response_model=ESGScoreListResponse, tags=["ESG Scores"])
def list_companies(sector: str | None = None, rating: str | None = None):
    """List all companies with their latest ESG scores."""
    session = get_session()
    try:
        q = session.query(CompanyESGRecord)
        if sector:
            q = q.filter(CompanyESGRecord.sector.ilike(f"%{sector}%"))
        if rating:
            q = q.filter(CompanyESGRecord.rating == rating)
        records = q.order_by(CompanyESGRecord.total_score.desc()).all()
        return ESGScoreListResponse(
            count=len(records),
            companies=[_record_to_response(r) for r in records],
        )
    finally:
        session.close()


@router.get("/companies/{ticker}", response_model=ESGScoreResponse, tags=["ESG Scores"])
def get_company(ticker: str, detail: bool = False):
    """Get the latest ESG score for a specific company."""
    session = get_session()
    try:
        record = session.query(CompanyESGRecord).filter(
            CompanyESGRecord.ticker == ticker.upper()
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found. Run the pipeline first.")
        return _record_to_response(record, include_detail=detail)
    finally:
        session.close()


@router.get("/companies/{ticker}/history", response_model=CompanyHistoryResponse, tags=["ESG Scores"])
def get_company_history(ticker: str, limit: int = 30):
    """Return ESG score history for a company (most recent first)."""
    session = get_session()
    try:
        records = (
            session.query(ScoreHistory)
            .filter(ScoreHistory.ticker == ticker.upper())
            .order_by(ScoreHistory.recorded_at.desc())
            .limit(limit)
            .all()
        )
        return CompanyHistoryResponse(
            ticker=ticker.upper(),
            history=[
                HistoryPoint(
                    recorded_at=r.recorded_at,
                    total_score=r.total_score,
                    environmental_score=r.environmental_score,
                    social_score=r.social_score,
                    governance_score=r.governance_score,
                    rating=r.rating,
                )
                for r in records
            ],
        )
    finally:
        session.close()


@router.get("/alerts", response_model=list[AlertResponse], tags=["Alerts"])
def get_alerts(level: str | None = None):
    """Return all companies currently flagged with ESG alerts."""
    session = get_session()
    try:
        q = session.query(CompanyESGRecord).filter(CompanyESGRecord.alert.isnot(None))
        if level:
            q = q.filter(CompanyESGRecord.alert == level.upper())
        records = q.all()
        return [
            AlertResponse(
                ticker=r.ticker,
                company_name=r.company_name,
                total=r.total_score,
                alert=r.alert,
            )
            for r in records
        ]
    finally:
        session.close()


@router.post("/pipeline/run", response_model=PipelineRunResponse, tags=["Pipeline"])
def trigger_pipeline(tickers: list[str] | None = None, background_tasks: BackgroundTasks = None):
    """Trigger the ESG pipeline for all or specific companies."""
    from src.workflow.esg_flow import run_esg_pipeline
    result = run_esg_pipeline(tickers=tickers)
    return PipelineRunResponse(
        status=result["status"],
        companies_processed=result.get("companies_processed", 0),
        alerts=result.get("alerts", []),
    )


@router.post("/score/live", response_model=ESGScoreResponse, tags=["ESG Scores"])
def score_live(ticker: str):
    """Ingest and score a company in real-time without persisting."""
    company = ingest_company(ticker.upper())
    if not company:
        raise HTTPException(status_code=404, detail=f"No data found for ticker '{ticker}'")
    result = score_from_dict(company)
    return ESGScoreResponse(
        ticker=result.ticker,
        company_name=result.company_name,
        sector=company.get("sector"),
        country=company.get("country"),
        environmental=result.environmental.score,
        social=result.social.score,
        governance=result.governance.score,
        total=result.total,
        rating=result.rating,
        alert=result.alert,
    )


@router.post("/rag/query", response_model=RAGQueryResponse, tags=["RAG / AI"])
def rag_query(request: RAGQueryRequest):
    """Ask a natural language question about ESG scores using the RAG layer."""
    try:
        from src.rag.chain import answer_question
        answer, sources = answer_question(request.question, ticker=request.ticker)
        return RAGQueryResponse(question=request.question, answer=answer, sources=sources)
    except Exception as exc:
        logger.error("RAG query failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
