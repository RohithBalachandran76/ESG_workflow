"""Fetch company financial data from Yahoo Finance via yfinance.

Falls back gracefully to mock data if the ticker is not found or the
network request fails — ensuring the pipeline always runs cleanly.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fetch_company_info(ticker: str) -> dict[str, Any] | None:
    """Return basic company info dict from Yahoo Finance, or None on failure."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        if not info or info.get("regularMarketPrice") is None:
            return None
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "country": info.get("country", "Unknown"),
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue"),
            "employees": info.get("fullTimeEmployees"),
        }
    except Exception as exc:
        logger.warning("Yahoo Finance fetch failed for %s: %s", ticker, exc)
        return None


def fetch_esg_data(ticker: str) -> dict[str, Any] | None:
    """Return ESG sustainability data from Yahoo Finance where available."""
    try:
        import yfinance as yf
        sustainability = yf.Ticker(ticker).sustainability
        if sustainability is None or sustainability.empty:
            return None
        data = sustainability.T.to_dict(orient="records")
        return data[0] if data else None
    except Exception as exc:
        logger.warning("ESG fetch failed for %s: %s", ticker, exc)
        return None
