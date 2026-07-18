"""
AgentRun SQLAlchemy model.

Records a single execution of an AI agent within an incident investigation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class AgentRun(Base):
    """Tracks the lifecycle and output of one agent invocation."""

    __tablename__ = "agent_runs"

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

    # ── Agent identity ───────────────────────────────────────────────────────
    agent_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment=(
            "One of: planning | kubernetes | github | storage | network | "
            "security | documentation | cost | rca"
        ),
    )

    # ── Lifecycle ────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        # Allowed: pending | running | completed | failed | cancelled
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Output ───────────────────────────────────────────────────────────────
    findings: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured findings reported by the agent.",
    )
    actions_taken: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of tool calls / remediation steps executed.",
    )
    error_message: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="Error detail if the run failed.",
    )
    token_usage: Mapped[dict[str, int] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="OpenAI token consumption: {prompt, completion, total}.",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    incident: Mapped[Any] = relationship(
        "Incident",
        back_populates="agent_runs",
    )

    def __repr__(self) -> str:
        return (
            f"<AgentRun id={self.id} agent={self.agent_type} status={self.status}>"
        )
