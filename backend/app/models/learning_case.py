"""
LearningCase SQLAlchemy model.

Stores approved incident resolutions and their vector embeddings so the
documentation agent and planning agent can retrieve similar past cases.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class LearningCase(Base):
    """An approved incident resolution stored for future retrieval."""

    __tablename__ = "learning_cases"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Foreign key ──────────────────────────────────────────────────────────
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Resolution ───────────────────────────────────────────────────────────
    resolution_approved: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        index=True,
        comment="True once a human SRE has approved this resolution.",
    )
    resolution_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the resolution.",
    )

    # ── Vector embedding ─────────────────────────────────────────────────────
    embedding_vector: Mapped[list[float] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "OpenAI text-embedding-3-small vector (1536 dims) stored as JSON "
            "array. Use pgvector column for large-scale cosine similarity search."
        ),
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default="text-embedding-3-small",
    )

    # ── Outcome tracking ─────────────────────────────────────────────────────
    outcome_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment=(
            "0.0–1.0 effectiveness score assigned after post-incident review. "
            "Used to weight similar-case retrieval."
        ),
    )
    feedback_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Metadata ─────────────────────────────────────────────────────────────
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    incident: Mapped[Any] = relationship(
        "Incident",
        back_populates="learning_cases",
    )

    def __repr__(self) -> str:
        return (
            f"<LearningCase id={self.id} incident_id={self.incident_id} "
            f"approved={self.resolution_approved} score={self.outcome_score}>"
        )
