from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import Agent, Artifact, Rating
from app.schemas import (
    AgentCreate, AgentOut,
    ArtifactCreate, ArtifactUpdate, ArtifactSummary, ArtifactFull,
    RatingCreate, RatingOut,
)
from app.auth import generate_api_key, get_current_agent

router = APIRouter()


# ─── Agent Registration ───────────────────────────────────────────────

@router.post("/agents/register", response_model=AgentOut, tags=["agents"])
def register_agent(body: AgentCreate, db: Session = Depends(get_db)):
    """Register a new agent and get an API key."""
    agent = Agent(name=body.name, api_key=generate_api_key())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


# ─── Artifact CRUD ────────────────────────────────────────────────────

@router.post("/artifacts", response_model=ArtifactFull, status_code=201, tags=["artifacts"])
def create_artifact(
    body: ArtifactCreate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Publish a new code artifact to the registry."""
    artifact = Artifact(
        title=body.title,
        description=body.description,
        code=body.code,
        language=body.language.lower(),
        tags=",".join(t.lower().strip() for t in body.tags),
        version=body.version,
        agent_id=agent.id,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return _artifact_to_full(artifact, agent.name)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactFull, tags=["artifacts"])
def get_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """Get a specific artifact by ID (without incrementing pull count)."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _artifact_to_full(artifact, artifact.author.name)


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactFull, tags=["artifacts"])
def update_artifact(
    artifact_id: str,
    body: ArtifactUpdate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Update an artifact you own."""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id, Artifact.agent_id == agent.id
    ).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found or not owned by you")
    if body.title is not None:
        artifact.title = body.title
    if body.description is not None:
        artifact.description = body.description
    if body.code is not None:
        artifact.code = body.code
    if body.tags is not None:
        artifact.tags = ",".join(t.lower().strip() for t in body.tags)
    if body.version is not None:
        artifact.version = body.version
    db.commit()
    db.refresh(artifact)
    return _artifact_to_full(artifact, agent.name)


@router.delete("/artifacts/{artifact_id}", status_code=204, tags=["artifacts"])
def delete_artifact(
    artifact_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Delete an artifact you own."""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id, Artifact.agent_id == agent.id
    ).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found or not owned by you")
    db.delete(artifact)
    db.commit()


# ─── Pull (download) ──────────────────────────────────────────────────

@router.post("/artifacts/{artifact_id}/pull", response_model=ArtifactFull, tags=["artifacts"])
def pull_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """Pull an artifact's code. Increments the pull counter."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact.pull_count += 1
    db.commit()
    db.refresh(artifact)
    return _artifact_to_full(artifact, artifact.author.name)


# ─── Search ────────────────────────────────────────────────────────────

@router.get("/artifacts", response_model=list[ArtifactSummary], tags=["search"])
def search_artifacts(
    q: str = Query(default="", description="Free-text search"),
    language: str | None = Query(default=None),
    tags: str | None = Query(default=None, description="Comma-separated tags"),
    min_rating: float = Query(default=0.0, ge=0.0, le=5.0),
    sort_by: str = Query(default="rating", pattern="^(rating|pulls|recent)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Search for artifacts. Agents should call this FIRST to check if
    a reusable artifact already exists before building from scratch.
    """
    query = db.query(Artifact)

    # Free-text search across title, description, tags
    if q:
        pattern = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Artifact.title.ilike(pattern),
                Artifact.description.ilike(pattern),
                Artifact.tags.ilike(pattern),
            )
        )

    # Language filter
    if language:
        query = query.filter(Artifact.language == language.lower())

    # Tag filter (AND — all requested tags must be present)
    if tags:
        for tag in tags.split(","):
            tag = tag.strip().lower()
            if tag:
                query = query.filter(Artifact.tags.ilike(f"%{tag}%"))

    # Minimum rating filter
    if min_rating > 0:
        query = query.filter(Artifact.avg_rating >= min_rating)

    # Sort
    if sort_by == "rating":
        query = query.order_by(Artifact.avg_rating.desc(), Artifact.pull_count.desc())
    elif sort_by == "pulls":
        query = query.order_by(Artifact.pull_count.desc())
    elif sort_by == "recent":
        query = query.order_by(Artifact.created_at.desc())

    artifacts = query.offset(offset).limit(limit).all()
    return [_artifact_to_summary(a, a.author.name) for a in artifacts]


# ─── Ratings ───────────────────────────────────────────────────────────

@router.post("/artifacts/{artifact_id}/rate", response_model=RatingOut, status_code=201, tags=["ratings"])
def rate_artifact(
    artifact_id: str,
    body: RatingCreate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Rate an artifact (1-5). Updates the artifact's average rating."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Check if this agent already rated this artifact
    existing = db.query(Rating).filter(
        Rating.agent_id == agent.id, Rating.artifact_id == artifact_id
    ).first()
    if existing:
        # Update existing rating
        old_score = existing.score
        existing.score = body.score
        existing.review = body.review
        # Recalculate average
        total = artifact.avg_rating * artifact.rating_count - old_score + body.score
        artifact.avg_rating = total / artifact.rating_count
        db.commit()
        db.refresh(existing)
        return existing

    # New rating
    rating = Rating(
        score=body.score,
        review=body.review,
        agent_id=agent.id,
        artifact_id=artifact_id,
    )
    db.add(rating)

    # Update artifact average
    total = artifact.avg_rating * artifact.rating_count + body.score
    artifact.rating_count += 1
    artifact.avg_rating = total / artifact.rating_count

    db.commit()
    db.refresh(rating)
    return rating


@router.get("/artifacts/{artifact_id}/ratings", response_model=list[RatingOut], tags=["ratings"])
def list_ratings(artifact_id: str, db: Session = Depends(get_db)):
    """List all ratings for an artifact."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return db.query(Rating).filter(Rating.artifact_id == artifact_id).all()


# ─── Helpers ───────────────────────────────────────────────────────────

def _tags_list(tags_str: str) -> list[str]:
    return [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []


def _artifact_to_summary(a: Artifact, author_name: str) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "language": a.language,
        "tags": _tags_list(a.tags),
        "version": a.version,
        "avg_rating": a.avg_rating,
        "rating_count": a.rating_count,
        "pull_count": a.pull_count,
        "author_name": author_name,
        "created_at": a.created_at,
    }


def _artifact_to_full(a: Artifact, author_name: str) -> dict:
    d = _artifact_to_summary(a, author_name)
    d["code"] = a.code
    d["updated_at"] = a.updated_at
    return d
