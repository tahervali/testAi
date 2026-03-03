import secrets
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Agent


def generate_api_key() -> str:
    return f"art_{secrets.token_urlsafe(32)}"


def get_current_agent(
    x_api_key: str = Header(..., description="Agent API key"),
    db: Session = Depends(get_db),
) -> Agent:
    agent = db.query(Agent).filter(Agent.api_key == x_api_key).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return agent
