"""
NetworkAgent – investigates network-layer issues.

Checks: Services, DNS resolution, Ingress status, NetworkPolicy,
pod connectivity, and certificate expiry.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.agents.kubernetes_agent import _run_kubectl
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class NetworkAgent(BaseAgent):
    """Investigates Kubernetes network configuration and connectivity."""

    agent_type = "network"

    tools = [
        {
            "name": "get_services",
            "description": "List Kubernetes Services and their endpoints in a namespace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "label_selector": {"type": "string"},
                },
                "required": ["namespace"],
            },
        },
        {
            "name": "check_endpoints",
            "description": "Check if a Service has ready endpoints (pods behind it).",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "service_name": {"type": "string"},
                },
                "required": ["namespace", "service_name"],
            },
        },
        {
            "name": "check_dns",
            "description": (
                "Check CoreDNS pod health and test DNS resolution for a hostname "
                "from within the cluster."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "FQDN or service name to resolve",
                    },
                    "namespace": {"type": "string", "description": "Namespace context for resolution"},
                },
                "required": ["hostname", "namespace"],
            },
        },
        {
            "name": "get_ingress",
            "description": "List Ingress resources and their rules, TLS config, and backend status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "ingress_name": {"type": "string"},
                },
                "required": ["namespace"],
            },
        },
        {
            "name": "get_network_policies",
            "description": (
                "List NetworkPolicy objects in a namespace to identify traffic restrictions "
                "that might block pod communication."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                },
                "required": ["namespace"],
            },
        },
        {
            "name": "check_cert_expiry",
            "description": "Check TLS certificate expiry for a given host:port.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer", "default": 443},
                },
                "required": ["host"],
            },
        },
        {
            "name": "test_connectivity",
            "description": (
                "Test TCP connectivity between two pods or from a pod to an external endpoint "
                "by running a netcat / curl command inside the cluster."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source_namespace": {"type": "string"},
                    "source_pod": {"type": "string"},
                    "target_host": {"type": "string"},
                    "target_port": {"type": "integer"},
                },
                "required": ["source_namespace", "source_pod", "target_host", "target_port"],
            },
        },
    ]

    async def run(self) -> dict[str, Any]:
        await self._emit_progress("NetworkAgent starting investigation")

        system_prompt = (
            "You are a Kubernetes networking expert. Investigate network-layer issues: "
            "service discovery failures, DNS problems, ingress mis-configurations, "
            "NetworkPolicy blocking traffic, and TLS/certificate issues. "
            "Report each finding with severity and a concrete fix."
        )

        user_message = (
            f"Incident Context:\n{self._build_context_summary()}\n\n"
            "Investigate the network layer. Check services in affected namespaces, "
            "verify DNS, inspect Ingress rules, and look for blocking NetworkPolicies."
        )

        summary = await self._run_agent_loop(system_prompt, user_message, max_iterations=8)
        await self._emit_progress("NetworkAgent investigation complete")

        return {
            "findings": self._findings,
            "actions_taken": self._actions,
            "token_usage": self._token_usage,
            "summary": summary,
        }

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_get_services(
        self, namespace: str, label_selector: str = ""
    ) -> dict[str, Any]:
        args = ["get", "svc", "-n", namespace, "-o", "wide"]
        if label_selector:
            args += ["-l", label_selector]
        return await _run_kubectl(*args)

    async def _tool_check_endpoints(
        self, namespace: str, service_name: str
    ) -> dict[str, Any]:
        result = await _run_kubectl(
            "get", "endpoints", service_name, "-n", namespace, "-o", "yaml"
        )
        return result

    async def _tool_check_dns(self, hostname: str, namespace: str) -> dict[str, Any]:
        # Check CoreDNS pods
        coredns = await _run_kubectl(
            "get", "pods", "-n", "kube-system", "-l", "k8s-app=kube-dns", "-o", "wide"
        )
        # Run a DNS lookup from a debug pod in the namespace
        nslookup = await _run_kubectl(
            "run", "dns-test", "--image=busybox:1.36", "--restart=Never",
            "--rm", "-it", "-n", namespace,
            "--", "nslookup", hostname,
        )
        return {"coredns_pods": coredns, "nslookup": nslookup}

    async def _tool_get_ingress(
        self, namespace: str, ingress_name: str = ""
    ) -> dict[str, Any]:
        args = ["get", "ingress", "-n", namespace, "-o", "yaml"]
        if ingress_name:
            args.insert(2, ingress_name)
        return await _run_kubectl(*args)

    async def _tool_get_network_policies(self, namespace: str) -> dict[str, Any]:
        return await _run_kubectl(
            "get", "networkpolicy", "-n", namespace, "-o", "yaml"
        )

    async def _tool_check_cert_expiry(
        self, host: str, port: int = 443
    ) -> dict[str, Any]:
        import asyncio
        import ssl

        try:
            ctx = ssl.create_default_context()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ctx), timeout=10
            )
            cert = writer.get_extra_info("ssl_object").getpeercert()
            writer.close()
            await writer.wait_closed()
            return {"host": host, "port": port, "cert": cert, "error": None}
        except Exception as e:  # noqa: BLE001
            return {"host": host, "port": port, "cert": None, "error": str(e)}

    async def _tool_test_connectivity(
        self,
        source_namespace: str,
        source_pod: str,
        target_host: str,
        target_port: int,
    ) -> dict[str, Any]:
        result = await _run_kubectl(
            "exec", source_pod, "-n", source_namespace, "--",
            "nc", "-zv", "-w", "5", target_host, str(target_port),
        )
        return result
