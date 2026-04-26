"""Build LangChain Documents from the ESG database for RAG indexing."""

from __future__ import annotations

from langchain_core.documents import Document

from src.scoring.database import get_engine, get_session
from src.scoring.models import CompanyESGRecord


def build_company_documents() -> list[Document]:
    """Convert all ESG records in the DB into LangChain Documents."""
    get_engine()
    session = get_session()
    try:
        records = session.query(CompanyESGRecord).all()
        if not records:
            return _mock_documents()
        return [_record_to_doc(r) for r in records]
    finally:
        session.close()


def _record_to_doc(r: CompanyESGRecord) -> Document:
    detail = r.metric_detail or {}
    lines = [
        f"Company: {r.company_name} (Ticker: {r.ticker})",
        f"Sector: {r.sector or 'Unknown'}, Country: {r.country or 'Unknown'}",
        f"ESG Total Score: {r.total_score:.1f} — Rating: {r.rating}",
        f"Environmental Score: {r.environmental_score:.1f}",
        f"Social Score: {r.social_score:.1f}",
        f"Governance Score: {r.governance_score:.1f}",
    ]
    if r.alert:
        lines.append(f"Alert Level: {r.alert}")

    for pillar, metrics in detail.items():
        lines.append(f"\n{pillar.title()} Metrics:")
        for metric, values in metrics.items():
            lines.append(f"  - {metric}: raw={values['raw']}, score={values['score']}")

    return Document(
        page_content="\n".join(lines),
        metadata={"ticker": r.ticker, "company": r.company_name, "rating": r.rating},
    )


def _mock_documents() -> list[Document]:
    """Fallback documents when no DB records exist yet."""
    import json
    from pathlib import Path
    mock_path = Path(__file__).parents[2] / "data" / "mock" / "companies.json"
    companies = json.loads(mock_path.read_text())
    docs = []
    for c in companies:
        lines = [
            f"Company: {c['name']} (Ticker: {c['ticker']})",
            f"Sector: {c.get('sector', 'Unknown')}, Country: {c.get('country', 'Unknown')}",
        ]
        for pillar in ("environmental", "social", "governance"):
            lines.append(f"\n{pillar.title()} data:")
            for k, v in c.get(pillar, {}).items():
                lines.append(f"  - {k}: {v}")
        docs.append(Document(
            page_content="\n".join(lines),
            metadata={"ticker": c["ticker"], "company": c["name"]},
        ))
    return docs
