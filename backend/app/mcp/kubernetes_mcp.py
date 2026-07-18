"""
Kubernetes MCP Server wrapper.

Wraps the official `@modelcontextprotocol/server-kubernetes` (or a compatible
open-source equivalent) via stdio transport.

The server exposes tools like:
  • list_pods, get_pod, list_deployments, list_services, etc.
"""

from __future__ import annotations

import os
from typing import Any

from app.config import get_settings
from app.mcp.client import StdioMCPClient

settings = get_settings()


class KubernetesMCPServer(StdioMCPClient):
    """
    Wraps the Kubernetes MCP server process.

    Configure by setting KUBERNETES_CONTEXT in environment.
    Install via: npm install -g @modelcontextprotocol/server-kubernetes
    """

    server_name = "kubernetes-mcp"

    @property
    def server_command(self) -> list[str]:  # type: ignore[override]
        cmd = ["npx", "-y", "@modelcontextprotocol/server-kubernetes"]
        return cmd

    @property
    def server_env(self) -> dict[str, str]:  # type: ignore[override]
        env: dict[str, str] = {}
        if settings.KUBERNETES_CONTEXT:
            env["KUBECONTEXT"] = settings.KUBERNETES_CONTEXT
        if settings.KUBECONFIG_PATH:
            env["KUBECONFIG"] = os.path.expanduser(settings.KUBECONFIG_PATH)
        return env

    # ── Convenience wrappers ─────────────────────────────────────────────────

    async def list_pods(
        self, namespace: str = "default", label_selector: str = ""
    ) -> Any:
        args: dict[str, Any] = {"namespace": namespace}
        if label_selector:
            args["labelSelector"] = label_selector
        return await self.call_tool("list_pods", args)

    async def get_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        tail_lines: int = 100,
        container: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "namespace": namespace,
            "podName": pod_name,
            "tailLines": tail_lines,
        }
        if container:
            args["containerName"] = container
        return await self.call_tool("get_pod_logs", args)

    async def list_deployments(self, namespace: str = "default") -> Any:
        return await self.call_tool("list_deployments", {"namespace": namespace})

    async def list_services(self, namespace: str = "default") -> Any:
        return await self.call_tool("list_services", {"namespace": namespace})

    async def get_events(self, namespace: str = "default") -> Any:
        return await self.call_tool("list_events", {"namespace": namespace})

    async def describe_node(self, node_name: str) -> Any:
        return await self.call_tool("get_node", {"name": node_name})
