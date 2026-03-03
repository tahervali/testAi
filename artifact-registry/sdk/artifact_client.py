"""
Agent Artifact Registry SDK

A lightweight client for AI agents to search, pull, publish, and rate
code artifacts. Drop this into any agent to save tokens by reusing
existing artifacts instead of building from scratch.

Usage:
    from artifact_client import ArtifactClient

    client = ArtifactClient(base_url="http://localhost:8000", api_key="art_...")

    # Search before building
    results = client.search("jwt authentication middleware", language="python")
    if results:
        code = client.pull(results[0]["id"])
        # Use the code instead of generating from scratch
    else:
        # Build it, then publish for others
        client.publish(
            title="JWT Auth Middleware",
            description="FastAPI middleware for JWT token validation",
            code=my_generated_code,
            language="python",
            tags=["jwt", "auth", "middleware", "fastapi"],
        )
"""

import httpx
from typing import Any


class ArtifactClient:
    """Client for the Agent Artifact Registry API."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._api = f"{self.base_url}/api/v1"

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-Api-Key"] = self.api_key
        return h

    @staticmethod
    def register(base_url: str, agent_name: str) -> "ArtifactClient":
        """Register a new agent and return a configured client."""
        url = f"{base_url.rstrip('/')}/api/v1/agents/register"
        resp = httpx.post(url, json={"name": agent_name})
        resp.raise_for_status()
        data = resp.json()
        return ArtifactClient(base_url=base_url, api_key=data["api_key"])

    # ─── Search ────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        language: str | None = None,
        tags: list[str] | None = None,
        min_rating: float = 0.0,
        sort_by: str = "rating",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search for existing artifacts. Call this BEFORE generating code
        to check if a reusable artifact already exists.

        Returns a list of artifact summaries sorted by relevance.
        """
        params: dict[str, Any] = {"q": query, "sort_by": sort_by, "limit": limit}
        if language:
            params["language"] = language
        if tags:
            params["tags"] = ",".join(tags)
        if min_rating > 0:
            params["min_rating"] = min_rating

        resp = httpx.get(f"{self._api}/artifacts", params=params)
        resp.raise_for_status()
        return resp.json()

    # ─── Pull ──────────────────────────────────────────────────────

    def pull(self, artifact_id: str) -> dict[str, Any]:
        """
        Pull an artifact by ID. Returns the full artifact including code.
        Increments the pull counter so popular artifacts surface higher.
        """
        resp = httpx.post(f"{self._api}/artifacts/{artifact_id}/pull")
        resp.raise_for_status()
        return resp.json()

    def pull_code(self, artifact_id: str) -> str:
        """Pull just the code string from an artifact."""
        return self.pull(artifact_id)["code"]

    # ─── Publish ───────────────────────────────────────────────────

    def publish(
        self,
        title: str,
        description: str,
        code: str,
        language: str,
        tags: list[str] | None = None,
        version: str = "1.0.0",
    ) -> dict[str, Any]:
        """
        Publish a new code artifact to the registry.
        Other agents can then find and reuse it.
        """
        resp = httpx.post(
            f"{self._api}/artifacts",
            headers=self._headers(),
            json={
                "title": title,
                "description": description,
                "code": code,
                "language": language,
                "tags": tags or [],
                "version": version,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Rate ──────────────────────────────────────────────────────

    def rate(
        self, artifact_id: str, score: float, review: str = ""
    ) -> dict[str, Any]:
        """
        Rate an artifact (1.0 - 5.0). Helps surface the best artifacts.
        """
        resp = httpx.post(
            f"{self._api}/artifacts/{artifact_id}/rate",
            headers=self._headers(),
            json={"score": score, "review": review},
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Update / Delete ───────────────────────────────────────────

    def update(self, artifact_id: str, **fields) -> dict[str, Any]:
        """Update an artifact you own."""
        resp = httpx.patch(
            f"{self._api}/artifacts/{artifact_id}",
            headers=self._headers(),
            json=fields,
        )
        resp.raise_for_status()
        return resp.json()

    def delete(self, artifact_id: str) -> None:
        """Delete an artifact you own."""
        resp = httpx.delete(
            f"{self._api}/artifacts/{artifact_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()

    # ─── Convenience ───────────────────────────────────────────────

    def search_or_build(
        self,
        query: str,
        language: str,
        build_fn,
        tags: list[str] | None = None,
        min_rating: float = 3.0,
        title: str | None = None,
    ) -> str:
        """
        The core token-saving pattern:
        1. Search for an existing artifact matching the query
        2. If found (with good rating), pull and return its code
        3. If not found, call build_fn() to generate code,
           then publish it for future reuse

        Args:
            query: What you're looking for
            language: Programming language
            build_fn: Callable that returns generated code (str)
            tags: Tags for publishing if built from scratch
            min_rating: Minimum rating threshold for reuse
            title: Title if publishing new artifact

        Returns:
            The code string (either pulled or freshly built)
        """
        results = self.search(query, language=language, min_rating=min_rating)
        if results:
            return self.pull_code(results[0]["id"])

        # Nothing found — build it
        code = build_fn()

        # Publish for future reuse
        if self.api_key:
            self.publish(
                title=title or query,
                description=query,
                code=code,
                language=language,
                tags=tags or [],
            )

        return code
