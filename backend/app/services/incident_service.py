"""
IncidentService – business logic for incident lifecycle management.

Handles CRUD operations and orchestrates the investigation workflow
by creating a MultiAgentCoordinator and injecting it with a WebSocket
progress callback.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import _session_factory
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentUpdate

logger = structlog.get_logger(__name__)


class IncidentService:
    """All incident-related business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, payload: IncidentCreate) -> Incident:
        """Persist a new incident and return the ORM instance."""
        incident = Incident(
            id=uuid.uuid4(),
            title=payload.title,
            description=payload.description,
            status=payload.status,
            severity=payload.severity,
            labels=payload.labels,
            affected_services=payload.affected_services,
            source=payload.source,
        )
        self._db.add(incident)
        await self._db.flush()
        await self._db.refresh(incident)
        logger.info("Incident created", incident_id=str(incident.id))
        return incident

    async def get_or_404(self, incident_id: uuid.UUID) -> Incident:
        """Return an incident or raise HTTP 404."""
        stmt = select(Incident).where(Incident.id == incident_id)
        result = await self._db.execute(stmt)
        incident = result.scalar_one_or_none()
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found",
            )
        return incident

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        severity: str | None = None,
    ) -> tuple[list[Incident], int]:
        """Return a paginated list of incidents."""
        query = select(Incident)
        count_query = select(func.count()).select_from(Incident)

        if status:
            query = query.where(Incident.status == status)
            count_query = count_query.where(Incident.status == status)
        if severity:
            query = query.where(Incident.severity == severity)
            count_query = count_query.where(Incident.severity == severity)

        query = (
            query.order_by(Incident.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        total = (await self._db.execute(count_query)).scalar_one()
        incidents = (await self._db.execute(query)).scalars().all()
        return list(incidents), total

    async def update(
        self, incident_id: uuid.UUID, payload: IncidentUpdate
    ) -> Incident:
        """Apply a partial update to an incident."""
        incident = await self.get_or_404(incident_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(incident, field, value)

        await self._db.flush()
        await self._db.refresh(incident)
        logger.info("Incident updated", incident_id=str(incident_id))
        return incident

    async def delete(self, incident_id: uuid.UUID) -> None:
        """Delete an incident and cascade to related records."""
        incident = await self.get_or_404(incident_id)
        await self._db.delete(incident)
        await self._db.flush()
        logger.info("Incident deleted", incident_id=str(incident_id))

    # ── Investigation workflow ────────────────────────────────────────────────

    async def run_investigation(self, incident_id: uuid.UUID) -> dict[str, Any]:
        """
        Launch a multi-agent investigation for the incident.

        This method is designed to run as a FastAPI BackgroundTask.
        It creates a fresh DB session (since the request session may be closed)
        and notifies Slack on completion.
        """
        if _session_factory is None:
            logger.error("DB session factory not available")
            return {}

        async with _session_factory() as db:
            try:
                stmt = select(Incident).where(Incident.id == incident_id)
                result = await db.execute(stmt)
                incident = result.scalar_one_or_none()
                if not incident:
                    logger.error("Incident not found for investigation", id=str(incident_id))
                    return {}

                # Import here to avoid circular deps at module load time
                from app.agents.coordinator import MultiAgentCoordinator
                from app.api.websocket import make_progress_callback
                from app.services.notification_service import NotificationService

                progress_cb = make_progress_callback(str(incident_id))
                coordinator = MultiAgentCoordinator(
                    incident=incident,
                    db=db,
                    progress_callback=progress_cb,
                )

                investigation_result = await coordinator.investigate()

                # Post Slack alert with RCA summary
                try:
                    notif = NotificationService()
                    await notif.post_rca_complete(incident, investigation_result)
                except Exception as notif_err:  # noqa: BLE001
                    logger.warning(
                        "Notification failed (non-fatal)",
                        error=str(notif_err),
                    )

                await db.commit()
                logger.info(
                    "Investigation complete",
                    incident_id=str(incident_id),
                )
                return investigation_result

            except Exception as exc:
                logger.exception(
                    "Investigation failed",
                    incident_id=str(incident_id),
                    error=str(exc),
                )
                await db.rollback()
                return {}
