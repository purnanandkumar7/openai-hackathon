"""
MultiAgentCoordinator – orchestrates the full investigation workflow.

Flow:
  1. Run PlanningAgent to determine which specialists to activate.
  2. Launch all specialist agents concurrently with asyncio.gather.
  3. Collect findings from all agents.
  4. Run RCAAgent to synthesise findings into a structured RCA report.
  5. Persist results to the database.
  6. Emit real-time progress via WebSocket callback.
"""

from __future__ import annotations

import asyncio
import importlib
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.rca_agent import RCAAgent
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Map agent name → dotted module.ClassName path
_AGENT_REGISTRY: dict[str, str] = {
    "kubernetes": "app.agents.kubernetes_agent.KubernetesAgent",
    "github": "app.agents.github_agent.GitHubAgent",
    "storage": "app.agents.storage_agent.StorageAgent",
    "network": "app.agents.network_agent.NetworkAgent",
    "security": "app.agents.security_agent.SecurityAgent",
    "documentation": "app.agents.documentation_agent.DocumentationAgent",
    "cost": "app.agents.cost_agent.CostAgent",
}


def _load_agent_class(dotted_path: str) -> type[BaseAgent]:
    """Dynamically import an agent class by dotted module path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)  # type: ignore[no-any-return]


class MultiAgentCoordinator:
    """
    Orchestrates a full multi-agent incident investigation.

    Usage::

        coordinator = MultiAgentCoordinator(
            incident=incident_row,
            db=db_session,
            progress_callback=ws_send,
        )
        result = await coordinator.investigate()
    """

    def __init__(
        self,
        incident: Any,  # models.Incident ORM object
        db: AsyncSession,
        progress_callback: Any | None = None,
    ) -> None:
        self._incident = incident
        self._db = db
        self._progress_callback = progress_callback
        self._log = logger.bind(incident_id=str(incident.id))

    # ── Public entry point ───────────────────────────────────────────────────

    async def investigate(self) -> dict[str, Any]:
        """
        Run the full investigation pipeline.

        Returns a summary dict with rca_report and per-agent results.
        """
        incident_context = self._build_incident_context()
        self._log.info("Investigation started")
        await self._update_incident_status("investigating")

        try:
            # 1. Planning phase
            plan_result = await self._run_planning_phase(incident_context)
            tasks = plan_result.get("plan", {}).get("tasks", [])
            if not tasks:
                self._log.warning("Empty plan, activating all agents")
                tasks = [
                    {"agent": name, "priority": i + 1}
                    for i, name in enumerate(_AGENT_REGISTRY)
                ]

            # 2. Specialist agents phase (concurrent)
            agent_results = await self._run_specialist_agents(
                incident_context, tasks
            )

            # 3. Collect findings per agent
            all_findings: dict[str, list[dict[str, Any]]] = {}
            for agent_type, result in agent_results.items():
                if isinstance(result, Exception):
                    self._log.error(
                        "Agent failed", agent=agent_type, error=str(result)
                    )
                    all_findings[agent_type] = []
                else:
                    all_findings[agent_type] = result.get("findings", [])
                    await self._persist_agent_run(agent_type, result)

            # 4. RCA synthesis
            await self._emit("rca_agent", "Synthesising root cause analysis…")
            rca_agent = RCAAgent(
                incident_context=incident_context,
                all_findings=all_findings,
                progress_callback=self._progress_callback,
            )
            rca_result = await rca_agent.run()
            rca_report = rca_result.get("rca_report", {})

            # 5. Persist RCA + close incident
            await self._persist_rca(rca_report, all_findings)
            self._log.info("Investigation complete")
            await self._emit("coordinator", "Investigation complete.")

            return {
                "incident_id": str(self._incident.id),
                "rca_report": rca_report,
                "agent_results": {
                    k: {
                        "findings_count": len(v),
                        "status": "ok" if not isinstance(agent_results.get(k), Exception) else "failed",
                    }
                    for k, v in all_findings.items()
                },
            }

        except Exception as exc:
            self._log.exception("Investigation pipeline failed", error=str(exc))
            await self._update_incident_status("open")
            raise

    # ── Pipeline phases ──────────────────────────────────────────────────────

    async def _run_planning_phase(
        self, incident_context: dict[str, Any]
    ) -> dict[str, Any]:
        await self._emit("planning", "Analysing incident and building investigation plan…")
        planner = PlanningAgent(
            incident_context=incident_context,
            progress_callback=self._progress_callback,
        )
        result = await planner.run()
        await self._persist_agent_run("planning", result)
        return result

    async def _run_specialist_agents(
        self,
        incident_context: dict[str, Any],
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Launch all planned agents concurrently."""
        coroutines: dict[str, Any] = {}

        for task in tasks:
            agent_name = task.get("agent", "")
            dotted_path = _AGENT_REGISTRY.get(agent_name)
            if not dotted_path:
                continue

            # Enrich context with task-specific focus
            ctx = dict(incident_context)
            if task.get("focus"):
                ctx["focus"] = task["focus"]

            agent_cls = _load_agent_class(dotted_path)
            agent_instance = agent_cls(
                incident_context=ctx,
                progress_callback=self._progress_callback,
                # Pass DB session to DocumentationAgent
                **({"db_session": self._db} if agent_name == "documentation" else {}),
            )
            coroutines[agent_name] = agent_instance.run()

        if not coroutines:
            return {}

        names = list(coroutines.keys())
        await self._emit("coordinator", f"Launching {len(names)} agents: {', '.join(names)}")

        results_list = await asyncio.gather(
            *coroutines.values(), return_exceptions=True
        )

        return dict(zip(names, results_list))

    # ── Database helpers ─────────────────────────────────────────────────────

    async def _persist_agent_run(
        self, agent_type: str, result: dict[str, Any]
    ) -> None:
        from app.models.agent_run import AgentRun

        run = AgentRun(
            id=uuid.uuid4(),
            incident_id=self._incident.id,
            agent_type=agent_type,
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            findings=result.get("findings", []),
            actions_taken=result.get("actions_taken", []),
            token_usage=result.get("token_usage"),
        )
        self._db.add(run)
        await self._db.flush()

    async def _persist_rca(
        self,
        rca_report: dict[str, Any],
        all_findings: dict[str, list[dict[str, Any]]],
    ) -> None:
        from sqlalchemy import update

        from app.models.incident import Incident

        stmt = (
            update(Incident)
            .where(Incident.id == self._incident.id)
            .values(
                status="resolved",
                resolved_at=datetime.now(timezone.utc),
                rca_report=rca_report,
                root_cause=rca_report.get("root_cause"),
                fix_applied=rca_report.get("fix_applied"),
                contributing_factors=[
                    cf.get("factor") for cf in rca_report.get("contributing_factors", [])
                ],
                prevention_steps=[
                    ps.get("action") for ps in rca_report.get("prevention_steps", [])
                ],
            )
        )
        await self._db.execute(stmt)
        await self._db.flush()

    async def _update_incident_status(self, status: str) -> None:
        from sqlalchemy import update

        from app.models.incident import Incident

        stmt = (
            update(Incident)
            .where(Incident.id == self._incident.id)
            .values(status=status)
        )
        await self._db.execute(stmt)
        await self._db.flush()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_incident_context(self) -> dict[str, Any]:
        inc = self._incident
        return {
            "id": str(inc.id),
            "title": inc.title,
            "description": inc.description or "",
            "severity": inc.severity,
            "status": inc.status,
            "affected_services": inc.affected_services or [],
            "labels": inc.labels or {},
            "source": inc.source,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "prior_findings": [],
        }

    async def _emit(self, agent: str, message: str) -> None:
        if self._progress_callback:
            try:
                await self._progress_callback(agent, message)
            except Exception:  # noqa: BLE001
                pass
