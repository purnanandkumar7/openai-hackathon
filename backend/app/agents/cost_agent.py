"""
CostAgent – identifies CPU/GPU waste and idle node spend.

Tools:
  • get_resource_requests     – compare requested vs actual utilisation
  • find_idle_workloads       – detect deployments with near-zero CPU/mem usage
  • get_gpu_utilisation       – check GPU utilisation via DCGM metrics
  • get_node_cost_breakdown   – estimate per-node cost using instance type labels
  • find_rightsizing_ops      – suggest VPA / HPA recommendations
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.agents.base import BaseAgent
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CostAgent(BaseAgent):
    """Identifies cloud waste and cost optimisation opportunities."""

    agent_type = "cost"

    tools = [
        {
            "name": "get_resource_requests",
            "description": (
                "Compare CPU/memory resource requests vs actual utilisation "
                "for all workloads in a namespace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Leave empty for cluster-wide view",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 20,
                        "description": "Return the top K most wasteful workloads",
                    },
                },
            },
        },
        {
            "name": "find_idle_workloads",
            "description": (
                "Find Deployments / StatefulSets with CPU utilisation < 5% "
                "over the last 24 hours (idle but billing resources)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "cpu_threshold": {
                        "type": "number",
                        "default": 0.05,
                        "description": "Utilisation fraction below which a workload is 'idle'",
                    },
                    "hours": {"type": "integer", "default": 24},
                },
            },
        },
        {
            "name": "get_gpu_utilisation",
            "description": (
                "Check GPU utilisation for all GPU nodes using DCGM Prometheus metrics. "
                "Identify GPUs running at < 10% utilisation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "utilisation_threshold": {
                        "type": "number",
                        "default": 0.10,
                        "description": "Flag GPUs below this fraction",
                    }
                },
            },
        },
        {
            "name": "get_node_cost_breakdown",
            "description": (
                "Estimate per-node hourly cost using node labels "
                "(node.kubernetes.io/instance-type, topology.kubernetes.io/region)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label_selector": {
                        "type": "string",
                        "description": "Filter nodes e.g. 'node-role=gpu'",
                    }
                },
            },
        },
        {
            "name": "find_rightsizing_ops",
            "description": (
                "Query VPA (VerticalPodAutoscaler) recommendations or generate "
                "rightsizing suggestions based on Prometheus utilisation data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                },
            },
        },
    ]

    async def run(self) -> dict[str, Any]:
        await self._emit_progress("CostAgent starting analysis")

        system_prompt = (
            "You are a FinOps engineer specialised in Kubernetes cost optimisation. "
            "Analyse CPU, memory, and GPU utilisation to find waste. "
            "Identify idle workloads, over-provisioned nodes, and GPU underutilisation. "
            "Quantify potential savings in vCPU-hours and provide rightsizing recommendations."
        )

        user_message = (
            f"Incident Context:\n{self._build_context_summary()}\n\n"
            "Analyse resource utilisation for the affected services. "
            "Identify any resource waste that may have contributed to the incident "
            "(e.g. OOM due to under-requests, idle GPU nodes consuming budget). "
            "Provide savings estimates and recommendations."
        )

        summary = await self._run_agent_loop(system_prompt, user_message, max_iterations=6)
        await self._emit_progress("CostAgent analysis complete")

        return {
            "findings": self._findings,
            "actions_taken": self._actions,
            "token_usage": self._token_usage,
            "summary": summary,
        }

    # ── Prometheus helpers ───────────────────────────────────────────────────

    async def _prom_query(self, query: str) -> list[dict[str, Any]]:
        prom_base = str(settings.PROMETHEUS_URL).rstrip("/")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{prom_base}/api/v1/query",
                params={"query": query},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("result", [])  # type: ignore[no-any-return]

    async def _prom_query_range(
        self, query: str, hours: int
    ) -> list[dict[str, Any]]:
        import time

        prom_base = str(settings.PROMETHEUS_URL).rstrip("/")
        end = int(time.time())
        start = end - hours * 3600
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{prom_base}/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "step": "1h"},
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("result", [])  # type: ignore[no-any-return]

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_get_resource_requests(
        self, namespace: str = "", top_k: int = 20
    ) -> dict[str, Any]:
        from app.agents.kubernetes_agent import _run_kubectl

        ns_flag = ["-n", namespace] if namespace else ["--all-namespaces"]
        result = await _run_kubectl("top", "pods", *ns_flag, "--sort-by=cpu")

        # Fetch requests from API server
        req_result = await _run_kubectl(
            "get", "pods", *ns_flag,
            "-o",
            "custom-columns="
            "NS:.metadata.namespace,"
            "NAME:.metadata.name,"
            "CPU_REQ:.spec.containers[*].resources.requests.cpu,"
            "MEM_REQ:.spec.containers[*].resources.requests.memory,"
            "CPU_LIM:.spec.containers[*].resources.limits.cpu,"
            "MEM_LIM:.spec.containers[*].resources.limits.memory",
        )
        return {"top_pods": result, "requests": req_result}

    async def _tool_find_idle_workloads(
        self,
        namespace: str = "",
        cpu_threshold: float = 0.05,
        hours: int = 24,
    ) -> dict[str, Any]:
        ns_filter = f', namespace="{namespace}"' if namespace else ""
        query = (
            f'avg_over_time(rate(container_cpu_usage_seconds_total'
            f'{{container!="", container!="POD"{ns_filter}}}[5m])[{hours}h:5m])'
        )
        try:
            results = await self._prom_query(query)
            idle = [
                {
                    "pod": r["metric"].get("pod"),
                    "namespace": r["metric"].get("namespace"),
                    "container": r["metric"].get("container"),
                    "avg_cpu": float(r["value"][1]),
                }
                for r in results
                if float(r["value"][1]) < cpu_threshold
            ]
            idle.sort(key=lambda x: x["avg_cpu"])
            return {"idle_workloads": idle, "threshold": cpu_threshold, "hours": hours}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    async def _tool_get_gpu_utilisation(
        self, utilisation_threshold: float = 0.10
    ) -> dict[str, Any]:
        query = "DCGM_FI_DEV_GPU_UTIL / 100"
        try:
            results = await self._prom_query(query)
            low_util = [
                {
                    "gpu": r["metric"].get("gpu"),
                    "instance": r["metric"].get("instance"),
                    "utilisation": float(r["value"][1]),
                }
                for r in results
                if float(r["value"][1]) < utilisation_threshold
            ]
            return {
                "low_utilisation_gpus": low_util,
                "threshold": utilisation_threshold,
                "total_gpus": len(results),
            }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e), "note": "DCGM metrics may not be available"}

    async def _tool_get_node_cost_breakdown(
        self, label_selector: str = ""
    ) -> dict[str, Any]:
        from app.agents.kubernetes_agent import _run_kubectl

        args = [
            "get", "nodes",
            "-o", "custom-columns="
            "NAME:.metadata.name,"
            "INSTANCE_TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,"
            "REGION:.metadata.labels.topology\\.kubernetes\\.io/region,"
            "ZONE:.metadata.labels.topology\\.kubernetes\\.io/zone,"
            "CPU:.status.capacity.cpu,"
            "MEMORY:.status.capacity.memory",
        ]
        if label_selector:
            args += ["-l", label_selector]
        return await _run_kubectl(*args)

    async def _tool_find_rightsizing_ops(
        self, namespace: str = ""
    ) -> dict[str, Any]:
        from app.agents.kubernetes_agent import _run_kubectl

        # Check for VPA objects
        ns_flag = ["-n", namespace] if namespace else ["--all-namespaces"]
        vpa_result = await _run_kubectl(
            "get", "vpa", *ns_flag, "-o", "yaml"
        )
        # Also check HPA
        hpa_result = await _run_kubectl("get", "hpa", *ns_flag)
        return {"vpa_recommendations": vpa_result, "hpa_status": hpa_result}
