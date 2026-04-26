"""Tests for the data ingestion layer."""

import pytest

from src.ingestion.mock_loader import get_mock_company, load_mock_companies
from src.ingestion.news_fetcher import _simple_sentiment


def test_load_mock_companies_returns_list():
    companies = load_mock_companies()
    assert isinstance(companies, list)
    assert len(companies) > 0


def test_mock_company_has_required_fields():
    companies = load_mock_companies()
    for c in companies:
        assert "ticker" in c
        assert "name" in c
        assert "environmental" in c
        assert "social" in c
        assert "governance" in c


def test_get_mock_company_found():
    company = get_mock_company("AAPL")
    assert company is not None
    assert company["ticker"] == "AAPL"


def test_get_mock_company_case_insensitive():
    company = get_mock_company("aapl")
    assert company is not None


def test_get_mock_company_not_found():
    company = get_mock_company("DOESNOTEXIST999")
    assert company is None


def test_simple_sentiment_positive():
    score = _simple_sentiment("company achieves sustainable growth and innovation award")
    assert score > 0


def test_simple_sentiment_negative():
    score = _simple_sentiment("company faces lawsuit and fraud penalty violation")
    assert score < 0


def test_simple_sentiment_neutral():
    score = _simple_sentiment("company released quarterly report")
    assert score == 0.0
