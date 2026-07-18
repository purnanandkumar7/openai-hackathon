"""
Agents API router.

Endpoints:
  GET  /agents/runs/{run_id}              – get a single agent run
  GET  /agents/incidents/{incident_id}    – list all runs for an incident
  GET  /agents/incidents/{id}/findings    – aggregated findings for an incident
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.agent_run import AgentRun
from app.schemas.agent import AgentRunResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunResponse,
    summary="Get a single agent run",
)
async def get_agent_run(run_id: uuid.UUID, db: DBDep) -> AgentRunResponse:
    """Fetch details of a specific agent run."""
    stmt = select(AgentRun).where(AgentRun.id == run_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AgentRun {run_id} not found",
        )
    return AgentRunResponse.model_validate(run)


@router.get(
    "/incidents/{incident_id}",
    response_model=list[AgentRunResponse],
    summary="List agent runs for an incident",
)
async def list_agent_runs(incident_id: uuid.UUID, db: DBDep) -> list[AgentRunResponse]:
    """Return all agent runs associated with an incident, ordered by creation time."""
    stmt = (
        select(AgentRun)
        .where(AgentRun.incident_id == incident_id)
        .order_by(AgentRun.created_at.asc())
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return [AgentRunResponse.model_validate(r) for r in runs]


@router.get(
    "/incidents/{incident_id}/findings",
    summary="Get aggregated findings for an incident",
    response_model=dict,
)
async def get_incident_findings(
    incident_id: uuid.UUID, db: DBDep
) -> dict:
    """
    Return all agent findings aggregated by agent type for an incident.
    """
    stmt = (
        select(AgentRun)
        .where(
            AgentRun.incident_id == incident_id,
            AgentRun.status == "completed",
        )
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    if not runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed agent runs found for incident {incident_id}",
        )

    aggregated: dict[str, list] = {}
    total_findings = 0
    for run in runs:
        findings = run.findings or []
        aggregated[run.agent_type] = findings
        total_findings += len(findings)

    return {
        "incident_id": str(incident_id),
        "total_findings": total_findings,
        "by_agent": aggregated,
        "run_count": len(runs),
    }
