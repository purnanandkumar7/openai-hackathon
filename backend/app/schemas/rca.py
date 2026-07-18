"""
Pydantic schemas for RCA (Root Cause Analysis) reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    """A single event in the incident timeline."""

    timestamp: datetime
    description: str
    source: str = Field(..., description="Which agent or system detected this event")
    severity: str = Field(default="info", pattern="^(critical|high|medium|low|info)$")
    metadata: dict[str, Any] | None = None


class ContributingFactor(BaseModel):
    """A factor that contributed to the incident."""

    factor: str
    category: str = Field(
        ...,
        description="e.g. 'infrastructure', 'application', 'human', 'process'",
    )
    impact: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    detail: str | None = None


class PreventionStep(BaseModel):
    """A recommended step to prevent recurrence."""

    action: str
    owner: str | None = None
    priority: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    due_days: int | None = Field(default=None, description="Days to complete from now")
    jira_ticket: str | None = None


class LessonLearned(BaseModel):
    """Lesson learned from this incident."""

    insight: str
    category: str = Field(
        ..., description="e.g. 'monitoring', 'deployment', 'capacity', 'runbook'"
    )
    action_item: str | None = None


class RCAReport(BaseModel):
    """
    Structured Root Cause Analysis report produced by the RCAAgent.

    This is the primary artefact of an Atlas AI investigation.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    incident_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: str = Field(default="rca_agent")
    model_used: str = Field(default="gpt-4o")

    # ── Executive summary ────────────────────────────────────────────────────
    executive_summary: str = Field(
        ..., description="2–3 sentence non-technical summary for stakeholders."
    )

    # ── Root cause ───────────────────────────────────────────────────────────
    root_cause: str = Field(
        ..., description="Single precise technical root-cause statement."
    )
    root_cause_category: str = Field(
        ...,
        description=(
            "One of: application_bug | infrastructure | misconfiguration | "
            "capacity | network | security | human_error | external_dependency"
        ),
    )

    # ── Timeline ─────────────────────────────────────────────────────────────
    timeline: list[TimelineEvent] = Field(default_factory=list)

    # ── Factors & remediation ────────────────────────────────────────────────
    contributing_factors: list[ContributingFactor] = Field(default_factory=list)
    fix_applied: str = Field(..., description="What was done to restore service.")
    fix_permanent: bool = Field(
        default=False, description="True if the fix is permanent, False if a workaround."
    )

    # ── Learning ─────────────────────────────────────────────────────────────
    lessons_learned: list[LessonLearned] = Field(default_factory=list)
    prevention_steps: list[PreventionStep] = Field(default_factory=list)
    similar_past_incidents: list[str] = Field(
        default_factory=list,
        description="IDs of similar past incidents from the learning database.",
    )

    # ── Metrics ─────────────────────────────────────────────────────────────
    time_to_detect_minutes: float | None = None
    time_to_mitigate_minutes: float | None = None
    time_to_resolve_minutes: float | None = None
    services_impacted: list[str] = Field(default_factory=list)
    estimated_blast_radius: str | None = None

    # ── Agent contributions ──────────────────────────────────────────────────
    agent_findings_summary: dict[str, Any] | None = Field(
        default=None,
        description="Map of agent_type → finding count / key observations.",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="AI confidence in this RCA (0.0 = uncertain, 1.0 = high confidence).",
    )
