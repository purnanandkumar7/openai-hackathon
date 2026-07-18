"""
StorageAgent – investigates storage-layer issues.

Checks: Ceph cluster health, OSD status, PVC binding, CSI node drivers,
NFS mount health, and disk I/O saturation via Prometheus.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.agents.base import BaseAgent
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class StorageAgent(BaseAgent):
    """Investigates persistent storage and volume issues."""

    agent_type = "storage"

    tools = [
        {
            "name": "get_ceph_health",
            "description": "Get overall Ceph cluster health status and active alerts.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_ceph_osds",
            "description": "List Ceph OSD status – show which OSDs are up/down/out.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_down": {
                        "type": "boolean",
                        "description": "Only show down/out OSDs",
                        "default": False,
                    }
                },
            },
        },
        {
            "name": "get_ceph_pools",
            "description": "List Ceph pool utilisation and replication status.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "check_pvc_status",
            "description": (
                "Check PersistentVolumeClaim binding status across all namespaces "
                "or a specific namespace. Identify Pending / Lost PVCs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Leave empty for all namespaces"},
                },
            },
        },
        {
            "name": "check_csi_drivers",
            "description": "Check CSI node driver pods are running on all nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "driver_namespace": {
                        "type": "string",
                        "default": "kube-system",
                    }
                },
            },
        },
        {
            "name": "check_nfs_mounts",
            "description": "Check NFS mount health by querying node mount stats via Prometheus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server": {"type": "string", "description": "NFS server hostname or IP"},
                },
            },
        },
        {
            "name": "query_disk_io",
            "description": (
                "Query Prometheus for disk I/O saturation metrics "
                "(reads/writes per second, await latency)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "node": {"type": "string", "description": "Node hostname or empty for all"},
                    "device": {"type": "string", "description": "Disk device name e.g. sda"},
                },
            },
        },
    ]

    async def run(self) -> dict[str, Any]:
        await self._emit_progress("StorageAgent starting investigation")

        system_prompt = (
            "You are a storage systems expert. Investigate storage issues: "
            "Ceph health, OSD status, PVC binding failures, CSI driver health, "
            "NFS mount problems, and disk I/O saturation. "
            "Report findings with severity (critical/high/medium/low) and recommended fixes."
        )

        user_message = (
            f"Incident Context:\n{self._build_context_summary()}\n\n"
            "Check storage layer health. Start with Ceph overall health, "
            "then check PVCs for the affected namespace, CSI drivers, and disk I/O metrics."
        )

        summary = await self._run_agent_loop(system_prompt, user_message, max_iterations=8)
        await self._emit_progress("StorageAgent investigation complete")

        return {
            "findings": self._findings,
            "actions_taken": self._actions,
            "token_usage": self._token_usage,
            "summary": summary,
        }

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _ceph_api(self, path: str, method: str = "GET") -> dict[str, Any]:
        """Make an authenticated call to the Ceph Dashboard REST API."""
        base = str(settings.CEPH_DASHBOARD_URL).rstrip("/")
        auth = (settings.CEPH_API_USER, settings.CEPH_API_PASSWORD)
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method,
                f"{base}/api{path}",
                auth=auth,
                headers={"Accept": "application/vnd.ceph.api.v1.0+json"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _prometheus_query(self, query: str) -> dict[str, Any]:
        prom_base = str(settings.PROMETHEUS_URL).rstrip("/")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{prom_base}/api/v1/query",
                params={"query": query},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _tool_get_ceph_health(self) -> dict[str, Any]:
        try:
            return await self._ceph_api("/health/minimal")
        except Exception as e:  # noqa: BLE001
            return {"error": str(e), "note": "Ceph Dashboard may not be available"}

    async def _tool_get_ceph_osds(self, filter_down: bool = False) -> dict[str, Any]:
        try:
            data = await self._ceph_api("/osd")
            if filter_down:
                data = [o for o in (data if isinstance(data, list) else []) if not o.get("up")]
            return {"osds": data}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    async def _tool_get_ceph_pools(self) -> dict[str, Any]:
        try:
            return {"pools": await self._ceph_api("/pool?stats=true")}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    async def _tool_check_pvc_status(self, namespace: str = "") -> dict[str, Any]:
        from app.agents.kubernetes_agent import _run_kubectl

        if namespace:
            result = await _run_kubectl("get", "pvc", "-n", namespace, "-o", "wide")
        else:
            result = await _run_kubectl("get", "pvc", "--all-namespaces", "-o", "wide")
        return result

    async def _tool_check_csi_drivers(
        self, driver_namespace: str = "kube-system"
    ) -> dict[str, Any]:
        from app.agents.kubernetes_agent import _run_kubectl

        # Get CSI DaemonSet pods
        result = await _run_kubectl(
            "get", "pods", "-n", driver_namespace,
            "-l", "app.kubernetes.io/component=csi-driver",
            "-o", "wide",
        )
        # Also list CSIDriver objects
        csi_drivers = await _run_kubectl("get", "csidriver")
        return {"pods": result, "csi_drivers": csi_drivers}

    async def _tool_check_nfs_mounts(self, server: str = "") -> dict[str, Any]:
        try:
            q = 'node_filesystem_files{fstype="nfs4"}'
            if server:
                q = f'node_filesystem_files{{fstype="nfs4", mountpoint=~".*{server}.*"}}'
            return await self._prometheus_query(q)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    async def _tool_query_disk_io(
        self, node: str = "", device: str = ""
    ) -> dict[str, Any]:
        label_filter = ""
        if node:
            label_filter += f', instance=~".*{node}.*"'
        if device:
            label_filter += f', device="{device}"'

        queries = {
            "read_iops": f'rate(node_disk_reads_completed_total{{job="node-exporter"{label_filter}}}[5m])',
            "write_iops": f'rate(node_disk_writes_completed_total{{job="node-exporter"{label_filter}}}[5m])',
            "read_latency_ms": f'rate(node_disk_read_time_seconds_total{{job="node-exporter"{label_filter}}}[5m]) * 1000',
        }
        results = {}
        for metric, query in queries.items():
            try:
                results[metric] = await self._prometheus_query(query)
            except Exception as e:  # noqa: BLE001
                results[metric] = {"error": str(e)}
        return results
