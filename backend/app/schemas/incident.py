"""
Pydantic schemas for Incident resources.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
class _IncidentBase(BaseModel):
    """Fields shared across create / update / response."""

    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = Field(default=None)
    status: str = Field(
        default="open",
        pattern="^(open|investigating|resolved|closed)$",
    )
    severity: str = Field(
        default="medium",
        pattern="^(critical|high|medium|low)$",
    )
    labels: dict[str, str] | None = None
    affected_services: list[str] | None = None
    source: str | None = None


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class IncidentCreate(_IncidentBase):
    """Schema for POST /incidents."""

    pass


class IncidentUpdate(BaseModel):
    """Schema for PATCH /incidents/{id} – all fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    status: str | None = Field(
        default=None,
        pattern="^(open|investigating|resolved|closed)$",
    )
    severity: str | None = Field(
        default=None,
        pattern="^(critical|high|medium|low)$",
    )
    root_cause: str | None = None
    fix_applied: str | None = None
    resolved_at: datetime | None = None
    labels: dict[str, str] | None = None
    affected_services: list[str] | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class IncidentResponse(_IncidentBase):
    """Full incident representation returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    root_cause: str | None = None
    fix_applied: str | None = None
    contributing_factors: list[str] | None = None
    prevention_steps: list[str] | None = None
    rca_report: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] | None = None


class IncidentList(BaseModel):
    """Paginated list of incidents."""

    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
