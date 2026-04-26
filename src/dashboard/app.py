"""Streamlit ESG Dashboard.

Run with:
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parents[2]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.ingestion.pipeline import ingest_all
from src.scoring.database import get_engine, get_session
from src.scoring.engine import score_from_dict
from src.scoring.models import CompanyESGRecord, ScoreHistory
from src.workflow.esg_flow import run_esg_pipeline

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ESG Workflow Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

RATING_COLOR = {
    "Excellent": "#2ecc71",
    "Good": "#3498db",
    "Fair": "#f39c12",
    "Poor": "#e74c3c",
}
ALERT_COLOR = {"CRITICAL": "#e74c3c", "WATCH": "#f39c12"}


# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_scores() -> list[dict]:
    get_engine()
    session = get_session()
    try:
        records = session.query(CompanyESGRecord).order_by(CompanyESGRecord.total_score.desc()).all()
        return [
            {
                "ticker": r.ticker,
                "company": r.company_name,
                "sector": r.sector or "—",
                "country": r.country or "—",
                "E": r.environmental_score,
                "S": r.social_score,
                "G": r.governance_score,
                "Total": r.total_score,
                "Rating": r.rating,
                "Alert": r.alert or "—",
                "detail": r.metric_detail or {},
            }
            for r in records
        ]
    finally:
        session.close()


def load_history(ticker: str) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(ScoreHistory)
            .filter(ScoreHistory.ticker == ticker)
            .order_by(ScoreHistory.recorded_at.asc())
            .all()
        )
        return [
            {
                "Date": r.recorded_at,
                "Total": r.total_score,
                "E": r.environmental_score,
                "S": r.social_score,
                "G": r.governance_score,
            }
            for r in records
        ]
    finally:
        session.close()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌿 ESG Workflow")
    st.caption("CSRD/ESRS-aligned scoring engine")
    st.divider()

    page = st.radio(
        "Navigate",
        ["Overview", "Company Detail", "Alerts", "AI Assistant", "Run Pipeline"],
        index=0,
    )
    st.divider()
    st.caption("Data refreshes every 5 min. Pipeline runs persist to SQLite.")


# ── Overview ──────────────────────────────────────────────────────────────────
if page == "Overview":
    st.title("ESG Scores — Overview")

    scores = load_scores()
    if not scores:
        st.warning("No data yet. Go to **Run Pipeline** to load scores.")
        st.stop()

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Companies Tracked", len(scores))
    col2.metric("Avg ESG Score", f"{sum(s['Total'] for s in scores) / len(scores):.1f}")
    alerts = [s for s in scores if s["Alert"] != "—"]
    col3.metric("Active Alerts", len(alerts), delta=None)
    excellents = [s for s in scores if s["Rating"] == "Excellent"]
    col4.metric("Excellent Rated", len(excellents))

    st.divider()

    # Bar chart — total scores
    import pandas as pd
    df = pd.DataFrame(scores)

    fig_bar = px.bar(
        df.sort_values("Total"),
        x="Total",
        y="company",
        orientation="h",
        color="Rating",
        color_discrete_map=RATING_COLOR,
        title="ESG Total Score by Company",
        labels={"company": "", "Total": "ESG Score (0-100)"},
        height=350,
    )
    fig_bar.update_layout(legend_title_text="Rating")
    st.plotly_chart(fig_bar, use_container_width=True)

    # Pillar breakdown radar
    st.subheader("E / S / G Pillar Breakdown")
    fig_radar = go.Figure()
    categories = ["Environmental", "Social", "Governance"]
    for s in scores:
        fig_radar.add_trace(go.Scatterpolar(
            r=[s["E"], s["S"], s["G"]],
            theta=categories,
            fill="toself",
            name=s["ticker"],
        ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=400)
    st.plotly_chart(fig_radar, use_container_width=True)

    # Table
    st.subheader("Scorecard Table")
    display_cols = ["ticker", "company", "sector", "country", "E", "S", "G", "Total", "Rating", "Alert"]
    st.dataframe(
        df[display_cols].style.background_gradient(subset=["Total", "E", "S", "G"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True,
        hide_index=True,
    )


# ── Company Detail ─────────────────────────────────────────────────────────────
elif page == "Company Detail":
    st.title("Company Deep-Dive")
    scores = load_scores()
    if not scores:
        st.warning("No data yet. Run the pipeline first.")
        st.stop()

    import pandas as pd
    tickers = [s["ticker"] for s in scores]
    selected = st.selectbox("Select Company", tickers)
    company_data = next(s for s in scores if s["ticker"] == selected)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total ESG Score", f"{company_data['Total']:.1f}", company_data["Rating"])
    col2.metric("Environmental", f"{company_data['E']:.1f}")
    col3.metric("Social", f"{company_data['S']:.1f}")
    col4.metric("Governance", f"{company_data['G']:.1f}")

    if company_data["Alert"] != "—":
        color = ALERT_COLOR.get(company_data["Alert"], "#888")
        st.markdown(
            f'<div style="background:{color};color:white;padding:10px;border-radius:6px;font-weight:bold;">'
            f'⚠ {company_data["Alert"]} ALERT — ESG score {company_data["Total"]:.1f}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Metric detail table
    detail = company_data["detail"]
    if detail:
        for pillar, metrics in detail.items():
            st.subheader(f"{pillar.title()} Metrics")
            rows = [{"Metric": k, "Raw Value": v["raw"], "Score (0-100)": v["score"]} for k, v in metrics.items()]
            df_m = pd.DataFrame(rows)
            st.dataframe(
                df_m.style.background_gradient(subset=["Score (0-100)"], cmap="RdYlGn", vmin=0, vmax=100),
                use_container_width=True,
                hide_index=True,
            )

    # History chart
    st.divider()
    st.subheader("Score History")
    history = load_history(selected)
    if history:
        df_h = pd.DataFrame(history)
        fig_h = px.line(df_h, x="Date", y=["Total", "E", "S", "G"],
                        title=f"{selected} — ESG Score Over Time", height=300)
        st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.info("Run the pipeline multiple times to see score history.")


# ── Alerts ─────────────────────────────────────────────────────────────────────
elif page == "Alerts":
    st.title("ESG Alerts")
    scores = load_scores()
    alerts = [s for s in scores if s["Alert"] != "—"]

    if not alerts:
        st.success("No active ESG alerts. All companies are within acceptable thresholds.")
    else:
        for a in alerts:
            level = a["Alert"]
            color = ALERT_COLOR.get(level, "#888")
            st.markdown(
                f'<div style="background:{color};color:white;padding:12px;border-radius:8px;margin-bottom:8px;">'
                f'<b>{level}</b> — {a["company"]} ({a["ticker"]}) &nbsp;|&nbsp; ESG Score: <b>{a["Total"]:.1f}</b>'
                f'&nbsp;|&nbsp; Sector: {a["sector"]}</div>',
                unsafe_allow_html=True,
            )


# ── AI Assistant ───────────────────────────────────────────────────────────────
elif page == "AI Assistant":
    st.title("AI ESG Assistant")
    st.caption("Ask natural language questions about ESG scores, powered by Claude + LangChain RAG.")

    scores = load_scores()
    tickers_opt = ["All companies"] + [s["ticker"] for s in scores]
    selected_ticker = st.selectbox("Focus on (optional)", tickers_opt)
    ticker_filter = None if selected_ticker == "All companies" else selected_ticker

    question = st.text_input("Your question", placeholder="Which company has the worst carbon intensity?")

    if st.button("Ask") and question:
        with st.spinner("Thinking..."):
            try:
                from src.rag.chain import answer_question
                answer, sources = answer_question(question, ticker=ticker_filter)
                st.markdown(f"**Answer:** {answer}")
                if sources:
                    st.caption("Sources: " + ", ".join(sources))
            except Exception as e:
                st.error(f"RAG layer error: {e}. Make sure ANTHROPIC_API_KEY is set.")


# ── Run Pipeline ───────────────────────────────────────────────────────────────
elif page == "Run Pipeline":
    st.title("Run ESG Pipeline")
    st.markdown(
        "Trigger the **Prefect-orchestrated pipeline** to ingest data, compute ESG scores, "
        "persist to the database, and surface alerts."
    )

    tickers_input = st.text_input(
        "Tickers to process (comma-separated, leave blank for all)",
        placeholder="AAPL, MSFT, XOM",
    )

    if st.button("Run Pipeline", type="primary"):
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()] or None
        with st.spinner("Running pipeline..."):
            result = run_esg_pipeline(tickers=tickers)

        st.success(f"Pipeline complete — {result.get('companies_processed', 0)} companies processed.")
        load_scores.clear()  # invalidate cache

        if result.get("alerts"):
            st.warning(f"{len(result['alerts'])} alert(s) triggered:")
            for a in result["alerts"]:
                st.write(f"- **{a['alert']}**: {a['company']} ({a['ticker']}) — score {a['total']:.1f}")

        st.subheader("Scores")
        import pandas as pd
        df_res = pd.DataFrame(result.get("scores", []))
        if not df_res.empty:
            st.dataframe(df_res, use_container_width=True, hide_index=True)
