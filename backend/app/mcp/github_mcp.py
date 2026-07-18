"""
GitHub MCP Server wrapper.

Wraps the official `@modelcontextprotocol/server-github` via stdio transport.

Provides tools for searching repos, reading files, listing PRs, and creating
issues without raw GitHub API calls.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.mcp.client import StdioMCPClient

settings = get_settings()


class GitHubMCPServer(StdioMCPClient):
    """
    Wraps the GitHub MCP server process.

    Install via: npm install -g @modelcontextprotocol/server-github
    Requires GITHUB_PERSONAL_ACCESS_TOKEN env var set in server_env.
    """

    server_name = "github-mcp"

    @property
    def server_command(self) -> list[str]:  # type: ignore[override]
        return ["npx", "-y", "@modelcontextprotocol/server-github"]

    @property
    def server_env(self) -> dict[str, str]:  # type: ignore[override]
        return {"GITHUB_PERSONAL_ACCESS_TOKEN": settings.GITHUB_TOKEN}

    # ── Convenience wrappers ─────────────────────────────────────────────────

    async def search_repositories(self, query: str, per_page: int = 10) -> Any:
        return await self.call_tool(
            "search_repositories", {"query": query, "perPage": per_page}
        )

    async def search_code(self, query: str, per_page: int = 5) -> Any:
        return await self.call_tool(
            "search_code", {"query": query, "perPage": per_page}
        )

    async def get_file_contents(
        self, owner: str, repo: str, path: str, ref: str = "main"
    ) -> Any:
        return await self.call_tool(
            "get_file_contents",
            {"owner": owner, "repo": repo, "path": path, "ref": ref},
        )

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 10,
    ) -> Any:
        return await self.call_tool(
            "list_pull_requests",
            {"owner": owner, "repo": repo, "state": state, "perPage": per_page},
        )

    async def get_pull_request(
        self, owner: str, repo: str, pull_number: int
    ) -> Any:
        return await self.call_tool(
            "get_pull_request",
            {"owner": owner, "repo": repo, "pullNumber": pull_number},
        )

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> Any:
        args: dict[str, Any] = {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
        }
        if labels:
            args["labels"] = labels
        return await self.call_tool("create_issue", args)

    async def list_commits(
        self,
        owner: str,
        repo: str,
        sha: str = "main",
        per_page: int = 20,
        since: str | None = None,
    ) -> Any:
        args: dict[str, Any] = {
            "owner": owner,
            "repo": repo,
            "sha": sha,
            "perPage": per_page,
        }
        if since:
            args["since"] = since
        return await self.call_tool("list_commits", args)
