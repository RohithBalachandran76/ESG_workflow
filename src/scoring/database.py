"""Database session factory and initialisation."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.scoring.models import Base

_engine = None
_SessionLocal = None


def get_engine(database_url: str = "sqlite:///./esg_workflow.db"):
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=_engine)
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()
