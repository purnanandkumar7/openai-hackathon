"""
Slack MCP Server wrapper.

Provides Slack messaging and channel management via the Slack Web API.
Used by the notification service to post incident updates and RCA summaries.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.mcp.client import MCPClient

logger = structlog.get_logger(__name__)
settings = get_settings()

_SLACK_API = "https://slack.com/api"


class SlackMCPServer(MCPClient):
    """
    HTTP-based MCP wrapper for the Slack Web API.

    Provides tools for posting messages, creating threads, and
    looking up channel information.
    """

    server_name = "slack-mcp"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._headers = {
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "post_message", "description": "Post a message to a Slack channel."},
            {"name": "post_thread_reply", "description": "Reply in a Slack thread."},
            {"name": "create_channel", "description": "Create a new Slack channel."},
            {"name": "invite_to_channel", "description": "Invite users to a channel."},
            {"name": "list_channels", "description": "List accessible Slack channels."},
            {"name": "upload_file", "description": "Upload a file to Slack."},
        ]

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            raise NotImplementedError(f"Unknown Slack tool: {tool_name}")
        return await handler(**arguments)

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_post_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_SLACK_API}/chat.postMessage",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return {"error": data.get("error", "unknown")}
            return {"ts": data["ts"], "channel": data["channel"]}

    async def _tool_post_thread_reply(
        self, channel: str, thread_ts: str, text: str
    ) -> dict[str, Any]:
        return await self._tool_post_message(channel, text, thread_ts=thread_ts)

    async def _tool_create_channel(
        self, name: str, is_private: bool = True
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_SLACK_API}/conversations.create",
                json={"name": name, "is_private": is_private},
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return {"error": data.get("error")}
            return {
                "channel_id": data["channel"]["id"],
                "name": data["channel"]["name"],
            }

    async def _tool_invite_to_channel(
        self, channel_id: str, user_ids: list[str]
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_SLACK_API}/conversations.invite",
                json={"channel": channel_id, "users": ",".join(user_ids)},
                headers=self._headers,
                timeout=10,
            )
            data = resp.json()
            return {"ok": data.get("ok"), "error": data.get("error")}

    async def _tool_list_channels(
        self, types: str = "public_channel,private_channel", limit: int = 50
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_SLACK_API}/conversations.list",
                params={"types": types, "limit": limit},
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            channels = [
                {"id": c["id"], "name": c["name"], "is_private": c.get("is_private")}
                for c in data.get("channels", [])
            ]
            return {"channels": channels}

    async def _tool_upload_file(
        self, channel: str, filename: str, content: str | bytes, title: str = ""
    ) -> dict[str, Any]:
        files = {"file": (filename, content)}
        data = {"channels": channel, "filename": filename}
        if title:
            data["title"] = title

        headers = {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_SLACK_API}/files.upload",
                data=data,
                files=files,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            return {"ok": result.get("ok"), "file_id": result.get("file", {}).get("id")}

    # ── Convenience methods ──────────────────────────────────────────────────

    async def post_incident_alert(
        self,
        channel: str,
        incident_id: str,
        title: str,
        severity: str,
        description: str,
    ) -> dict[str, Any]:
        """Post a formatted incident alert with Block Kit."""
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }.get(severity, "⚪")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} Incident: {title}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:* {severity.upper()}"},
                    {"type": "mrkdwn", "text": f"*ID:* `{incident_id}`"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": description[:300]},
            },
            {"type": "divider"},
        ]
        return await self._tool_post_message(
            channel=channel,
            text=f"{severity_emoji} Incident: {title}",
            blocks=blocks,
        )

    async def post_rca_summary(
        self,
        channel: str,
        thread_ts: str,
        incident_id: str,
        rca_report: dict[str, Any],
    ) -> dict[str, Any]:
        """Post an RCA summary as a thread reply."""
        root_cause = rca_report.get("root_cause", "Under investigation")
        fix = rca_report.get("fix_applied", "Pending")
        confidence = rca_report.get("confidence_score", 0)

        text = (
            f"*🔍 Atlas AI RCA Complete* (Incident `{incident_id}`)\n\n"
            f"*Root Cause:* {root_cause}\n"
            f"*Fix Applied:* {fix}\n"
            f"*AI Confidence:* {confidence:.0%}"
        )
        return await self._tool_post_message(
            channel=channel, text=text, thread_ts=thread_ts
        )
