"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.scoring.database import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()  # ensure DB + tables exist
    yield


app = FastAPI(
    title="ESG Workflow API",
    description=(
        "Environmental, Social & Governance scoring pipeline.\n\n"
        "Aligned with **CSRD/ESRS** framework. "
        "Supports real-time scoring, historical tracking, alert management, "
        "and natural-language Q&A via a LangChain RAG layer."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {"service": "ESG Workflow API", "version": "1.0.0", "status": "running"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
