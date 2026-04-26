"""Database session factory and initialisation."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.scoring.models import Base

_engine = None
_SessionLocal = None

_DEFAULT_DB_URL = "sqlite:///./esg_workflow.db"


def get_engine(database_url: str | None = None):
    global _engine
    if _engine is None:
        url = database_url or os.environ.get("DATABASE_URL", _DEFAULT_DB_URL)
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=_engine)
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()
