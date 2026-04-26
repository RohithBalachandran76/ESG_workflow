"""LangChain RAG chain for natural-language ESG Q&A.

Uses:
  - ChromaDB as in-memory vector store
  - Claude (claude-sonnet-4-6) as the LLM via langchain-anthropic
  - Documents built from the live ESG database

Prompt is tuned to answer ESG-specific questions with domain context
(CSRD, ESRS, LkSG, carbon intensity, board independence, etc.)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_vectorstore = None
_chain = None


def _build_chain():
    global _vectorstore, _chain

    from langchain.chains import RetrievalQA
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_anthropic import ChatAnthropic
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import FakeEmbeddings

    from src.rag.documents import build_company_documents

    docs = build_company_documents()

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    splits = splitter.split_documents(docs)

    # Use FakeEmbeddings for zero-dependency demo; swap for real embeddings in production
    embeddings = FakeEmbeddings(size=1536)
    _vectorstore = Chroma.from_documents(splits, embeddings)

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        temperature=0,
        max_tokens=1024,
    )

    _chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=_vectorstore.as_retriever(search_kwargs={"k": 4}),
        return_source_documents=True,
    )
    return _chain


ESG_SYSTEM_CONTEXT = """You are an expert ESG (Environmental, Social, Governance) analyst.
You have access to a database of company ESG scores aligned with the CSRD/ESRS framework.
Scores are on a 0-100 scale per pillar. Ratings: Excellent (>75), Good (55-75), Fair (35-55), Poor (<35).
Alerts: CRITICAL (<30 total score), WATCH (<45 total score).
Answer concisely and cite specific scores and metrics where possible.
"""


def answer_question(question: str, ticker: str | None = None) -> tuple[str, list[str]]:
    """Run the RAG chain and return (answer, list_of_source_tickers)."""
    global _chain
    if _chain is None:
        _build_chain()

    # Prepend ticker context if provided
    augmented = question
    if ticker:
        augmented = f"Regarding company with ticker {ticker}: {question}"

    full_question = ESG_SYSTEM_CONTEXT + "\n\nUser question: " + augmented

    result = _chain.invoke({"query": full_question})
    answer = result.get("result", "No answer generated.")
    source_docs = result.get("source_documents", [])
    sources = list({d.metadata.get("ticker", "unknown") for d in source_docs})
    return answer, sources


def reset_chain():
    """Force rebuild of the chain (call after pipeline runs to refresh docs)."""
    global _vectorstore, _chain
    _vectorstore = None
    _chain = None
