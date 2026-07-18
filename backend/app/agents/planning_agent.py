"""
PlanningAgent – decomposes an incident into investigation subtasks,
launches the appropriate specialist agents, and collects their results.

The planning agent acts as the orchestrator of a single investigation cycle,
choosing which agents to run based on incident severity and context.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Mapping from plan task names → agent class import paths
_AGENT_TASK_MAP = {
    "kubernetes": "app.agents.kubernetes_agent.KubernetesAgent",
    "github": "app.agents.github_agent.GitHubAgent",
    "storage": "app.agents.storage_agent.StorageAgent",
    "network": "app.agents.network_agent.NetworkAgent",
    "security": "app.agents.security_agent.SecurityAgent",
    "documentation": "app.agents.documentation_agent.DocumentationAgent",
    "cost": "app.agents.cost_agent.CostAgent",
}


class PlanningAgent(BaseAgent):
    """
    Decomposes an incident and plans which specialist agents should run.

    Returns a prioritised list of agent tasks with rationale.
    This is consumed by the MultiAgentCoordinator to launch agents concurrently.
    """

    agent_type = "planning"
    tools = []  # Planning is pure reasoning; no external tools needed

    async def run(self) -> dict[str, Any]:
        """Produce an investigation plan for the incident."""
        await self._emit_progress("PlanningAgent analysing incident")

        system_prompt = (
            "You are an expert SRE incident commander. "
            "Given an incident description, produce a structured investigation plan. "
            "Choose which specialist agents to activate and explain why. "
            "Agents available: kubernetes, github, storage, network, security, "
            "documentation, cost. "
            "Output JSON with exactly this structure:\n"
            "{\n"
            '  "plan_summary": "brief rationale",\n'
            '  "tasks": [\n'
            '    {"agent": "agent_name", "priority": 1, "rationale": "why", '
            '"focus": "specific focus area for this agent"}\n'
            "  ],\n"
            '  "hypothesis": "leading hypothesis about root cause",\n'
            '  "estimated_severity": "critical|high|medium|low"\n'
            "}"
        )

        user_message = (
            f"Incident to investigate:\n{self._build_context_summary()}\n\n"
            "Produce an investigation plan. For critical/high severity incidents, "
            "activate all relevant agents. For medium/low, focus on the most likely layers. "
            "Always include documentation agent to check for known issues."
        )

        raw = await self._run_agent_loop(
            system_prompt, user_message, max_iterations=1
        )

        plan = self._parse_plan(raw)
        await self._emit_progress(f"PlanningAgent produced plan: {len(plan['tasks'])} tasks")

        return {
            "plan": plan,
            "findings": self._findings,
            "token_usage": self._token_usage,
        }

    def _parse_plan(self, raw: str) -> dict[str, Any]:
        """Parse the plan JSON from LLM output."""
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
            if "```" in clean:
                clean = clean[: clean.rfind("```")]

        try:
            data = json.loads(clean.strip())
        except json.JSONDecodeError:
            logger.warning("Plan JSON parse failed, using default plan")
            # Default: run all agents for unknown incidents
            data = {
                "plan_summary": "Could not parse LLM plan — running all agents",
                "tasks": [
                    {"agent": name, "priority": i + 1, "rationale": "default", "focus": ""}
                    for i, name in enumerate(_AGENT_TASK_MAP)
                ],
                "hypothesis": "Unknown",
                "estimated_severity": self.incident_context.get("severity", "medium"),
            }

        # Validate task agent names
        valid_tasks = [
            t for t in data.get("tasks", []) if t.get("agent") in _AGENT_TASK_MAP
        ]
        data["tasks"] = sorted(valid_tasks, key=lambda t: t.get("priority", 99))
        return data
