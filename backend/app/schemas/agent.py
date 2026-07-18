"""
Pydantic schemas for AgentRun resources.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentFinding(BaseModel):
    """A single observation reported by an agent."""

    category: str = Field(..., description="Category e.g. 'pod_crash', 'disk_pressure'")
    severity: str = Field(
        default="medium",
        pattern="^(critical|high|medium|low|info)$",
    )
    title: str
    detail: str
    evidence: dict[str, Any] | None = None
    recommended_action: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class AgentAction(BaseModel):
    """A tool call or remediation step taken by an agent."""

    tool_name: str
    input_args: dict[str, Any]
    output: Any = None
    success: bool = True
    duration_ms: int | None = None
    timestamp: datetime | None = None


class AgentRunResponse(BaseModel):
    """Full agent run representation returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    agent_type: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    findings: list[AgentFinding] | None = None
    actions_taken: list[AgentAction] | None = None
    error_message: str | None = None
    token_usage: dict[str, int] | None = None
