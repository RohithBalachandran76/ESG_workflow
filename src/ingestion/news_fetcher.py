"""Fetch news headlines for a company and compute an aggregate sentiment score.

Uses NewsAPI (free tier) if NEWS_API_KEY is set; otherwise returns a neutral
sentiment of 0.0 so the pipeline continues without an API key.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2/everything"


def _simple_sentiment(text: str) -> float:
    """Naïve keyword-based sentiment: returns value in [-1, 1]."""
    positive = {"profit", "growth", "green", "sustainable", "award", "record", "innovation", "partnership"}
    negative = {"scandal", "fine", "lawsuit", "fraud", "leak", "spill", "loss", "penalty", "violation", "recall"}
    words = set(text.lower().split())
    pos = len(words & positive)
    neg = len(words & negative)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def fetch_news_sentiment(company_name: str, days: int = 30) -> float:
    """Return an aggregate sentiment score in [-1, 1] for a company's recent news."""
    api_key = os.getenv("NEWS_API_KEY", "")
    if not api_key:
        logger.debug("NEWS_API_KEY not set — returning neutral sentiment")
        return 0.0

    try:
        params: dict[str, Any] = {
            "q": company_name,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 20,
            "apiKey": api_key,
        }
        resp = requests.get(NEWSAPI_BASE, params=params, timeout=10)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        if not articles:
            return 0.0
        scores = [
            _simple_sentiment(
                (a.get("title") or "") + " " + (a.get("description") or "")
            )
            for a in articles
        ]
        return round(sum(scores) / len(scores), 3)
    except Exception as exc:
        logger.warning("NewsAPI request failed for %s: %s", company_name, exc)
        return 0.0
