from pydantic import BaseModel, Field
from datetime import datetime


# --- Agent ---

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class AgentOut(BaseModel):
    id: str
    name: str
    api_key: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Artifact ---

class ArtifactCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    language: str = Field(..., min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0", max_length=32)


class ArtifactUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    code: str | None = None
    tags: list[str] | None = None
    version: str | None = None


class ArtifactSummary(BaseModel):
    id: str
    title: str
    description: str
    language: str
    tags: list[str]
    version: str
    avg_rating: float
    rating_count: int
    pull_count: int
    author_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactFull(ArtifactSummary):
    code: str
    updated_at: datetime


# --- Rating ---

class RatingCreate(BaseModel):
    score: float = Field(..., ge=1.0, le=5.0)
    review: str = Field(default="")


class RatingOut(BaseModel):
    id: str
    score: float
    review: str
    agent_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Search ---

class SearchQuery(BaseModel):
    q: str = Field(default="", description="Free-text search across title, description, tags")
    language: str | None = Field(default=None, description="Filter by language")
    tags: list[str] = Field(default_factory=list, description="Filter by tags (AND match)")
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    sort_by: str = Field(default="rating", pattern="^(rating|pulls|recent)$")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
