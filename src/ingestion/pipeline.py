"""Ingestion pipeline: resolves the best available data source per company
and returns a unified dict ready for the scoring engine.

Priority: Yahoo Finance (real) → mock data → skip
News sentiment enriches the social pillar in all cases.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ingestion.finance_fetcher import fetch_company_info
from src.ingestion.mock_loader import get_mock_company, load_mock_companies
from src.ingestion.news_fetcher import fetch_news_sentiment

logger = logging.getLogger(__name__)


def _enrich_with_sentiment(company: dict[str, Any]) -> dict[str, Any]:
    """Replace news_sentiment_score in social data with a live fetch when possible."""
    live_score = fetch_news_sentiment(company["name"])
    if live_score != 0.0:
        company["social"]["news_sentiment_score"] = live_score
    return company


def ingest_company(ticker: str) -> dict[str, Any] | None:
    """Return a fully resolved company dict for the scoring engine, or None."""
    mock = get_mock_company(ticker)
    if mock is None:
        logger.warning("No data found for ticker %s", ticker)
        return None

    # Try to enrich name/sector from Yahoo Finance
    live_info = fetch_company_info(ticker)
    if live_info:
        mock["name"] = live_info.get("name", mock["name"])
        mock["sector"] = live_info.get("sector", mock.get("sector", "Unknown"))
        mock["country"] = live_info.get("country", mock.get("country", "Unknown"))

    return _enrich_with_sentiment(mock)


def ingest_all() -> list[dict[str, Any]]:
    """Ingest and enrich all companies in the mock dataset."""
    companies = load_mock_companies()
    result = []
    for company in companies:
        enriched = _enrich_with_sentiment(company)
        result.append(enriched)
    logger.info("Ingested %d companies", len(result))
    return result
