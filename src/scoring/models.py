"""SQLAlchemy ORM models for persisting ESG scores."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class CompanyESGRecord(Base):
    __tablename__ = "esg_scores"

    ticker = Column(String(20), primary_key=True)
    company_name = Column(String(200), nullable=False)
    sector = Column(String(100))
    country = Column(String(10))
    environmental_score = Column(Float)
    social_score = Column(Float)
    governance_score = Column(Float)
    total_score = Column(Float)
    rating = Column(String(20))
    alert = Column(String(20), nullable=True)
    metric_detail = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScoreHistory(Base):
    __tablename__ = "score_history"

    id = Column(String(40), primary_key=True)
    ticker = Column(String(20), nullable=False)
    total_score = Column(Float)
    environmental_score = Column(Float)
    social_score = Column(Float)
    governance_score = Column(Float)
    rating = Column(String(20))
    recorded_at = Column(DateTime, default=datetime.utcnow)
