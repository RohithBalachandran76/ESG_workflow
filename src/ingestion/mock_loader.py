"""Load company ESG data from the local mock JSON file."""

import json
from pathlib import Path
from typing import Any

MOCK_PATH = Path(__file__).parents[2] / "data" / "mock" / "companies.json"


def load_mock_companies() -> list[dict[str, Any]]:
    with open(MOCK_PATH) as f:
        return json.load(f)


def get_mock_company(ticker: str) -> dict[str, Any] | None:
    companies = load_mock_companies()
    ticker_upper = ticker.upper()
    return next((c for c in companies if c["ticker"] == ticker_upper), None)
