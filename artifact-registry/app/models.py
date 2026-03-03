import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_id():
    return uuid.uuid4().hex[:16]


class Agent(Base):
    """Registered agent that can publish/pull/rate artifacts."""
    __tablename__ = "agents"

    id = Column(String(16), primary_key=True, default=gen_id)
    name = Column(String(128), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    artifacts = relationship("Artifact", back_populates="author")
    ratings = relationship("Rating", back_populates="agent")


class Artifact(Base):
    """A reusable code artifact published by an agent."""
    __tablename__ = "artifacts"

    id = Column(String(16), primary_key=True, default=gen_id)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(64), nullable=False)
    tags = Column(String(512), default="")  # comma-separated
    version = Column(String(32), default="1.0.0")
    avg_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    pull_count = Column(Integer, default=0)
    agent_id = Column(String(16), ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    author = relationship("Agent", back_populates="artifacts")
    ratings = relationship("Rating", back_populates="artifact")

    __table_args__ = (
        Index("ix_artifacts_language", "language"),
        Index("ix_artifacts_avg_rating", "avg_rating"),
    )


class Rating(Base):
    """An agent's rating of an artifact."""
    __tablename__ = "ratings"

    id = Column(String(16), primary_key=True, default=gen_id)
    score = Column(Float, nullable=False)  # 1.0 - 5.0
    review = Column(Text, default="")
    agent_id = Column(String(16), ForeignKey("agents.id"), nullable=False)
    artifact_id = Column(String(16), ForeignKey("artifacts.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent", back_populates="ratings")
    artifact = relationship("Artifact", back_populates="ratings")

    __table_args__ = (
        Index("ix_ratings_artifact", "artifact_id"),
    )
