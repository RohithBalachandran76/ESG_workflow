"""Integration tests for the FastAPI endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.scoring.database import get_engine

MOCK_PIPELINE_RESULT = {
    "status": "success",
    "companies_processed": 5,
    "alerts": [],
    "scores": [
        {"ticker": "AAPL", "name": "Apple Inc.", "total": 78.5, "rating": "Excellent", "e": 80.0, "s": 75.0, "g": 82.0},
    ],
}


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temp SQLite DB for tests."""
    db_path = tmp_path / "test_esg.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    import src.scoring.database as db_module
    db_module._engine = None
    db_module._SessionLocal = None
    get_engine(f"sqlite:///{db_path}")
    yield
    db_module._engine = None
    db_module._SessionLocal = None


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ESG" in resp.json()["service"]


def test_list_companies_empty(client):
    resp = client.get("/api/v1/companies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["companies"] == []


def test_get_company_not_found(client):
    resp = client.get("/api/v1/companies/UNKNOWN")
    assert resp.status_code == 404


def test_alerts_empty(client):
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_score_live_known_ticker(client):
    resp = client.post("/api/v1/score/live?ticker=AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert 0 <= data["total"] <= 100
    assert data["rating"] in ("Excellent", "Good", "Fair", "Poor")


def test_score_live_unknown_ticker(client):
    resp = client.post("/api/v1/score/live?ticker=UNKNOWN999")
    assert resp.status_code == 404


def test_pipeline_run(client):
    with patch("src.workflow.esg_flow.run_esg_pipeline", return_value=MOCK_PIPELINE_RESULT):
        resp = client.post("/api/v1/pipeline/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["companies_processed"] > 0


def test_list_companies_after_pipeline(client):
    with patch("src.workflow.esg_flow.run_esg_pipeline", return_value=MOCK_PIPELINE_RESULT):
        client.post("/api/v1/pipeline/run")
    # pipeline mock doesn't actually write to DB — verify endpoint itself responds correctly
    resp = client.get("/api/v1/companies")
    assert resp.status_code == 200
    assert "companies" in resp.json()
