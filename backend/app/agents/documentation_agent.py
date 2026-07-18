"""
DocumentationAgent – retrieves relevant runbooks, Confluence pages,
and past incident resolutions from the vector knowledge base.

Tools:
  • search_vector_db      – semantic search against past incident resolutions
  • search_confluence     – full-text search in Confluence wiki
  • get_runbook           – fetch a specific runbook by name/ID
  • search_internal_docs  – search internal documentation repos
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.agents.base import BaseAgent
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class DocumentationAgent(BaseAgent):
    """Finds relevant runbooks and similar past incidents."""

    agent_type = "documentation"

    tools = [
        {
            "name": "search_vector_db",
            "description": (
                "Perform semantic similarity search against the Atlas AI learning "
                "database of approved past incident resolutions. "
                "Returns the top-K most similar past incidents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of the problem",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of results to return",
                    },
                    "threshold": {
                        "type": "number",
                        "default": 0.75,
                        "description": "Minimum cosine similarity (0–1)",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "search_confluence",
            "description": (
                "Search Confluence for pages matching a query (runbooks, postmortems, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "space_key": {
                        "type": "string",
                        "description": "Confluence space key e.g. 'OPS'",
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_runbook",
            "description": "Fetch the full content of a runbook by its title or Confluence page ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Confluence page ID or exact page title",
                    },
                },
                "required": ["identifier"],
            },
        },
        {
            "name": "search_internal_docs",
            "description": (
                "Search internal documentation stored in GitHub wiki or a docs repository."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "repo": {
                        "type": "string",
                        "description": "owner/repo (defaults to GITHUB_REPO setting)",
                    },
                },
                "required": ["query"],
            },
        },
    ]

    def __init__(self, *args: Any, db_session: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._db_session = db_session  # Optional injected DB session for vector search

    async def run(self) -> dict[str, Any]:
        await self._emit_progress("DocumentationAgent starting search")

        system_prompt = (
            "You are a knowledge management expert. Search for relevant runbooks, "
            "past incident resolutions, and internal documentation that could help "
            "diagnose and fix this incident. Prioritise the most actionable results."
        )

        user_message = (
            f"Incident Context:\n{self._build_context_summary()}\n\n"
            "Search the knowledge base for: "
            "1) Similar past incidents with their resolutions, "
            "2) Relevant runbooks, "
            "3) Confluence postmortems. "
            "Summarise the most applicable guidance."
        )

        summary = await self._run_agent_loop(system_prompt, user_message, max_iterations=6)
        await self._emit_progress("DocumentationAgent search complete")

        return {
            "findings": self._findings,
            "actions_taken": self._actions,
            "token_usage": self._token_usage,
            "summary": summary,
        }

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_search_vector_db(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.75,
    ) -> dict[str, Any]:
        """Search the Atlas AI learning database for similar past incidents."""
        if self._db_session is None:
            return {"results": [], "note": "No DB session available"}

        try:
            # Generate embedding for the query
            response = await self._client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=query,
            )
            query_vector = response.data[0].embedding

            # Query learning_cases table using dot-product similarity on JSONB vectors
            # In production replace with pgvector <=> operator
            from sqlalchemy import select

            from app.models.learning_case import LearningCase

            stmt = (
                select(LearningCase)
                .where(LearningCase.resolution_approved == True)  # noqa: E712
                .limit(top_k * 5)  # Fetch more, then re-rank
            )
            result = await self._db_session.execute(stmt)
            cases = result.scalars().all()

            # Cosine similarity in Python (pgvector would do this in SQL)
            import numpy as np

            q = np.array(query_vector)
            ranked = []
            for case in cases:
                if case.embedding_vector:
                    v = np.array(case.embedding_vector)
                    sim = float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-9))
                    if sim >= threshold:
                        ranked.append(
                            {
                                "incident_id": str(case.incident_id),
                                "resolution": case.resolution_text,
                                "outcome_score": case.outcome_score,
                                "similarity": round(sim, 4),
                                "tags": case.tags,
                            }
                        )

            ranked.sort(key=lambda x: x["similarity"], reverse=True)
            return {"results": ranked[:top_k], "total_checked": len(cases)}

        except Exception as e:  # noqa: BLE001
            return {"results": [], "error": str(e)}

    async def _tool_search_confluence(
        self, query: str, space_key: str = "", limit: int = 5
    ) -> dict[str, Any]:
        base = str(settings.CONFLUENCE_URL).rstrip("/")
        params: dict[str, Any] = {
            "cql": f'type=page AND text~"{query}"'
                  + (f' AND space="{space_key}"' if space_key else ""),
            "limit": limit,
            "expand": "metadata.labels",
        }
        auth = (settings.CONFLUENCE_USERNAME, settings.CONFLUENCE_API_TOKEN)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{base}/rest/api/content/search",
                    params=params,
                    auth=auth,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                pages = [
                    {
                        "id": p["id"],
                        "title": p["title"],
                        "url": f"{base}/wiki{p.get('_links', {}).get('webui', '')}",
                        "space": p.get("space", {}).get("key"),
                    }
                    for p in data.get("results", [])
                ]
                return {"pages": pages, "total": data.get("totalSize", 0)}
        except Exception as e:  # noqa: BLE001
            return {"pages": [], "error": str(e)}

    async def _tool_get_runbook(self, identifier: str) -> dict[str, Any]:
        base = str(settings.CONFLUENCE_URL).rstrip("/")
        auth = (settings.CONFLUENCE_USERNAME, settings.CONFLUENCE_API_TOKEN)

        # Try by ID first, then search by title
        url = f"{base}/rest/api/content/{identifier}?expand=body.storage"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, auth=auth, timeout=15)
                if resp.status_code == 200:
                    page = resp.json()
                    return {
                        "title": page["title"],
                        "content_html": page.get("body", {}).get("storage", {}).get("value", ""),
                        "id": page["id"],
                    }
                # Fall back to search by title
                search_resp = await client.get(
                    f"{base}/rest/api/content/search",
                    params={"cql": f'title="{identifier}" AND type=page', "expand": "body.storage"},
                    auth=auth,
                    timeout=15,
                )
                search_resp.raise_for_status()
                results = search_resp.json().get("results", [])
                if results:
                    p = results[0]
                    return {
                        "title": p["title"],
                        "content_html": p.get("body", {}).get("storage", {}).get("value", ""),
                        "id": p["id"],
                    }
                return {"error": f"Page not found: {identifier}"}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    async def _tool_search_internal_docs(
        self, query: str, repo: str = ""
    ) -> dict[str, Any]:
        repo = repo or settings.GITHUB_REPO
        if not repo:
            return {"results": [], "note": "GITHUB_REPO not configured"}

        # Use GitHub code search in the docs/wiki directory
        gh_query = f"{query} repo:{repo} path:docs"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.github.com/search/code",
                    params={"q": gh_query, "per_page": 5},
                    headers={
                        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                items = [
                    {"name": i["name"], "path": i["path"], "html_url": i["html_url"]}
                    for i in data.get("items", [])
                ]
                return {"results": items, "total": data.get("total_count", 0)}
        except Exception as e:  # noqa: BLE001
            return {"results": [], "error": str(e)}
