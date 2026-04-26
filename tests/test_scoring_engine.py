"""Unit tests for the ESG scoring engine."""

import pytest

from src.scoring.engine import ESGScore, score_company, score_from_dict


MOCK_ENV = {
    "carbon_intensity": 85,
    "renewable_energy_pct": 100,
    "water_usage_intensity": 120,
    "waste_recycling_rate": 77,
    "environmental_fines": 0,
}
MOCK_SOC = {
    "employee_safety_rate": 0.4,
    "gender_pay_gap": 3,
    "employee_turnover": 9,
    "community_investment_pct": 1.2,
    "news_sentiment_score": 0.35,
}
MOCK_GOV = {
    "board_independence": 73,
    "audit_committee_score": 88,
    "ceo_pay_ratio": 220,
    "corruption_incidents": 0,
    "transparency_score": 85,
}


def test_score_company_returns_esg_score():
    result = score_company("TEST", "Test Corp", MOCK_ENV, MOCK_SOC, MOCK_GOV)
    assert isinstance(result, ESGScore)
    assert result.ticker == "TEST"


def test_score_ranges():
    result = score_company("TEST", "Test Corp", MOCK_ENV, MOCK_SOC, MOCK_GOV)
    assert 0 <= result.total <= 100
    assert 0 <= result.environmental.score <= 100
    assert 0 <= result.social.score <= 100
    assert 0 <= result.governance.score <= 100


def test_excellent_company_rating():
    result = score_company("TEST", "Test Corp", MOCK_ENV, MOCK_SOC, MOCK_GOV)
    assert result.rating in ("Excellent", "Good")
    assert result.alert is None


def test_poor_company_rating():
    poor_env = {k: v * 5 if k != "renewable_energy_pct" else 2 for k, v in MOCK_ENV.items()}
    poor_soc = {k: v * 3 if k not in ("news_sentiment_score", "community_investment_pct") else -0.5 for k, v in MOCK_SOC.items()}
    poor_gov = {k: v // 3 if k not in ("corruption_incidents",) else 5 for k, v in MOCK_GOV.items()}
    result = score_company("BAD", "Bad Corp", poor_env, poor_soc, poor_gov)
    assert result.rating in ("Poor", "Fair")


def test_critical_alert_triggered():
    """Score a company with very bad metrics and expect CRITICAL or WATCH alert."""
    bad_env = {"carbon_intensity": 600, "renewable_energy_pct": 1, "water_usage_intensity": 1200, "waste_recycling_rate": 5, "environmental_fines": 10}
    bad_soc = {"employee_safety_rate": 6, "gender_pay_gap": 30, "employee_turnover": 40, "community_investment_pct": 0, "news_sentiment_score": -0.8}
    bad_gov = {"board_independence": 10, "audit_committee_score": 15, "ceo_pay_ratio": 600, "corruption_incidents": 5, "transparency_score": 10}
    result = score_company("WORST", "Worst Corp", bad_env, bad_soc, bad_gov)
    assert result.alert in ("CRITICAL", "WATCH")


def test_score_from_dict():
    company = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "environmental": MOCK_ENV,
        "social": MOCK_SOC,
        "governance": MOCK_GOV,
    }
    result = score_from_dict(company)
    assert result.ticker == "AAPL"
    assert result.company_name == "Apple Inc."


def test_missing_metric_graceful():
    """Missing metrics should not crash the engine."""
    partial_env = {"carbon_intensity": 100}
    result = score_company("PARTIAL", "Partial Corp", partial_env, MOCK_SOC, MOCK_GOV)
    assert isinstance(result, ESGScore)
    assert result.environmental.score >= 0
