"""Prefect flow: orchestrates the full ESG pipeline.

Schedule: runs daily (configurable).
Tasks:
  1. ingest_task       — fetch & enrich company data
  2. score_task        — compute ESG scores
  3. persist_task      — upsert scores into SQLite
  4. alert_task        — log & surface CRITICAL/WATCH alerts
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from prefect import flow, task, get_run_logger

from src.ingestion.pipeline import ingest_all, ingest_company
from src.scoring.database import get_session
from src.scoring.engine import ESGScore, score_from_dict
from src.scoring.models import CompanyESGRecord, ScoreHistory

logger = logging.getLogger(__name__)


@task(name="ingest-companies", retries=2, retry_delay_seconds=30)
def ingest_task(tickers: list[str] | None = None) -> list[dict[str, Any]]:
    log = get_run_logger()
    if tickers:
        companies = [c for t in tickers if (c := ingest_company(t)) is not None]
    else:
        companies = ingest_all()
    log.info("Ingested %d companies", len(companies))
    return companies


@task(name="score-companies")
def score_task(companies: list[dict[str, Any]]) -> list[ESGScore]:
    log = get_run_logger()
    scores = [score_from_dict(c) for c in companies]
    log.info("Scored %d companies", len(scores))
    return scores


@task(name="persist-scores")
def persist_task(scores: list[ESGScore], companies_meta: list[dict[str, Any]]) -> None:
    log = get_run_logger()
    meta_by_ticker = {c["ticker"]: c for c in companies_meta}
    session = get_session()
    try:
        for s in scores:
            meta = meta_by_ticker.get(s.ticker, {})
            detail = {
                "environmental": {m.name: {"raw": m.raw_value, "score": m.normalised} for m in s.environmental.metrics},
                "social": {m.name: {"raw": m.raw_value, "score": m.normalised} for m in s.social.metrics},
                "governance": {m.name: {"raw": m.raw_value, "score": m.normalised} for m in s.governance.metrics},
            }
            record = CompanyESGRecord(
                ticker=s.ticker,
                company_name=s.company_name,
                sector=meta.get("sector"),
                country=meta.get("country"),
                environmental_score=s.environmental.score,
                social_score=s.social.score,
                governance_score=s.governance.score,
                total_score=s.total,
                rating=s.rating,
                alert=s.alert,
                metric_detail=detail,
                updated_at=datetime.now(timezone.utc),
            )
            session.merge(record)

            history = ScoreHistory(
                id=str(uuid.uuid4()),
                ticker=s.ticker,
                total_score=s.total,
                environmental_score=s.environmental.score,
                social_score=s.social.score,
                governance_score=s.governance.score,
                rating=s.rating,
                recorded_at=datetime.now(timezone.utc),
            )
            session.add(history)

        session.commit()
        log.info("Persisted %d records to database", len(scores))
    finally:
        session.close()


@task(name="check-alerts")
def alert_task(scores: list[ESGScore]) -> list[dict]:
    log = get_run_logger()
    alerts = [
        {"ticker": s.ticker, "company": s.company_name, "total": s.total, "alert": s.alert}
        for s in scores
        if s.alert is not None
    ]
    for a in alerts:
        if a["alert"] == "CRITICAL":
            log.error("CRITICAL ESG ALERT: %s (%s) — score %.1f", a["company"], a["ticker"], a["total"])
        else:
            log.warning("WATCH ESG ALERT: %s (%s) — score %.1f", a["company"], a["ticker"], a["total"])
    if not alerts:
        log.info("No ESG alerts triggered")
    return alerts


@flow(name="esg-daily-pipeline", log_prints=True)
def run_esg_pipeline(tickers: list[str] | None = None) -> dict[str, Any]:
    """Full ESG pipeline: ingest → score → persist → alert."""
    companies = ingest_task(tickers=tickers)
    if not companies:
        return {"status": "no_data", "scores": [], "alerts": []}

    scores = score_task(companies)
    persist_task(scores, companies)
    alerts = alert_task(scores)

    summary = {
        "status": "success",
        "companies_processed": len(scores),
        "alerts": alerts,
        "scores": [
            {
                "ticker": s.ticker,
                "name": s.company_name,
                "total": s.total,
                "rating": s.rating,
                "e": s.environmental.score,
                "s": s.social.score,
                "g": s.governance.score,
            }
            for s in scores
        ],
    }
    return summary


if __name__ == "__main__":
    result = run_esg_pipeline()
    import json
    print(json.dumps(result, indent=2))
