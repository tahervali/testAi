import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Use in-memory SQLite for tests — StaticPool ensures all connections share
# the same underlying database so tables created in setup are visible.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def register_agent(name="test-agent"):
    resp = client.post("/api/v1/agents/register", json={"name": name})
    assert resp.status_code == 200
    return resp.json()


def publish_artifact(api_key, **overrides):
    data = {
        "title": "JWT Middleware",
        "description": "FastAPI JWT authentication middleware",
        "code": "def verify_token(token): ...",
        "language": "python",
        "tags": ["jwt", "auth", "middleware"],
        "version": "1.0.0",
    }
    data.update(overrides)
    resp = client.post(
        "/api/v1/artifacts",
        json=data,
        headers={"X-Api-Key": api_key},
    )
    return resp


# ─── Agent Registration ───────────────────────────────────────────

class TestAgentRegistration:
    def test_register_agent(self):
        agent = register_agent("my-agent")
        assert agent["name"] == "my-agent"
        assert agent["api_key"].startswith("art_")
        assert "id" in agent

    def test_register_multiple_agents(self):
        a1 = register_agent("agent-1")
        a2 = register_agent("agent-2")
        assert a1["api_key"] != a2["api_key"]


# ─── Artifact CRUD ────────────────────────────────────────────────

class TestArtifactCRUD:
    def test_create_artifact(self):
        agent = register_agent()
        resp = publish_artifact(agent["api_key"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "JWT Middleware"
        assert data["language"] == "python"
        assert "jwt" in data["tags"]
        assert data["code"] == "def verify_token(token): ..."

    def test_create_requires_auth(self):
        resp = client.post("/api/v1/artifacts", json={
            "title": "test", "description": "test",
            "code": "x=1", "language": "python",
        })
        assert resp.status_code == 422  # missing header

    def test_create_rejects_bad_key(self):
        resp = client.post(
            "/api/v1/artifacts",
            json={"title": "t", "description": "d", "code": "c", "language": "py"},
            headers={"X-Api-Key": "bad_key"},
        )
        assert resp.status_code == 401

    def test_get_artifact(self):
        agent = register_agent()
        created = publish_artifact(agent["api_key"]).json()
        resp = client.get(f"/api/v1/artifacts/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["code"] == "def verify_token(token): ..."

    def test_get_not_found(self):
        resp = client.get("/api/v1/artifacts/nonexistent")
        assert resp.status_code == 404

    def test_update_artifact(self):
        agent = register_agent()
        created = publish_artifact(agent["api_key"]).json()
        resp = client.patch(
            f"/api/v1/artifacts/{created['id']}",
            json={"title": "Updated Title", "version": "2.0.0"},
            headers={"X-Api-Key": agent["api_key"]},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["version"] == "2.0.0"

    def test_update_only_owner(self):
        agent1 = register_agent("owner")
        agent2 = register_agent("other")
        created = publish_artifact(agent1["api_key"]).json()
        resp = client.patch(
            f"/api/v1/artifacts/{created['id']}",
            json={"title": "Hijack"},
            headers={"X-Api-Key": agent2["api_key"]},
        )
        assert resp.status_code == 404

    def test_delete_artifact(self):
        agent = register_agent()
        created = publish_artifact(agent["api_key"]).json()
        resp = client.delete(
            f"/api/v1/artifacts/{created['id']}",
            headers={"X-Api-Key": agent["api_key"]},
        )
        assert resp.status_code == 204
        assert client.get(f"/api/v1/artifacts/{created['id']}").status_code == 404


# ─── Pull ──────────────────────────────────────────────────────────

class TestPull:
    def test_pull_increments_count(self):
        agent = register_agent()
        created = publish_artifact(agent["api_key"]).json()
        assert created["pull_count"] == 0

        resp = client.post(f"/api/v1/artifacts/{created['id']}/pull")
        assert resp.status_code == 200
        assert resp.json()["pull_count"] == 1

        resp = client.post(f"/api/v1/artifacts/{created['id']}/pull")
        assert resp.json()["pull_count"] == 2

    def test_pull_returns_code(self):
        agent = register_agent()
        created = publish_artifact(agent["api_key"]).json()
        resp = client.post(f"/api/v1/artifacts/{created['id']}/pull")
        assert resp.json()["code"] == "def verify_token(token): ..."


# ─── Search ────────────────────────────────────────────────────────

class TestSearch:
    def test_search_by_text(self):
        agent = register_agent()
        publish_artifact(agent["api_key"], title="Redis Cache Helper", description="Redis caching utility", tags=["redis", "cache"])
        publish_artifact(agent["api_key"], title="JWT Auth", description="JWT middleware", tags=["jwt"])

        resp = client.get("/api/v1/artifacts", params={"q": "redis"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["title"] == "Redis Cache Helper"

    def test_search_by_language(self):
        agent = register_agent()
        publish_artifact(agent["api_key"], language="python")
        publish_artifact(agent["api_key"], language="javascript", title="JS Util", code="const x = 1")

        resp = client.get("/api/v1/artifacts", params={"language": "python"})
        results = resp.json()
        assert len(results) == 1
        assert results[0]["language"] == "python"

    def test_search_by_tags(self):
        agent = register_agent()
        publish_artifact(agent["api_key"], tags=["auth", "jwt"])
        publish_artifact(agent["api_key"], title="Logger", description="Logging util", tags=["logging"], code="import logging")

        resp = client.get("/api/v1/artifacts", params={"tags": "auth"})
        results = resp.json()
        assert len(results) == 1
        assert "auth" in results[0]["tags"]

    def test_search_empty_returns_all(self):
        agent = register_agent()
        publish_artifact(agent["api_key"])
        publish_artifact(agent["api_key"], title="Another", description="Another artifact", code="pass")

        resp = client.get("/api/v1/artifacts")
        assert len(resp.json()) == 2

    def test_search_sort_by_pulls(self):
        agent = register_agent()
        a1 = publish_artifact(agent["api_key"], title="Unpopular", description="Not popular", code="pass").json()
        a2 = publish_artifact(agent["api_key"], title="Popular", description="Very popular", code="pass").json()
        # Pull a2 three times
        for _ in range(3):
            client.post(f"/api/v1/artifacts/{a2['id']}/pull")

        resp = client.get("/api/v1/artifacts", params={"sort_by": "pulls"})
        results = resp.json()
        assert results[0]["title"] == "Popular"


# ─── Ratings ───────────────────────────────────────────────────────

class TestRatings:
    def test_rate_artifact(self):
        agent = register_agent()
        created = publish_artifact(agent["api_key"]).json()

        resp = client.post(
            f"/api/v1/artifacts/{created['id']}/rate",
            json={"score": 4.5, "review": "Great middleware!"},
            headers={"X-Api-Key": agent["api_key"]},
        )
        assert resp.status_code == 201
        assert resp.json()["score"] == 4.5

        # Check artifact average updated
        artifact = client.get(f"/api/v1/artifacts/{created['id']}").json()
        assert artifact["avg_rating"] == 4.5
        assert artifact["rating_count"] == 1

    def test_multiple_ratings(self):
        a1 = register_agent("agent-1")
        a2 = register_agent("agent-2")
        created = publish_artifact(a1["api_key"]).json()

        client.post(
            f"/api/v1/artifacts/{created['id']}/rate",
            json={"score": 5.0},
            headers={"X-Api-Key": a1["api_key"]},
        )
        client.post(
            f"/api/v1/artifacts/{created['id']}/rate",
            json={"score": 3.0},
            headers={"X-Api-Key": a2["api_key"]},
        )

        artifact = client.get(f"/api/v1/artifacts/{created['id']}").json()
        assert artifact["avg_rating"] == 4.0
        assert artifact["rating_count"] == 2

    def test_update_existing_rating(self):
        agent = register_agent()
        created = publish_artifact(agent["api_key"]).json()

        # Rate once
        client.post(
            f"/api/v1/artifacts/{created['id']}/rate",
            json={"score": 2.0},
            headers={"X-Api-Key": agent["api_key"]},
        )
        # Re-rate
        client.post(
            f"/api/v1/artifacts/{created['id']}/rate",
            json={"score": 5.0},
            headers={"X-Api-Key": agent["api_key"]},
        )

        artifact = client.get(f"/api/v1/artifacts/{created['id']}").json()
        assert artifact["avg_rating"] == 5.0
        assert artifact["rating_count"] == 1  # still 1, not 2

    def test_list_ratings(self):
        a1 = register_agent("a1")
        a2 = register_agent("a2")
        created = publish_artifact(a1["api_key"]).json()

        client.post(
            f"/api/v1/artifacts/{created['id']}/rate",
            json={"score": 5.0, "review": "Excellent"},
            headers={"X-Api-Key": a1["api_key"]},
        )
        client.post(
            f"/api/v1/artifacts/{created['id']}/rate",
            json={"score": 3.0, "review": "Okay"},
            headers={"X-Api-Key": a2["api_key"]},
        )

        resp = client.get(f"/api/v1/artifacts/{created['id']}/ratings")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ─── Health ────────────────────────────────────────────────────────

class TestHealth:
    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["service"] == "Agent Artifact Registry"
