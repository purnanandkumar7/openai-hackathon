"""
RCAAgent – synthesises findings from all specialist agents into a structured
Root Cause Analysis report.

This agent does NOT call external tools directly. Instead it consumes the
collated findings from the coordinator and uses GPT-4o to reason across them
and produce a structured `RCAReport`.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.config import get_settings
from app.schemas.rca import (
    ContributingFactor,
    LessonLearned,
    PreventionStep,
    RCAReport,
    TimelineEvent,
)

logger = structlog.get_logger(__name__)
settings = get_settings()


class RCAAgent(BaseAgent):
    """Synthesises multi-agent findings into a complete RCA report."""

    agent_type = "rca"
    tools = []  # Pure synthesis — no external tool calls needed

    def __init__(
        self,
        incident_context: dict[str, Any],
        all_findings: dict[str, list[dict[str, Any]]],
        **kwargs: Any,
    ) -> None:
        """
        Args:
            incident_context: Standard incident context dict.
            all_findings: Map of agent_type → list of findings from that agent.
        """
        super().__init__(incident_context, **kwargs)
        self.all_findings = all_findings

    async def run(self) -> dict[str, Any]:
        await self._emit_progress("RCAAgent synthesising findings")

        findings_text = self._format_findings_for_prompt()
        ctx = self._build_context_summary()

        system_prompt = (
            "You are a principal site reliability engineer writing a formal "
            "Root Cause Analysis report. "
            "You have access to findings from specialist agents covering "
            "Kubernetes, GitHub, storage, network, security, cost, and documentation. "
            "Synthesise all findings into a comprehensive, accurate RCA. "
            "Be precise, technical, and actionable. "
            "Output your analysis as a valid JSON object matching the schema provided."
        )

        json_schema = json.dumps(
            {
                "executive_summary": "string",
                "root_cause": "string",
                "root_cause_category": (
                    "application_bug|infrastructure|misconfiguration|"
                    "capacity|network|security|human_error|external_dependency"
                ),
                "timeline": [
                    {
                        "timestamp": "ISO8601",
                        "description": "string",
                        "source": "string",
                        "severity": "critical|high|medium|low|info",
                    }
                ],
                "contributing_factors": [
                    {
                        "factor": "string",
                        "category": "infrastructure|application|human|process",
                        "impact": "critical|high|medium|low",
                        "detail": "string",
                    }
                ],
                "fix_applied": "string",
                "fix_permanent": "bool",
                "lessons_learned": [{"insight": "string", "category": "string"}],
                "prevention_steps": [
                    {
                        "action": "string",
                        "owner": "string",
                        "priority": "critical|high|medium|low",
                        "due_days": "integer",
                    }
                ],
                "time_to_detect_minutes": "number|null",
                "time_to_mitigate_minutes": "number|null",
                "services_impacted": ["string"],
                "estimated_blast_radius": "string",
                "confidence_score": "0.0-1.0",
            },
            indent=2,
        )

        user_message = (
            f"Incident Context:\n{ctx}\n\n"
            f"Agent Findings:\n{findings_text}\n\n"
            f"Produce a JSON RCA report matching this schema:\n{json_schema}\n\n"
            "Focus on the most probable root cause supported by evidence across agents. "
            "Construct a chronological timeline from the evidence. "
            "List 3-5 prevention steps with owners and due dates."
        )

        raw_output = await self._run_agent_loop(
            system_prompt, user_message, max_iterations=1
        )

        rca_report = self._parse_rca_output(raw_output)
        await self._emit_progress("RCAAgent synthesis complete")

        return {
            "findings": self._findings,
            "actions_taken": self._actions,
            "token_usage": self._token_usage,
            "rca_report": rca_report.model_dump(),
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _format_findings_for_prompt(self) -> str:
        """Format all agent findings into a structured text block."""
        lines: list[str] = []
        for agent_type, findings in self.all_findings.items():
            lines.append(f"\n=== {agent_type.upper()} AGENT FINDINGS ===")
            if not findings:
                lines.append("  (no findings)")
                continue
            for i, f in enumerate(findings, 1):
                lines.append(
                    f"  [{i}] [{f.get('severity', 'N/A').upper()}] {f.get('title', 'N/A')}"
                )
                lines.append(f"      Category: {f.get('category', 'N/A')}")
                lines.append(f"      Detail: {f.get('detail', 'N/A')}")
                if f.get("recommended_action"):
                    lines.append(f"      Action: {f['recommended_action']}")
                if f.get("evidence"):
                    lines.append(f"      Evidence: {json.dumps(f['evidence'], default=str)[:200]}")
        return "\n".join(lines)

    def _parse_rca_output(self, raw: str) -> RCAReport:
        """Parse the LLM JSON output into a validated RCAReport."""
        # Strip markdown code fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
            # Remove closing fence
            if "```" in clean:
                clean = clean[: clean.rfind("```")]

        try:
            data = json.loads(clean.strip())
        except json.JSONDecodeError as e:
            logger.warning("RCA JSON parse failed, using defaults", error=str(e))
            data = {}

        incident_id = str(self.incident_context.get("id", "unknown"))
        now = datetime.utcnow()

        # Build timeline
        timeline_events = []
        for t in data.get("timeline", []):
            try:
                timeline_events.append(
                    TimelineEvent(
                        timestamp=t.get("timestamp", now.isoformat()),
                        description=t.get("description", ""),
                        source=t.get("source", "rca_agent"),
                        severity=t.get("severity", "info"),
                    )
                )
            except Exception:  # noqa: BLE001
                pass

        contributing_factors = [
            ContributingFactor(
                factor=cf.get("factor", ""),
                category=cf.get("category", "infrastructure"),
                impact=cf.get("impact", "medium"),
                detail=cf.get("detail"),
            )
            for cf in data.get("contributing_factors", [])
        ]

        lessons = [
            LessonLearned(
                insight=ll.get("insight", ""),
                category=ll.get("category", "general"),
                action_item=ll.get("action_item"),
            )
            for ll in data.get("lessons_learned", [])
        ]

        prevention = [
            PreventionStep(
                action=ps.get("action", ""),
                owner=ps.get("owner"),
                priority=ps.get("priority", "medium"),
                due_days=ps.get("due_days"),
            )
            for ps in data.get("prevention_steps", [])
        ]

        # Build agent findings summary
        agent_summary = {
            agent: len(findings)
            for agent, findings in self.all_findings.items()
        }

        return RCAReport(
            incident_id=incident_id,
            generated_at=now,
            executive_summary=data.get(
                "executive_summary", "RCA synthesis in progress."
            ),
            root_cause=data.get("root_cause", "Under investigation."),
            root_cause_category=data.get("root_cause_category", "infrastructure"),
            timeline=timeline_events,
            contributing_factors=contributing_factors,
            fix_applied=data.get("fix_applied", "Pending."),
            fix_permanent=bool(data.get("fix_permanent", False)),
            lessons_learned=lessons,
            prevention_steps=prevention,
            time_to_detect_minutes=data.get("time_to_detect_minutes"),
            time_to_mitigate_minutes=data.get("time_to_mitigate_minutes"),
            services_impacted=data.get("services_impacted", []),
            estimated_blast_radius=data.get("estimated_blast_radius"),
            agent_findings_summary=agent_summary,
            confidence_score=float(data.get("confidence_score", 0.9)),
        )
