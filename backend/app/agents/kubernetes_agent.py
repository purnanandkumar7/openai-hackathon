"""
KubernetesAgent – investigates Kubernetes-layer issues.

Tools:
  • get_pods            – list pods in a namespace (with status filtering)
  • get_pod_logs        – fetch recent log lines from a container
  • describe_pod        – full pod description (events, conditions, resource reqs)
  • get_events          – cluster / namespace events ordered by last timestamp
  • get_pvc             – list / describe PersistentVolumeClaims
  • get_nodes           – node status, capacity, conditions
  • get_deployments     – deployment status and rollout history
  • exec_kubectl        – low-level kubectl passthrough for arbitrary queries
"""

from __future__ import annotations

import asyncio
import shlex
from typing import Any

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)

_KUBECTL_TIMEOUT = 30  # seconds


async def _run_kubectl(*args: str) -> dict[str, Any]:
    """Execute kubectl and return {stdout, stderr, returncode}."""
    cmd = ["kubectl", *args]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_KUBECTL_TIMEOUT
        )
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "returncode": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"stdout": "", "stderr": "kubectl timed out", "returncode": -1}
    except FileNotFoundError:
        return {"stdout": "", "stderr": "kubectl not found in PATH", "returncode": -1}


class KubernetesAgent(BaseAgent):
    """Investigates Kubernetes infrastructure issues."""

    agent_type = "kubernetes"

    tools = [
        {
            "name": "get_pods",
            "description": (
                "List pods in a Kubernetes namespace, optionally filtered by "
                "label selector or field selector (e.g. status.phase=Failed)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Kubernetes namespace"},
                    "label_selector": {
                        "type": "string",
                        "description": "Label selector e.g. 'app=myapp'",
                    },
                    "field_selector": {
                        "type": "string",
                        "description": "Field selector e.g. 'status.phase=Failed'",
                    },
                    "all_namespaces": {
                        "type": "boolean",
                        "description": "If true, query all namespaces",
                    },
                },
                "required": ["namespace"],
            },
        },
        {
            "name": "get_pod_logs",
            "description": "Fetch recent log lines from a pod container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name": {"type": "string"},
                    "container": {"type": "string"},
                    "tail_lines": {
                        "type": "integer",
                        "description": "Number of lines from the end",
                        "default": 100,
                    },
                    "previous": {
                        "type": "boolean",
                        "description": "Fetch logs from previous container instance",
                        "default": False,
                    },
                },
                "required": ["namespace", "pod_name"],
            },
        },
        {
            "name": "describe_pod",
            "description": (
                "Get full description of a pod including events, conditions, "
                "resource requests and limits, and volume mounts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name": {"type": "string"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
        {
            "name": "get_events",
            "description": (
                "List Kubernetes events ordered by last timestamp. "
                "Useful for spotting OOMKills, failed scheduling, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "field_selector": {"type": "string"},
                    "all_namespaces": {"type": "boolean"},
                },
                "required": ["namespace"],
            },
        },
        {
            "name": "get_pvc",
            "description": "List PersistentVolumeClaims and their bound PV status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pvc_name": {"type": "string", "description": "Specific PVC name (optional)"},
                },
                "required": ["namespace"],
            },
        },
        {
            "name": "get_nodes",
            "description": (
                "Get node status, capacity, allocatable resources, and "
                "conditions (MemoryPressure, DiskPressure, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label_selector": {"type": "string"},
                },
            },
        },
        {
            "name": "get_deployments",
            "description": (
                "Get deployment status including replica counts, rollout "
                "history, and pod template hash."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "deployment_name": {"type": "string"},
                },
                "required": ["namespace"],
            },
        },
        {
            "name": "exec_kubectl",
            "description": (
                "Execute an arbitrary kubectl command. "
                "Do NOT use for destructive operations without explicit human approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "string",
                        "description": "kubectl arguments as a single string e.g. 'get cm -n kube-system -o yaml'",
                    }
                },
                "required": ["args"],
            },
        },
    ]

    # ── Entry point ─────────────────────────────────────────────────────────

    async def run(self) -> dict[str, Any]:
        """Investigate Kubernetes-layer issues for the incident."""
        await self._emit_progress("KubernetesAgent starting investigation")

        system_prompt = (
            "You are an expert Site Reliability Engineer specialised in Kubernetes. "
            "Investigate the incident by querying cluster state. "
            "Look for: CrashLoopBackOff, OOMKilled, Pending pods, evictions, "
            "resource exhaustion, failed deployments, and related events. "
            "Use available tools systematically. "
            "Summarise every finding with category, severity, and recommended action."
        )

        user_message = (
            f"Incident Context:\n{self._build_context_summary()}\n\n"
            "Investigate the Kubernetes layer. Start with pods in the affected "
            "namespace, look for anomalies, check events, describe any problematic "
            "pods, and assess nodes. Report all findings."
        )

        summary = await self._run_agent_loop(system_prompt, user_message, max_iterations=12)
        await self._emit_progress("KubernetesAgent investigation complete")

        return {
            "findings": self._findings,
            "actions_taken": self._actions,
            "token_usage": self._token_usage,
            "summary": summary,
        }

    # ── Tool implementations ─────────────────────────────────────────────────

    async def _tool_get_pods(
        self,
        namespace: str,
        label_selector: str = "",
        field_selector: str = "",
        all_namespaces: bool = False,
    ) -> dict[str, Any]:
        args = ["get", "pods", "-o", "wide"]
        if all_namespaces:
            args.append("--all-namespaces")
        else:
            args += ["-n", namespace]
        if label_selector:
            args += ["-l", label_selector]
        if field_selector:
            args += ["--field-selector", field_selector]
        return await _run_kubectl(*args)

    async def _tool_get_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: str = "",
        tail_lines: int = 100,
        previous: bool = False,
    ) -> dict[str, Any]:
        args = ["logs", pod_name, "-n", namespace, f"--tail={tail_lines}"]
        if container:
            args += ["-c", container]
        if previous:
            args.append("--previous")
        return await _run_kubectl(*args)

    async def _tool_describe_pod(
        self, namespace: str, pod_name: str
    ) -> dict[str, Any]:
        return await _run_kubectl("describe", "pod", pod_name, "-n", namespace)

    async def _tool_get_events(
        self,
        namespace: str,
        field_selector: str = "",
        all_namespaces: bool = False,
    ) -> dict[str, Any]:
        args = ["get", "events", "--sort-by=.lastTimestamp"]
        if all_namespaces:
            args.append("--all-namespaces")
        else:
            args += ["-n", namespace]
        if field_selector:
            args += ["--field-selector", field_selector]
        return await _run_kubectl(*args)

    async def _tool_get_pvc(
        self, namespace: str, pvc_name: str = ""
    ) -> dict[str, Any]:
        args = ["get", "pvc", "-n", namespace, "-o", "wide"]
        if pvc_name:
            args.insert(2, pvc_name)
        return await _run_kubectl(*args)

    async def _tool_get_nodes(self, label_selector: str = "") -> dict[str, Any]:
        args = ["get", "nodes", "-o", "wide"]
        if label_selector:
            args += ["-l", label_selector]
        result = await _run_kubectl(*args)
        # Also get node descriptions for conditions
        describe_result = await _run_kubectl("describe", "nodes")
        return {"list": result, "describe": describe_result}

    async def _tool_get_deployments(
        self, namespace: str, deployment_name: str = ""
    ) -> dict[str, Any]:
        args = ["get", "deployment", "-n", namespace, "-o", "wide"]
        if deployment_name:
            args.insert(2, deployment_name)
        result = await _run_kubectl(*args)
        if deployment_name:
            history = await _run_kubectl(
                "rollout", "history", f"deployment/{deployment_name}", "-n", namespace
            )
            return {"status": result, "history": history}
        return {"status": result}

    async def _tool_exec_kubectl(self, args: str) -> dict[str, Any]:
        """Execute arbitrary kubectl command (readonly operations only)."""
        parsed = shlex.split(args)
        # Safety gate – block destructive verbs
        destructive = {"delete", "drain", "taint", "patch", "apply", "create", "replace"}
        if parsed and parsed[0] in destructive:
            return {
                "error": (
                    f"Destructive verb '{parsed[0]}' requires explicit human approval. "
                    "Skipping."
                )
            }
        return await _run_kubectl(*parsed)
