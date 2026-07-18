"""
Incidents API router.

Endpoints:
  POST   /incidents/                   – create a new incident
  GET    /incidents/                   – list incidents with pagination + filters
  GET    /incidents/{id}               – get one incident
  PATCH  /incidents/{id}               – update incident fields
  DELETE /incidents/{id}               – delete incident
  POST   /incidents/{id}/investigate   – trigger multi-agent investigation
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.incident import Incident
from app.schemas.incident import (
    IncidentCreate,
    IncidentList,
    IncidentResponse,
    IncidentUpdate,
)
from app.services.incident_service import IncidentService

logger = structlog.get_logger(__name__)
router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new incident",
)
async def create_incident(
    payload: IncidentCreate,
    db: DBDep,
) -> IncidentResponse:
    """Create a new incident record."""
    svc = IncidentService(db)
    incident = await svc.create(payload)
    return IncidentResponse.model_validate(incident)


@router.get(
    "/",
    response_model=IncidentList,
    summary="List incidents",
)
async def list_incidents(
    db: DBDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
) -> IncidentList:
    """Return a paginated list of incidents, optionally filtered by status/severity."""
    svc = IncidentService(db)
    items, total = await svc.list(
        page=page, page_size=page_size, status=status, severity=severity
    )
    return IncidentList(
        items=[IncidentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get a single incident",
)
async def get_incident(incident_id: uuid.UUID, db: DBDep) -> IncidentResponse:
    """Fetch a single incident by ID."""
    svc = IncidentService(db)
    incident = await svc.get_or_404(incident_id)
    return IncidentResponse.model_validate(incident)


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Update an incident",
)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    db: DBDep,
) -> IncidentResponse:
    """Partially update an incident."""
    svc = IncidentService(db)
    incident = await svc.update(incident_id, payload)
    return IncidentResponse.model_validate(incident)


@router.delete(
    "/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an incident",
)
async def delete_incident(incident_id: uuid.UUID, db: DBDep) -> None:
    """Permanently delete an incident and all related records."""
    svc = IncidentService(db)
    await svc.delete(incident_id)


# ---------------------------------------------------------------------------
# Investigation trigger
# ---------------------------------------------------------------------------


@router.post(
    "/{incident_id}/investigate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger AI investigation",
    response_model=dict[str, Any],
)
async def trigger_investigation(
    incident_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: DBDep,
) -> dict[str, Any]:
    """
    Trigger a full multi-agent investigation for an incident.

    The investigation runs asynchronously in the background.
    Monitor progress via the WebSocket endpoint `/ws/incidents/{id}/progress`.
    """
    svc = IncidentService(db)
    incident = await svc.get_or_404(incident_id)

    if incident.status not in ("open", "investigating"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot investigate an incident in '{incident.status}' status.",
        )

    # Queue investigation as a background task
    background_tasks.add_task(svc.run_investigation, incident_id)

    logger.info("Investigation queued", incident_id=str(incident_id))
    return {
        "message": "Investigation queued",
        "incident_id": str(incident_id),
        "status": "investigating",
        "progress_url": f"/ws/incidents/{incident_id}/progress",
    }
