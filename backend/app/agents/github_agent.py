"""
GitHubAgent – investigates code and issue history on GitHub.

Tools:
  • search_issues        – search issues/PRs in a repository
  • get_pr               – fetch a pull-request with diff stat and review status
  • create_issue         – create a GitHub issue (incident tracking)
  • search_code          – search code across the org for patterns
  • get_commit_history   – list recent commits on a branch with messages and authors
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.agents.base import BaseAgent
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

_GH_API = "https://api.github.com"


def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


class GitHubAgent(BaseAgent):
    """Investigates GitHub repositories for incident-related code changes."""

    agent_type = "github"

    tools = [
        {
            "name": "search_issues",
            "description": (
                "Search GitHub issues and pull-requests using GitHub search syntax. "
                "Useful for finding recently merged PRs or related bug reports."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GitHub search query e.g. 'repo:org/repo is:pr is:merged label:bug'",
                    },
                    "per_page": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_pr",
            "description": "Fetch a pull-request by number with diff stats and review status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repo"},
                    "pull_number": {"type": "integer"},
                },
                "required": ["repo", "pull_number"],
            },
        },
        {
            "name": "create_issue",
            "description": "Create a GitHub issue for tracking incident remediation tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repo"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Label names e.g. ['incident', 'bug']",
                    },
                },
                "required": ["repo", "title", "body"],
            },
        },
        {
            "name": "search_code",
            "description": "Search code in GitHub repositories for patterns or file names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GitHub code search query e.g. 'MAX_CONNECTIONS repo:org/repo'",
                    },
                    "per_page": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_commit_history",
            "description": "List recent commits on a repository branch with messages and authors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repo"},
                    "branch": {"type": "string", "default": "main"},
                    "per_page": {"type": "integer", "default": 20},
                    "since": {
                        "type": "string",
                        "description": "ISO 8601 timestamp – only commits after this",
                    },
                },
                "required": ["repo"],
            },
        },
    ]

    async def run(self) -> dict[str, Any]:
        """Investigate code history and issues related to the incident."""
        await self._emit_progress("GitHubAgent starting investigation")

        system_prompt = (
            "You are a senior software engineer investigating a production incident. "
            "Use GitHub tools to find recently merged PRs, commits, or issues that "
            "could be related to this incident. Look for config changes, dependency bumps, "
            "and related bug reports. Summarise findings with severity and evidence."
        )

        user_message = (
            f"Incident Context:\n{self._build_context_summary()}\n\n"
            f"Default repository: {settings.GITHUB_REPO or 'unknown'}\n\n"
            "Search for GitHub PRs merged in the last 48 hours, recent commits, "
            "and any open issues related to the affected services. "
            "Identify if any code change likely caused this incident."
        )

        summary = await self._run_agent_loop(system_prompt, user_message, max_iterations=8)
        await self._emit_progress("GitHubAgent investigation complete")

        return {
            "findings": self._findings,
            "actions_taken": self._actions,
            "token_usage": self._token_usage,
            "summary": summary,
        }

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_search_issues(
        self, query: str, per_page: int = 10
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(headers=_gh_headers()) as client:
            resp = await client.get(
                f"{_GH_API}/search/issues",
                params={"q": query, "per_page": per_page, "sort": "updated"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            # Return lightweight summary
            items = [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "html_url": i["html_url"],
                    "created_at": i["created_at"],
                    "updated_at": i["updated_at"],
                    "labels": [la["name"] for la in i.get("labels", [])],
                    "body_preview": (i.get("body") or "")[:300],
                }
                for i in data.get("items", [])
            ]
            return {"total_count": data["total_count"], "items": items}

    async def _tool_get_pr(self, repo: str, pull_number: int) -> dict[str, Any]:
        async with httpx.AsyncClient(headers=_gh_headers()) as client:
            resp = await client.get(
                f"{_GH_API}/repos/{repo}/pulls/{pull_number}", timeout=15
            )
            resp.raise_for_status()
            pr = resp.json()
            return {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "merged": pr.get("merged", False),
                "merged_at": pr.get("merged_at"),
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "additions": pr.get("additions"),
                "deletions": pr.get("deletions"),
                "changed_files": pr.get("changed_files"),
                "html_url": pr["html_url"],
                "user": pr["user"]["login"],
                "body_preview": (pr.get("body") or "")[:500],
                "head_ref": pr["head"]["ref"],
                "base_ref": pr["base"]["ref"],
            }

    async def _tool_create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(headers=_gh_headers()) as client:
            payload: dict[str, Any] = {"title": title, "body": body}
            if labels:
                payload["labels"] = labels
            resp = await client.post(
                f"{_GH_API}/repos/{repo}/issues", json=payload, timeout=15
            )
            resp.raise_for_status()
            issue = resp.json()
            return {
                "number": issue["number"],
                "html_url": issue["html_url"],
                "created_at": issue["created_at"],
            }

    async def _tool_search_code(
        self, query: str, per_page: int = 5
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(headers=_gh_headers()) as client:
            resp = await client.get(
                f"{_GH_API}/search/code",
                params={"q": query, "per_page": per_page},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            items = [
                {
                    "name": i["name"],
                    "path": i["path"],
                    "repository": i["repository"]["full_name"],
                    "html_url": i["html_url"],
                }
                for i in data.get("items", [])
            ]
            return {"total_count": data["total_count"], "items": items}

    async def _tool_get_commit_history(
        self,
        repo: str,
        branch: str = "main",
        per_page: int = 20,
        since: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"sha": branch, "per_page": per_page}
        if since:
            params["since"] = since
        async with httpx.AsyncClient(headers=_gh_headers()) as client:
            resp = await client.get(
                f"{_GH_API}/repos/{repo}/commits", params=params, timeout=15
            )
            resp.raise_for_status()
            commits = [
                {
                    "sha": c["sha"][:8],
                    "message": c["commit"]["message"].split("\n")[0],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"],
                    "html_url": c["html_url"],
                }
                for c in resp.json()
            ]
            return {"branch": branch, "commits": commits}
