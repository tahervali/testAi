import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, JSON
from database import Base


def _id():
    return uuid.uuid4().hex[:12]


def _now():
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(12), primary_key=True, default=_id)
    name = Column(String(128), nullable=False, unique=True)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=_now)
    push_count = Column(Integer, default=0)
    pull_count = Column(Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "push_count": self.push_count,
            "pull_count": self.pull_count,
        }


class Solution(Base):
    __tablename__ = "solutions"

    id = Column(String(12), primary_key=True, default=_id)
    task_description = Column(Text, nullable=False)
    solution_type = Column(String(32), nullable=False, default="artifact")
    solution = Column(Text, nullable=False)
    language = Column(String(64), nullable=False, default="python")
    tags = Column(JSON, default=list)
    input_schema = Column(Text, default="")
    output_schema = Column(Text, default="")
    agent_id = Column(String(12), nullable=False)
    agent_name = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=_now)
    success_rate = Column(Float, default=1.0)
    attempt_count = Column(Integer, default=0)
    composed_from = Column(JSON, default=list)

    def to_dict(self):
        return {
            "id": self.id,
            "task_description": self.task_description,
            "solution_type": self.solution_type,
            "solution": self.solution,
            "language": self.language,
            "tags": self.tags or [],
            "input_schema": self.input_schema or "",
            "output_schema": self.output_schema or "",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "success_rate": self.success_rate,
            "attempt_count": self.attempt_count,
            "composed_from": self.composed_from or [],
        }


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(String(12), primary_key=True, default=_id)
    solution_id = Column(String(12), nullable=False, index=True)
    agent_name = Column(String(128), nullable=False)
    rating = Column(Integer, nullable=False)  # 0 or 1
    created_at = Column(DateTime, default=_now)

    def to_dict(self):
        return {
            "id": self.id,
            "solution_id": self.solution_id,
            "agent_name": self.agent_name,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Log(Base):
    __tablename__ = "logs"

    id = Column(String(12), primary_key=True, default=_id)
    event = Column(String(64), nullable=False)
    agent_name = Column(String(128), default="")
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)

    def to_dict(self):
        return {
            "id": self.id,
            "event": self.event,
            "agent_name": self.agent_name,
            "payload": self.payload or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
