"""
LearningService – stores approved resolutions and computes embeddings.

When an SRE approves an RCA resolution:
  1. Generate an OpenAI embedding for the resolution text.
  2. Store the LearningCase with the embedding and outcome score.
  3. The embedding is later used by DocumentationAgent for semantic retrieval.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.incident import Incident
from app.models.learning_case import LearningCase

logger = structlog.get_logger(__name__)
settings = get_settings()


class LearningService:
    """Manages the learning knowledge base for Atlas AI."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # ── Store approved resolution ────────────────────────────────────────────

    async def store_approved_resolution(
        self,
        incident: Incident,
        resolution_text: str,
        approved_by: str = "anonymous",
        outcome_score: float = 1.0,
        tags: list[str] | None = None,
    ) -> LearningCase:
        """
        Store an approved incident resolution with its embedding vector.

        If a LearningCase already exists for this incident, update it;
        otherwise create a new one.
        """
        # Compute embedding
        embedding = await self._compute_embedding(resolution_text)

        # Check for existing case
        stmt = select(LearningCase).where(LearningCase.incident_id == incident.id)
        result = await self._db.execute(stmt)
        existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing:
            existing.resolution_text = resolution_text
            existing.resolution_approved = True
            existing.embedding_vector = embedding
            existing.outcome_score = outcome_score
            existing.approved_at = now
            existing.approved_by = approved_by
            if tags:
                existing.tags = tags
            await self._db.flush()
            await self._db.refresh(existing)
            logger.info("Learning case updated", case_id=str(existing.id))
            return existing

        # Build enriched text for embedding (include title and root cause)
        case = LearningCase(
            id=uuid.uuid4(),
            incident_id=incident.id,
            resolution_text=resolution_text,
            resolution_approved=True,
            embedding_vector=embedding,
            embedding_model=settings.OPENAI_EMBEDDING_MODEL,
            outcome_score=outcome_score,
            approved_at=now,
            approved_by=approved_by,
            tags=tags or _auto_tags(incident),
            extra_metadata={
                "incident_title": incident.title,
                "severity": incident.severity,
                "root_cause": incident.root_cause,
            },
        )
        self._db.add(case)
        await self._db.flush()
        await self._db.refresh(case)
        logger.info("Learning case created", case_id=str(case.id))
        return case

    # ── Update outcome score ─────────────────────────────────────────────────

    async def update_outcome_score(
        self,
        learning_case_id: uuid.UUID,
        outcome_score: float,
        feedback_notes: str = "",
    ) -> LearningCase | None:
        """
        Update the outcome score of an existing learning case.

        Call this after a post-incident review to adjust the weight of
        this case in future similarity searches.
        """
        stmt = select(LearningCase).where(LearningCase.id == learning_case_id)
        result = await self._db.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            return None

        case.outcome_score = max(0.0, min(1.0, outcome_score))
        if feedback_notes:
            case.feedback_notes = feedback_notes

        await self._db.flush()
        return case

    # ── Stats ────────────────────────────────────────────────────────────────

    async def get_learning_stats(self) -> dict[str, Any]:
        """Return summary statistics for the learning knowledge base."""
        from sqlalchemy import func

        total = (
            await self._db.execute(
                select(func.count()).select_from(LearningCase)
            )
        ).scalar_one()

        approved = (
            await self._db.execute(
                select(func.count())
                .select_from(LearningCase)
                .where(LearningCase.resolution_approved == True)  # noqa: E712
            )
        ).scalar_one()

        avg_score = (
            await self._db.execute(
                select(func.avg(LearningCase.outcome_score))
                .where(LearningCase.outcome_score.isnot(None))
            )
        ).scalar_one()

        return {
            "total_cases": total,
            "approved_cases": approved,
            "average_outcome_score": round(float(avg_score or 0.0), 3),
            "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
        }

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _compute_embedding(self, text: str) -> list[float]:
        """Compute an OpenAI embedding vector for the given text."""
        response = await self._client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text[:8000],  # Respect max token limit
        )
        return response.data[0].embedding


def _auto_tags(incident: Incident) -> list[str]:
    """Generate automatic tags from the incident for better retrieval."""
    tags = [incident.severity, incident.status]
    if incident.affected_services:
        tags.extend(incident.affected_services[:3])
    if incident.labels:
        tags.extend(list(incident.labels.values())[:3])
    return [t for t in tags if t]
