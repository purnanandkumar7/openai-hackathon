"""
Prometheus MCP Server wrapper.

Wraps a Prometheus MCP server (e.g. `mcp-prometheus`) that exposes the
Prometheus HTTP API as MCP tools.

Tools exposed:
  • query_metric   – instant PromQL query
  • query_range    – range PromQL query
  • get_alerts     – fetch active Alertmanager alerts
  • get_dashboard  – retrieve a Grafana dashboard JSON (if configured)
  • list_metrics   – list all metric names matching a regex
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.mcp.client import MCPClient

logger = structlog.get_logger(__name__)
settings = get_settings()


class PrometheusMCPServer(MCPClient):
    """
    HTTP-based MCP wrapper for Prometheus / Alertmanager.

    Unlike the stdio clients this one communicates directly with the
    Prometheus HTTP API. This avoids requiring an npm package while
    providing the same tool interface.
    """

    server_name = "prometheus-mcp"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._base = str(settings.PROMETHEUS_URL).rstrip("/")

    async def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "query_metric",
                "description": "Execute an instant PromQL query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "time": {"type": "string", "description": "RFC3339 or Unix timestamp"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "query_range",
                "description": "Execute a range PromQL query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "step": {"type": "string", "default": "60s"},
                    },
                    "required": ["query", "start", "end"],
                },
            },
            {
                "name": "get_alerts",
                "description": "Fetch active Alertmanager alerts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Alertmanager label filter e.g. 'severity=critical'",
                        }
                    },
                },
            },
            {
                "name": "get_dashboard",
                "description": "Retrieve a Grafana dashboard JSON by UID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dashboard_uid": {"type": "string"},
                        "grafana_url": {"type": "string"},
                        "grafana_token": {"type": "string"},
                    },
                    "required": ["dashboard_uid", "grafana_url"],
                },
            },
            {
                "name": "list_metrics",
                "description": "List all Prometheus metric names matching an optional regex.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "match": {
                            "type": "string",
                            "description": "Regex pattern e.g. 'kube_pod.*'",
                        }
                    },
                },
            },
        ]

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            raise NotImplementedError(f"Unknown tool: {tool_name}")
        return await handler(**arguments)

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_query_metric(
        self, query: str, time: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, str] = {"query": query}
        if time:
            params["time"] = time
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/api/v1/query", params=params, timeout=15
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _tool_query_range(
        self,
        query: str,
        start: str,
        end: str,
        step: str = "60s",
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "step": step},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _tool_get_alerts(self, filter: str = "") -> dict[str, Any]:
        """Fetch active alerts from Alertmanager."""
        # Derive Alertmanager URL by convention (same host, port 9093)
        am_base = self._base.replace(":9090", ":9093")
        params: dict[str, str] = {}
        if filter:
            params["filter"] = filter
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{am_base}/api/v2/alerts",
                    params=params,
                    timeout=10,
                )
                resp.raise_for_status()
                return {"alerts": resp.json()}
        except Exception as e:  # noqa: BLE001
            # Fall back to Prometheus rules endpoint
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base}/api/v1/alerts", timeout=10
                )
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]

    async def _tool_get_dashboard(
        self,
        dashboard_uid: str,
        grafana_url: str,
        grafana_token: str = "",
    ) -> dict[str, Any]:
        headers = {}
        if grafana_token:
            headers["Authorization"] = f"Bearer {grafana_token}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{grafana_url.rstrip('/')}/api/dashboards/uid/{dashboard_uid}",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _tool_list_metrics(self, match: str = "") -> dict[str, Any]:
        params: dict[str, str] = {}
        if match:
            params["match[]"] = match
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/api/v1/label/__name__/values",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    # ── Convenience methods ──────────────────────────────────────────────────

    async def query_metric(self, query: str, time: str | None = None) -> dict[str, Any]:
        return await self._tool_query_metric(query, time)

    async def get_alerts(self, filter: str = "") -> dict[str, Any]:
        return await self._tool_get_alerts(filter)
