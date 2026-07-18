"""
Jira MCP Server wrapper.

Wraps Jira REST API as an MCP-compatible tool interface.
Provides tools for creating, searching, and updating issues.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.mcp.client import MCPClient

logger = structlog.get_logger(__name__)
settings = get_settings()


class JiraMCPServer(MCPClient):
    """
    HTTP-based MCP wrapper for the Atlassian Jira REST API v3.

    No npm dependency required – communicates directly with the Jira API.
    """

    server_name = "jira-mcp"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._base = f"{str(settings.JIRA_URL).rstrip('/')}/rest/api/3"
        self._auth = (settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "create_issue",
                "description": "Create a Jira issue (bug, task, incident).",
            },
            {
                "name": "search_issues",
                "description": "Search Jira issues using JQL.",
            },
            {
                "name": "get_issue",
                "description": "Fetch a Jira issue by key.",
            },
            {
                "name": "add_comment",
                "description": "Add a comment to a Jira issue.",
            },
            {
                "name": "update_issue",
                "description": "Update fields (status, priority, assignee) of a Jira issue.",
            },
            {
                "name": "transition_issue",
                "description": "Transition a Jira issue to a new status.",
            },
        ]

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            raise NotImplementedError(f"Unknown Jira tool: {tool_name}")
        return await handler(**arguments)

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_create_issue(
        self,
        summary: str,
        description: str = "",
        issue_type: str = "Bug",
        priority: str = "High",
        labels: list[str] | None = None,
        project_key: str = "",
    ) -> dict[str, Any]:
        project_key = project_key or settings.JIRA_PROJECT_KEY
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
            }
        }
        if labels:
            payload["fields"]["labels"] = labels

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/issue",
                json=payload,
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"key": data["key"], "id": data["id"], "url": data["self"]}

    async def _tool_search_issues(
        self, jql: str, max_results: int = 20
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/search",
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": "summary,status,priority,assignee,created,updated",
                },
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            issues = [
                {
                    "key": i["key"],
                    "summary": i["fields"]["summary"],
                    "status": i["fields"]["status"]["name"],
                    "priority": i["fields"].get("priority", {}).get("name"),
                    "created": i["fields"]["created"],
                }
                for i in data.get("issues", [])
            ]
            return {"total": data.get("total", 0), "issues": issues}

    async def _tool_get_issue(self, issue_key: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/issue/{issue_key}",
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _tool_add_comment(
        self, issue_key: str, comment_text: str
    ) -> dict[str, Any]:
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment_text}],
                    }
                ],
            }
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/issue/{issue_key}/comment",
                json=payload,
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return {"id": resp.json()["id"]}

    async def _tool_update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self._base}/issue/{issue_key}",
                json={"fields": fields},
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return {"updated": True, "key": issue_key}

    async def _tool_transition_issue(
        self, issue_key: str, transition_name: str
    ) -> dict[str, Any]:
        # Get available transitions
        async with httpx.AsyncClient() as client:
            t_resp = await client.get(
                f"{self._base}/issue/{issue_key}/transitions",
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
            t_resp.raise_for_status()
            transitions = t_resp.json().get("transitions", [])
            match = next(
                (t for t in transitions if t["name"].lower() == transition_name.lower()),
                None,
            )
            if not match:
                return {
                    "error": f"Transition '{transition_name}' not found",
                    "available": [t["name"] for t in transitions],
                }

            resp = await client.post(
                f"{self._base}/issue/{issue_key}/transitions",
                json={"transition": {"id": match["id"]}},
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return {"transitioned": True, "to": transition_name}

    # ── Convenience methods ──────────────────────────────────────────────────

    async def create_incident_ticket(
        self,
        incident_title: str,
        incident_id: str,
        severity: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a Jira incident ticket with standard Atlas AI metadata."""
        return await self._tool_create_issue(
            summary=f"[Atlas AI] {incident_title}",
            description=(
                f"Incident ID: {incident_id}\n"
                f"Severity: {severity}\n\n"
                f"{description}"
            ),
            issue_type="Bug",
            priority="Critical" if severity in ("critical", "high") else "High",
            labels=["atlas-ai", "incident", f"severity-{severity}"],
        )
