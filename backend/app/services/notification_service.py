"""
NotificationService – sends alerts via Slack, Jira, and GitHub.

Called by the investigation pipeline at key milestones:
  • Incident opened → Slack alert + Jira ticket
  • Investigation complete → Slack RCA summary thread reply
  • Resolution approved → Jira ticket update
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import get_settings
from app.models.incident import Incident

logger = structlog.get_logger(__name__)
settings = get_settings()


class NotificationService:
    """Dispatches notifications across integrated platforms."""

    def __init__(self) -> None:
        self._slack_ts: dict[str, str] = {}  # incident_id → slack thread ts

    # ── Slack ────────────────────────────────────────────────────────────────

    async def post_incident_alert(self, incident: Incident) -> str | None:
        """
        Post a Slack alert for a new incident.

        Returns the thread timestamp for follow-up replies.
        """
        if not settings.SLACK_BOT_TOKEN:
            logger.debug("Slack not configured – skipping alert")
            return None

        from app.mcp.slack_mcp import SlackMCPServer

        try:
            slack = SlackMCPServer()
            result = await slack.post_incident_alert(
                channel=settings.SLACK_INCIDENT_CHANNEL,
                incident_id=str(incident.id),
                title=incident.title,
                severity=incident.severity,
                description=incident.description or "",
            )
            ts = result.get("ts")
            if ts:
                self._slack_ts[str(incident.id)] = ts
            logger.info(
                "Slack alert posted",
                incident_id=str(incident.id),
                channel=settings.SLACK_INCIDENT_CHANNEL,
            )
            return ts
        except Exception as exc:  # noqa: BLE001
            logger.warning("Slack alert failed", error=str(exc))
            return None

    async def post_rca_complete(
        self, incident: Incident, investigation_result: dict[str, Any]
    ) -> None:
        """Post an RCA summary as a thread reply to the original incident alert."""
        if not settings.SLACK_BOT_TOKEN:
            return

        from app.mcp.slack_mcp import SlackMCPServer

        thread_ts = self._slack_ts.get(str(incident.id))
        if not thread_ts:
            # Try posting a standalone message if no thread ts available
            thread_ts = await self.post_incident_alert(incident) or ""

        rca_report = investigation_result.get("rca_report", {})
        try:
            slack = SlackMCPServer()
            await slack.post_rca_summary(
                channel=settings.SLACK_INCIDENT_CHANNEL,
                thread_ts=thread_ts,
                incident_id=str(incident.id),
                rca_report=rca_report,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Slack RCA post failed", error=str(exc))

    async def post_investigation_progress(
        self,
        incident_id: str,
        agent: str,
        message: str,
    ) -> None:
        """Post a brief progress update as a thread reply (throttled)."""
        if not settings.SLACK_BOT_TOKEN:
            return

        thread_ts = self._slack_ts.get(incident_id)
        if not thread_ts:
            return

        from app.mcp.slack_mcp import SlackMCPServer

        try:
            slack = SlackMCPServer()
            await slack._tool_post_thread_reply(
                channel=settings.SLACK_INCIDENT_CHANNEL,
                thread_ts=thread_ts,
                text=f"🤖 `{agent}`: {message}",
            )
        except Exception:  # noqa: BLE001
            pass  # Non-fatal

    # ── Jira ─────────────────────────────────────────────────────────────────

    async def create_jira_ticket(self, incident: Incident) -> str | None:
        """
        Create a Jira incident ticket.

        Returns the Jira issue key (e.g. 'OPS-42').
        """
        if not settings.JIRA_API_TOKEN:
            logger.debug("Jira not configured – skipping ticket creation")
            return None

        from app.mcp.jira_mcp import JiraMCPServer

        try:
            jira = JiraMCPServer()
            result = await jira.create_incident_ticket(
                incident_title=incident.title,
                incident_id=str(incident.id),
                severity=incident.severity,
                description=incident.description or "",
            )
            key = result.get("key")
            logger.info("Jira ticket created", key=key, incident_id=str(incident.id))
            return key
        except Exception as exc:  # noqa: BLE001
            logger.warning("Jira ticket creation failed", error=str(exc))
            return None

    async def update_jira_with_rca(
        self, issue_key: str, rca_report: dict[str, Any]
    ) -> None:
        """Add an RCA summary comment to an existing Jira issue."""
        if not settings.JIRA_API_TOKEN or not issue_key:
            return

        from app.mcp.jira_mcp import JiraMCPServer

        try:
            jira = JiraMCPServer()
            root_cause = rca_report.get("root_cause", "Under investigation")
            fix = rca_report.get("fix_applied", "Pending")

            comment = (
                f"*Atlas AI RCA Complete*\n\n"
                f"*Root Cause:* {root_cause}\n"
                f"*Fix Applied:* {fix}\n\n"
                f"Full RCA report available in the Atlas AI dashboard."
            )
            await jira._tool_add_comment(issue_key, comment)

            # Transition to "Resolved" if possible
            await jira._tool_transition_issue(issue_key, "Resolved")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Jira RCA update failed", error=str(exc))

    # ── GitHub ───────────────────────────────────────────────────────────────

    async def create_github_issue(
        self, incident: Incident, rca_report: dict[str, Any] | None = None
    ) -> str | None:
        """
        Create a GitHub issue for tracking incident follow-up tasks.

        Returns the issue URL.
        """
        if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO:
            return None

        from app.mcp.github_mcp import GitHubMCPServer

        owner, repo = settings.GITHUB_REPO.split("/", 1)
        body_lines = [
            f"## Incident: {incident.title}",
            f"**Severity:** {incident.severity.upper()}",
            f"**Atlas AI Incident ID:** `{incident.id}`",
            "",
            f"**Description:**\n{incident.description or 'N/A'}",
        ]
        if rca_report:
            body_lines += [
                "",
                f"**Root Cause:** {rca_report.get('root_cause', 'TBD')}",
                f"**Fix Applied:** {rca_report.get('fix_applied', 'Pending')}",
            ]
            steps = rca_report.get("prevention_steps", [])
            if steps:
                body_lines += ["", "**Prevention Steps:**"]
                for ps in steps:
                    action = ps.get("action", str(ps)) if isinstance(ps, dict) else str(ps)
                    body_lines.append(f"- [ ] {action}")

        try:
            async with GitHubMCPServer() as gh:
                result = await gh.create_issue(
                    owner=owner,
                    repo=repo,
                    title=f"[Incident] {incident.title}",
                    body="\n".join(body_lines),
                    labels=["incident", f"severity:{incident.severity}"],
                )
                url = result if isinstance(result, str) else str(result)
                logger.info("GitHub issue created", url=url)
                return url
        except Exception as exc:  # noqa: BLE001
            logger.warning("GitHub issue creation failed", error=str(exc))
            return None
