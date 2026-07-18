"""
Incident SQLAlchemy model.

Represents a production incident from detection through resolution.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Incident(Base):
    """A production incident managed by Atlas AI."""

    __tablename__ = "incidents"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Core fields ──────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        index=True,
        # Allowed: open | investigating | resolved | closed
    )

    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="medium",
        index=True,
        # Allowed: critical | high | medium | low
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── AI-generated artefacts ───────────────────────────────────────────────
    rca_report: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured RCA report produced by RCAAgent.",
    )
    timeline: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Chronological list of events during the incident.",
    )
    root_cause: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="One-sentence root-cause summary.",
    )
    fix_applied: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the remediation applied.",
    )
    contributing_factors: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    prevention_steps: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ── Metadata ─────────────────────────────────────────────────────────────
    labels: Mapped[dict[str, str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Arbitrary key/value labels (team, service, environment, etc.).",
    )
    affected_services: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Origin of the incident: alertmanager | pagerduty | manual | etc.",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    agent_runs: Mapped[list[Any]] = relationship(
        "AgentRun",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    learning_cases: Mapped[list[Any]] = relationship(
        "LearningCase",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Incident id={self.id} title={self.title!r} status={self.status}>"
