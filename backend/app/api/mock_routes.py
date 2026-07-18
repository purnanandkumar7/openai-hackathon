"""
Mock routes — served when MOCK_MODE=true.

Replaces every DB-backed endpoint with in-memory responses so the backend
starts with zero external dependencies (no Postgres, no Redis).

All data matches the TypeScript mock-data in the frontend so the UI
displays realistic content when pointed at this server.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import ORJSONResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory mock store
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc).isoformat()

MOCK_INCIDENTS: list[dict[str, Any]] = [
    {
        "id": "inc-0001-0000-0000-000000000001",
        "title": "Production API gateway returning 502 errors",
        "description": "The API gateway is returning HTTP 502 errors for ~40% of requests. Payment service is completely down. Error rate spiked from 0.1% to 38% at 14:23 UTC.",
        "severity": "P1",
        "status": "investigating",
        "created_at": "2025-01-15T14:23:00Z",
        "updated_at": "2025-01-15T14:31:00Z",
        "resolved_at": None,
        "affected_services": ["api-gateway", "payment-service", "checkout-ui"],
        "assigned_agents": ["orchestrator", "log_analyzer", "metric_analyzer"],
        "investigation_id": "inv-0001-0000-0000-000000000001",
        "rca_id": None,
        "metadata": {"environment": "production", "region": "us-east-1"},
    },
    {
        "id": "inc-0002-0000-0000-000000000002",
        "title": "Database connection pool exhaustion in order service",
        "description": "Order service pods are failing to acquire database connections. Connection pool is at 100% utilisation causing cascading failures.",
        "severity": "P1",
        "status": "open",
        "created_at": "2025-01-15T13:45:00Z",
        "updated_at": "2025-01-15T13:50:00Z",
        "resolved_at": None,
        "affected_services": ["order-service", "postgres-primary"],
        "assigned_agents": [],
        "investigation_id": None,
        "rca_id": None,
        "metadata": {"environment": "production"},
    },
    {
        "id": "inc-0003-0000-0000-000000000003",
        "title": "ML recommendation engine OOM crash loop",
        "description": "recommendation-engine pods are in CrashLoopBackOff. OOMKilled events detected. Memory limit is 4Gi but process peaks at 6.8Gi during batch inference.",
        "severity": "P2",
        "status": "investigating",
        "created_at": "2025-01-15T12:10:00Z",
        "updated_at": "2025-01-15T12:20:00Z",
        "resolved_at": None,
        "affected_services": ["recommendation-engine", "product-catalog"],
        "assigned_agents": ["orchestrator", "log_analyzer"],
        "investigation_id": "inv-0003-0000-0000-000000000003",
        "rca_id": None,
        "metadata": {"environment": "production", "namespace": "ml-serving"},
    },
    {
        "id": "inc-0004-0000-0000-000000000004",
        "title": "Kubernetes secret removed — deployment CrashLoopBackOff",
        "description": "api-service pods crash immediately on startup. Logs show: 'Error: SECRET_KEY environment variable not found'. Secret was deleted in PR #847.",
        "severity": "P1",
        "status": "resolved",
        "created_at": "2025-01-15T09:00:00Z",
        "updated_at": "2025-01-15T09:27:00Z",
        "resolved_at": "2025-01-15T09:27:00Z",
        "affected_services": ["api-service", "auth-service"],
        "assigned_agents": ["orchestrator", "log_analyzer", "rca_synthesizer", "fix_recommender"],
        "investigation_id": "inv-0004-0000-0000-000000000004",
        "rca_id": "rca-0004-0000-0000-000000000004",
        "metadata": {"environment": "production", "resolution_time_minutes": 27},
    },
    {
        "id": "inc-0005-0000-0000-000000000005",
        "title": "Redis cache eviction causing DB thundering herd",
        "description": "Redis memory limit reached, triggering mass cache eviction. All requests now hitting PostgreSQL simultaneously. DB CPU at 98%, p99 latency 8.4s.",
        "severity": "P2",
        "status": "resolved",
        "created_at": "2025-01-14T18:30:00Z",
        "updated_at": "2025-01-14T19:15:00Z",
        "resolved_at": "2025-01-14T19:15:00Z",
        "affected_services": ["cache-layer", "postgres-primary", "api-service"],
        "assigned_agents": ["orchestrator", "metric_analyzer", "rca_synthesizer"],
        "investigation_id": "inv-0005-0000-0000-000000000005",
        "rca_id": "rca-0005-0000-0000-000000000005",
        "metadata": {"environment": "production", "resolution_time_minutes": 45},
    },
    {
        "id": "inc-0006-0000-0000-000000000006",
        "title": "TLS certificate expiry — auth service HTTPS failure",
        "description": "auth-service TLS certificate expired at 00:00 UTC. All HTTPS connections being rejected. Users cannot log in.",
        "severity": "P1",
        "status": "resolved",
        "created_at": "2025-01-14T00:05:00Z",
        "updated_at": "2025-01-14T00:43:00Z",
        "resolved_at": "2025-01-14T00:43:00Z",
        "affected_services": ["auth-service", "user-portal"],
        "assigned_agents": ["orchestrator", "log_analyzer", "fix_recommender"],
        "investigation_id": "inv-0006-0000-0000-000000000006",
        "rca_id": "rca-0006-0000-0000-000000000006",
        "metadata": {"environment": "production", "resolution_time_minutes": 38},
    },
    {
        "id": "inc-0007-0000-0000-000000000007",
        "title": "Ingress controller misconfiguration — 404 on all routes",
        "description": "After a Helm upgrade of ingress-nginx, all service routes return 404. The rewrite-target annotation was changed incorrectly.",
        "severity": "P2",
        "status": "resolved",
        "created_at": "2025-01-13T16:00:00Z",
        "updated_at": "2025-01-13T16:22:00Z",
        "resolved_at": "2025-01-13T16:22:00Z",
        "affected_services": ["ingress-nginx", "all-services"],
        "assigned_agents": ["orchestrator", "log_analyzer", "fix_recommender"],
        "investigation_id": None,
        "rca_id": None,
        "metadata": {"environment": "production"},
    },
    {
        "id": "inc-0008-0000-0000-000000000008",
        "title": "Slow query degrading checkout performance",
        "description": "New index missing on orders.user_id column. Full table scans on high-traffic checkout queries causing P95 latency to hit 4.2s (SLO is 500ms).",
        "severity": "P3",
        "status": "closed",
        "created_at": "2025-01-12T11:00:00Z",
        "updated_at": "2025-01-12T12:30:00Z",
        "resolved_at": "2025-01-12T12:30:00Z",
        "affected_services": ["checkout-service", "postgres-primary"],
        "assigned_agents": ["orchestrator", "metric_analyzer"],
        "investigation_id": None,
        "rca_id": None,
        "metadata": {"environment": "production"},
    },
]

MOCK_RCA: dict[str, Any] = {
    "id": "rca-0004-0000-0000-000000000004",
    "incident_id": "inc-0004-0000-0000-000000000004",
    "investigation_id": "inv-0004-0000-0000-000000000004",
    "generated_at": "2025-01-15T09:27:00Z",
    "confidence_score": 0.97,
    "executive_summary": (
        "A missing Kubernetes secret caused the api-service and auth-service to enter "
        "CrashLoopBackOff at 09:00 UTC on 2025-01-15. The SECRET_KEY environment variable "
        "was referenced in the deployment manifest but the corresponding Kubernetes Secret "
        "object was deleted in PR #847 (merged 2025-01-15 08:53 UTC). Atlas AI detected the "
        "root cause within 4 minutes and restored service in 27 minutes with zero data loss."
    ),
    "root_cause": {
        "title": "Kubernetes Secret deleted in PR #847",
        "description": (
            "The api-secret Kubernetes Secret containing SECRET_KEY was deleted in a "
            "cleanup PR (#847) that was intended only to remove unused secrets. "
            "The secret was still actively referenced by the api-service and auth-service "
            "Deployment manifests via envFrom. When the new Deployment rolled out at 09:00 UTC, "
            "pods failed to start because the secret no longer existed."
        ),
        "service": "api-service",
        "component": "kubernetes-secrets",
        "category": "configuration",
    },
    "contributing_factors": [
        {
            "id": "cf-001",
            "title": "No pre-deployment secret existence check",
            "description": "The CI/CD pipeline did not validate that all secrets referenced in envFrom exist before deploying.",
            "category": "process",
            "weight": 0.6,
            "evidence": [
                "kubectl describe deployment api-service: envFrom references 'api-secret' which does not exist",
                "CI pipeline logs show no pre-flight secret validation step",
            ],
        },
        {
            "id": "cf-002",
            "title": "Secret cleanup PR lacked cross-reference check",
            "description": "PR #847 deleted secrets without checking which deployments reference them.",
            "category": "human",
            "weight": 0.3,
            "evidence": [
                "GitHub PR #847: 'cleanup: remove unused secrets'",
                "No automated check was run to detect active secret references",
            ],
        },
    ],
    "timeline": [
        {"id": "tl-001", "timestamp": "2025-01-15T08:53:00Z", "type": "deployment", "title": "PR #847 merged", "description": "Cleanup PR deleting 'api-secret' and 'auth-secret' merged to main.", "service": "github", "severity": "medium"},
        {"id": "tl-002", "timestamp": "2025-01-15T09:00:00Z", "type": "deployment", "title": "api-service Deployment rolled out", "description": "Kubernetes rolled out new api-service pods referencing the now-deleted secret.", "service": "api-service", "severity": "critical"},
        {"id": "tl-003", "timestamp": "2025-01-15T09:00:15Z", "type": "anomaly", "title": "CrashLoopBackOff detected", "description": "Pods enter CrashLoopBackOff: CreateContainerConfigError — secret 'api-secret' not found.", "service": "api-service", "severity": "critical"},
        {"id": "tl-004", "timestamp": "2025-01-15T09:00:30Z", "type": "alert", "title": "PagerDuty alert fired", "description": "High error rate alert triggered. Atlas AI investigation started.", "service": "monitoring", "severity": "high"},
        {"id": "tl-005", "timestamp": "2025-01-15T09:04:00Z", "type": "incident", "title": "Root cause identified by Atlas AI", "description": "Kubernetes Agent found CreateContainerConfigError. GitHub Agent traced deletion to PR #847.", "service": "atlas-ai", "severity": "low"},
        {"id": "tl-006", "timestamp": "2025-01-15T09:20:00Z", "type": "recovery", "title": "Secret recreated, deployment restarted", "description": "SECRET_KEY secret recreated with correct value. kubectl rollout restart triggered.", "service": "api-service", "severity": "low"},
        {"id": "tl-007", "timestamp": "2025-01-15T09:27:00Z", "type": "recovery", "title": "All pods healthy", "description": "All 3 api-service pods Running. Error rate returned to 0%. Incident resolved.", "service": "api-service", "severity": "low"},
    ],
    "fix_recommendations": [
        {
            "id": "fix-001",
            "title": "Add pre-deployment secret existence check to CI/CD",
            "description": "Before any Deployment rollout, the pipeline should verify all envFrom secret references exist in the target namespace.",
            "type": "immediate",
            "priority": "critical",
            "effort": "low",
            "impact": "high",
            "steps": [
                "Add a CI step: kubectl get secret <name> -n <namespace> for each envFrom reference",
                "Fail the pipeline if any referenced secret is missing",
                "Add this check to the Helm pre-upgrade hook as well",
            ],
            "owner": "platform-team",
            "estimated_effort": "2 hours",
        },
        {
            "id": "fix-002",
            "title": "Implement secret lifecycle policy",
            "description": "Require all Kubernetes secrets to be tagged with which workloads reference them. Block deletion if active references exist.",
            "type": "short_term",
            "priority": "high",
            "effort": "medium",
            "impact": "high",
            "steps": [
                "Add annotation atlas.ai/referenced-by to all secrets",
                "Create OPA/Gatekeeper policy preventing deletion of referenced secrets",
                "Update runbook for secret rotation to include reference check",
            ],
            "owner": "security-team",
            "estimated_effort": "1 week",
        },
    ],
    "lessons_learned": [
        {
            "id": "ll-001",
            "category": "prevention",
            "title": "Secret references must be validated before deployment",
            "description": "Infrastructure-as-code cleanup PRs must include automated cross-reference checks.",
            "action_items": [
                "Implement pre-deployment secret validation in CI pipeline",
                "Add OPA policy to prevent deletion of referenced secrets",
                "Create team runbook for safe secret cleanup procedure",
            ],
        },
        {
            "id": "ll-002",
            "category": "detection",
            "title": "Atlas AI detected root cause 4x faster than manual investigation",
            "description": "Automated investigation with concurrent agents reduced MTTR from ~2hr to 27min.",
            "action_items": [
                "Expand Atlas AI coverage to staging environment",
                "Add secret-reference checks to Atlas AI Kubernetes Agent",
            ],
        },
    ],
    "affected_services": ["api-service", "auth-service"],
    "impact_summary": "100% of API traffic failed for 27 minutes affecting ~14,000 active users.",
}

MOCK_AGENTS: list[dict[str, Any]] = [
    {"type": "orchestrator",        "display_name": "Planning Agent",       "description": "Decomposes incidents into investigation tasks",        "icon": "🧩", "total_runs": 124, "success_rate": 0.98, "avg_duration_ms": 2100, "status": "idle",    "findings_count": 87,  "last_run": "2025-01-15T09:04:00Z"},
    {"type": "log_analyzer",        "display_name": "Kubernetes Agent",     "description": "kubectl, pod logs, events, PVCs, node status",         "icon": "⎈",  "total_runs": 118, "success_rate": 0.95, "avg_duration_ms": 8400, "status": "running", "findings_count": 203, "last_run": "2025-01-15T14:25:00Z"},
    {"type": "metric_analyzer",     "display_name": "Metrics Agent",        "description": "Prometheus queries, SLO breaches, anomaly detection",  "icon": "📊", "total_runs": 109, "success_rate": 0.96, "avg_duration_ms": 5200, "status": "running", "findings_count": 178, "last_run": "2025-01-15T14:26:00Z"},
    {"type": "trace_analyzer",      "display_name": "Storage Agent",        "description": "Ceph, CSI drivers, NFS, PVC bindings, disk I/O",       "icon": "💾", "total_runs": 87,  "success_rate": 0.93, "avg_duration_ms": 6100, "status": "idle",    "findings_count": 91,  "last_run": "2025-01-15T09:06:00Z"},
    {"type": "dependency_mapper",   "display_name": "Network Agent",        "description": "DNS, Services, Ingress, NetworkPolicy, connectivity",   "icon": "🌐", "total_runs": 95,  "success_rate": 0.94, "avg_duration_ms": 4800, "status": "idle",    "findings_count": 112, "last_run": "2025-01-15T09:07:00Z"},
    {"type": "hypothesis_generator","display_name": "GitHub Agent",         "description": "PRs, commits, issues, blame, code search",             "icon": "🐙", "total_runs": 103, "success_rate": 0.97, "avg_duration_ms": 3900, "status": "idle",    "findings_count": 156, "last_run": "2025-01-15T09:05:00Z"},
    {"type": "evidence_collector",  "display_name": "Security Agent",       "description": "RBAC, CVEs, secret hygiene, PodSecurityPolicy",        "icon": "🔐", "total_runs": 78,  "success_rate": 0.92, "avg_duration_ms": 7200, "status": "idle",    "findings_count": 67,  "last_run": "2025-01-14T18:40:00Z"},
    {"type": "rca_synthesizer",     "display_name": "Documentation Agent",  "description": "RAG search across runbooks, wikis, past incidents",    "icon": "📚", "total_runs": 89,  "success_rate": 0.91, "avg_duration_ms": 9100, "status": "idle",    "findings_count": 134, "last_run": "2025-01-15T09:08:00Z"},
    {"type": "fix_recommender",     "display_name": "RCA Agent",            "description": "Synthesizes all findings into structured RCA report",  "icon": "📋", "total_runs": 67,  "success_rate": 0.99, "avg_duration_ms": 12000,"status": "idle",    "findings_count": 67,  "last_run": "2025-01-15T09:27:00Z"},
]

MOCK_STATS: dict[str, Any] = {
    "total_incidents": 8,
    "incidents_last_30_days": 8,
    "by_status": {"open": 1, "investigating": 2, "resolved": 4, "closed": 1},
    "by_severity": {"P1": 4, "P2": 3, "P3": 1, "P4": 0},
    "total_agent_runs": 870,
    "learning": {"approved_cases": 12, "average_outcome_score": 0.94},
    "generated_at": _NOW,
}

# In-memory editable incident list (supports POST/PATCH)
_incident_store: dict[str, dict[str, Any]] = {i["id"]: i for i in MOCK_INCIDENTS}

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0", "mode": "mock"}


@router.get("/health/ready", tags=["ops"])
async def readiness() -> dict[str, Any]:
    return {"status": "ready", "checks": {"database": True, "mode": "mock"}}


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.get("/api/v1/incidents", tags=["incidents"])
async def list_incidents(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    items = list(_incident_store.values())
    if status:
        items = [i for i in items if i["status"] == status]
    if severity:
        items = [i for i in items if i["severity"] == severity]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    start = (page - 1) * page_size
    paginated = items[start : start + page_size]
    return {
        "items": paginated,
        "total": len(items),
        "page": page,
        "page_size": page_size,
        "has_more": (start + page_size) < len(items),
    }


@router.post("/api/v1/incidents", tags=["incidents"], status_code=201)
async def create_incident(payload: dict[str, Any]) -> dict[str, Any]:
    new_id = f"inc-{uuid.uuid4().hex[:8]}-0000-0000-000000000000"
    incident: dict[str, Any] = {
        "id": new_id,
        "title": payload.get("title", "Untitled"),
        "description": payload.get("description", ""),
        "severity": payload.get("severity", "P3"),
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "affected_services": payload.get("affected_services", []),
        "assigned_agents": [],
        "investigation_id": None,
        "rca_id": None,
        "metadata": payload.get("metadata", {}),
    }
    _incident_store[new_id] = incident
    return incident


@router.get("/api/v1/incidents/{incident_id}", tags=["incidents"])
async def get_incident(incident_id: str) -> dict[str, Any]:
    incident = _incident_store.get(incident_id)
    if not incident:
        return ORJSONResponse({"detail": f"Incident {incident_id} not found"}, status_code=404)
    return incident


@router.patch("/api/v1/incidents/{incident_id}", tags=["incidents"])
async def update_incident(incident_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    incident = _incident_store.get(incident_id)
    if not incident:
        return ORJSONResponse({"detail": "Not found"}, status_code=404)
    incident.update({k: v for k, v in payload.items() if v is not None})
    incident["updated_at"] = datetime.now(timezone.utc).isoformat()
    return incident


@router.post("/api/v1/incidents/{incident_id}/investigate", tags=["incidents"])
async def trigger_investigation(incident_id: str) -> dict[str, Any]:
    incident = _incident_store.get(incident_id)
    if not incident:
        return ORJSONResponse({"detail": "Not found"}, status_code=404)
    incident["status"] = "investigating"
    incident["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {
        "message": "Investigation queued (mock mode)",
        "incident_id": incident_id,
        "status": "investigating",
        "progress_url": f"/ws/incidents/{incident_id}/progress",
    }


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@router.get("/api/v1/agents", tags=["agents"])
async def list_agents() -> list[dict[str, Any]]:
    return MOCK_AGENTS


@router.get("/api/v1/agents/runs/{run_id}", tags=["agents"])
async def get_agent_run(run_id: str) -> dict[str, Any]:
    return {"id": run_id, "status": "completed", "findings": [], "agent_type": "orchestrator"}


@router.get("/api/v1/agents/incidents/{incident_id}", tags=["agents"])
async def list_agent_runs(incident_id: str) -> list[dict[str, Any]]:
    return []


@router.get("/api/v1/agents/incidents/{incident_id}/findings", tags=["agents"])
async def get_incident_findings(incident_id: str) -> dict[str, Any]:
    return {"incident_id": incident_id, "total_findings": 0, "by_agent": {}, "run_count": 0}


# ---------------------------------------------------------------------------
# RCA
# ---------------------------------------------------------------------------

@router.get("/api/v1/rca/{incident_id}", tags=["rca"])
async def get_rca_report(incident_id: str) -> dict[str, Any]:
    if incident_id == "inc-0004-0000-0000-000000000004":
        return MOCK_RCA
    return ORJSONResponse(
        {"detail": "RCA report not yet generated. Trigger an investigation first."},
        status_code=404,
    )


@router.post("/api/v1/rca/{incident_id}/approve", tags=["rca"])
async def approve_resolution(incident_id: str) -> dict[str, Any]:
    return {
        "message": "Resolution approved and stored for learning",
        "learning_case_id": str(uuid.uuid4()),
        "incident_id": incident_id,
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@router.get("/api/v1/metrics/stats", tags=["metrics"])
async def get_stats() -> dict[str, Any]:
    return MOCK_STATS


@router.get("/api/v1/metrics/agent-summary", tags=["metrics"])
async def get_agent_summary() -> dict[str, Any]:
    agents_summary = {
        a["type"]: {
            "total": a["total_runs"],
            "completed": int(a["total_runs"] * a["success_rate"]),
            "failed": int(a["total_runs"] * (1 - a["success_rate"])),
            "success_rate": a["success_rate"],
        }
        for a in MOCK_AGENTS
    }
    return {"agents": agents_summary}


@router.get("/api/v1/metrics/incidents", tags=["metrics"])
async def get_incident_volume(days: int = 30) -> dict[str, Any]:
    return {
        "period_days": days,
        "data": [
            {"date": "2025-01-09", "count": 2},
            {"date": "2025-01-10", "count": 1},
            {"date": "2025-01-11", "count": 3},
            {"date": "2025-01-12", "count": 1},
            {"date": "2025-01-13", "count": 1},
            {"date": "2025-01-14", "count": 2},
            {"date": "2025-01-15", "count": 3},
        ],
    }


# ---------------------------------------------------------------------------
# WebSocket — simulated real-time agent progress feed
# ---------------------------------------------------------------------------

_AGENT_SEQUENCE = [
    (1.0,  "agent_started",      "orchestrator",         "Planning incident investigation..."),
    (2.0,  "agent_started",      "log_analyzer",         "Connecting to Kubernetes API..."),
    (2.0,  "agent_started",      "metric_analyzer",      "Querying Prometheus metrics..."),
    (3.0,  "agent_progress",     "log_analyzer",         "kubectl get pods -n production"),
    (4.0,  "agent_finding",      "log_analyzer",         "CrashLoopBackOff on api-service pods (3/3 failing)"),
    (5.0,  "agent_progress",     "log_analyzer",         "kubectl logs api-service-7f9d4 --tail=50"),
    (6.0,  "agent_finding",      "log_analyzer",         "Error: SECRET_KEY environment variable not found"),
    (6.5,  "agent_started",      "hypothesis_generator", "Searching GitHub for recent changes..."),
    (7.0,  "agent_completed",    "metric_analyzer",      "Error rate: 0.1% → 38.4% at 14:23 UTC"),
    (8.0,  "agent_finding",      "hypothesis_generator", "PR #847 removed secret 'api-secret' 7 minutes ago"),
    (9.0,  "agent_started",      "evidence_collector",   "Checking RBAC for secret creation permissions..."),
    (10.0, "agent_finding",      "evidence_collector",   "RBAC allows: secret/create in production namespace"),
    (11.0, "agent_completed",    "log_analyzer",         "8 findings collected"),
    (12.0, "agent_completed",    "hypothesis_generator", "Root cause identified with 97% confidence"),
    (13.0, "agent_completed",    "evidence_collector",   "Security check passed"),
    (14.0, "agent_started",      "rca_synthesizer",      "Synthesizing root cause analysis..."),
    (16.0, "agent_completed",    "rca_synthesizer",      "RCA report generated"),
    (17.0, "agent_started",      "fix_recommender",      "Applying fix: recreating missing secret..."),
    (19.0, "agent_finding",      "fix_recommender",      "kubectl create secret generic api-secret — SUCCESS"),
    (20.0, "agent_progress",     "fix_recommender",      "kubectl rollout restart deployment/api-service"),
    (22.0, "agent_finding",      "fix_recommender",      "All 3 pods Running (3/3) — health check 200 OK"),
    (23.0, "agent_completed",    "fix_recommender",      "Fix applied and validated"),
    (24.0, "investigation_completed", "orchestrator",    "Investigation complete. MTTR: 4m 28s"),
]


@router.websocket("/ws/incidents/{incident_id}/progress")
async def ws_progress(websocket: WebSocket, incident_id: str) -> None:
    """Stream simulated agent progress events over WebSocket."""
    await websocket.accept()
    try:
        inv_id = f"inv-mock-{incident_id}"
        # Send initial event
        await websocket.send_text(json.dumps({
            "type": "investigation_started",
            "investigation_id": inv_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"message": f"Atlas AI starting investigation for incident {incident_id}"},
        }))

        prev_delay = 0.0
        for delay, event_type, agent_type, message in _AGENT_SEQUENCE:
            await asyncio.sleep(delay - prev_delay)
            prev_delay = delay
            await websocket.send_text(json.dumps({
                "type": event_type,
                "investigation_id": inv_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "agent_type": agent_type,
                    "message": message,
                    "progress": int((_AGENT_SEQUENCE.index((delay, event_type, agent_type, message)) + 1)
                                    / len(_AGENT_SEQUENCE) * 100),
                },
            }))

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
