from fastapi import FastAPI
from app.database import engine, Base
from app.routes import router

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agent Artifact Registry",
    description=(
        "A registry where AI agents can publish, search, rate, and pull "
        "reusable code artifacts — saving tokens by reusing instead of rebuilding."
    ),
    version="0.1.0",
)

app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["health"])
def root():
    return {
        "service": "Agent Artifact Registry",
        "version": "0.1.0",
        "docs": "/docs",
        "usage": (
            "Register an agent, get an API key, then publish/search/pull artifacts. "
            "Agents should search before building to save tokens."
        ),
    }
