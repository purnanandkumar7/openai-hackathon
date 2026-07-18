"""
Metrics API router.

Endpoints:
  GET  /metrics/stats           – Atlas AI learning loop and investigation statistics
  GET  /metrics/agent-summary   – per-agent invocation counts and success rates
  GET  /metrics/incidents       – incident volume over time
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.agent_run import AgentRun
from app.models.incident import Incident
from app.models.learning_case import LearningCase

logger = structlog.get_logger(__name__)
router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/stats",
    summary="Atlas AI operational statistics",
    response_model=dict[str, Any],
)
async def get_stats(db: DBDep) -> dict[str, Any]:
    """Return key operational metrics for the Atlas AI platform."""
    now = datetime.now(timezone.utc)
    last_30d = now - timedelta(days=30)

    # Total incidents
    total_incidents = (
        await db.execute(select(func.count()).select_from(Incident))
    ).scalar_one()

    # Incidents by status
    status_counts = (
        await db.execute(
            select(Incident.status, func.count().label("cnt"))
            .group_by(Incident.status)
        )
    ).all()

    # Incidents by severity
    severity_counts = (
        await db.execute(
            select(Incident.severity, func.count().label("cnt"))
            .group_by(Incident.severity)
        )
    ).all()

    # Investigations last 30 days
    recent_investigations = (
        await db.execute(
            select(func.count())
            .select_from(Incident)
            .where(Incident.created_at >= last_30d)
        )
    ).scalar_one()

    # Total agent runs
    total_agent_runs = (
        await db.execute(select(func.count()).select_from(AgentRun))
    ).scalar_one()

    # Learning cases
    approved_cases = (
        await db.execute(
            select(func.count())
            .select_from(LearningCase)
            .where(LearningCase.resolution_approved == True)  # noqa: E712
        )
    ).scalar_one()

    avg_outcome = (
        await db.execute(
            select(func.avg(LearningCase.outcome_score))
            .where(LearningCase.outcome_score.isnot(None))
        )
    ).scalar_one()

    return {
        "total_incidents": total_incidents,
        "incidents_last_30_days": recent_investigations,
        "by_status": {r.status: r.cnt for r in status_counts},
        "by_severity": {r.severity: r.cnt for r in severity_counts},
        "total_agent_runs": total_agent_runs,
        "learning": {
            "approved_cases": approved_cases,
            "average_outcome_score": round(float(avg_outcome or 0), 3),
        },
        "generated_at": now.isoformat(),
    }


@router.get(
    "/agent-summary",
    summary="Per-agent invocation statistics",
    response_model=dict[str, Any],
)
async def get_agent_summary(db: DBDep) -> dict[str, Any]:
    """Return invocation counts and success rates per agent type."""
    rows = (
        await db.execute(
            select(
                AgentRun.agent_type,
                AgentRun.status,
                func.count().label("cnt"),
            ).group_by(AgentRun.agent_type, AgentRun.status)
        )
    ).all()

    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        if row.agent_type not in summary:
            summary[row.agent_type] = {"total": 0, "completed": 0, "failed": 0}
        summary[row.agent_type][row.status] = row.cnt
        summary[row.agent_type]["total"] += row.cnt

    # Compute success rate
    for agent, data in summary.items():
        total = data["total"]
        data["success_rate"] = round(data.get("completed", 0) / max(total, 1), 3)

    return {"agents": summary}


@router.get(
    "/incidents",
    summary="Incident volume over time",
    response_model=dict[str, Any],
)
async def get_incident_volume(
    db: DBDep,
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Return daily incident counts over the specified number of days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        await db.execute(
            select(
                func.date_trunc("day", Incident.created_at).label("day"),
                func.count().label("count"),
            )
            .where(Incident.created_at >= since)
            .group_by(func.date_trunc("day", Incident.created_at))
            .order_by(func.date_trunc("day", Incident.created_at))
        )
    ).all()

    return {
        "period_days": days,
        "data": [{"date": str(r.day)[:10], "count": r.count} for r in rows],
    }
