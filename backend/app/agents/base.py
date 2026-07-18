"""
BaseAgent – abstract base class for all Atlas AI specialist agents.

Every agent:
  1. Receives an incident context dict on construction.
  2. Implements `run()` to perform its investigation.
  3. Reports structured findings via `report_findings()`.
  4. Delegates tool I/O through `call_tool()` which can be backed by either
     a local MCP client or a plain function.

Tool definitions follow the OpenAI Responses API format
(client.responses.create with a `tools` parameter).
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
ToolDef = dict[str, Any]   # OpenAI function-tool definition
ToolResult = Any            # Arbitrary tool output


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------
class BaseAgent(ABC):
    """
    Abstract base for all Atlas AI investigation agents.

    Subclasses must implement:
        • ``tools``   – list of OpenAI tool definitions (class attribute)
        • ``run()``   – async entry-point that drives the investigation
    """

    #: Agent type identifier – overridden by each subclass
    agent_type: str = "base"

    #: OpenAI tool definitions in the format expected by the Responses API
    tools: list[ToolDef] = []

    def __init__(
        self,
        incident_context: dict[str, Any],
        *,
        run_id: str | None = None,
        progress_callback: Any | None = None,
    ) -> None:
        """
        Args:
            incident_context: Dict containing incident id, title, description,
                              severity, affected_services, prior findings, etc.
            run_id:           Optional AgentRun DB id for logging correlation.
            progress_callback: Optional async callable(agent_type, message) for
                               real-time WebSocket streaming.
        """
        self.incident_context = incident_context
        self.run_id = run_id
        self.progress_callback = progress_callback

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._findings: list[dict[str, Any]] = []
        self._actions: list[dict[str, Any]] = []
        self._token_usage: dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
        self._log = logger.bind(agent=self.agent_type, run_id=run_id)

    # ── Public interface ────────────────────────────────────────────────────

    @abstractmethod
    async def run(self) -> dict[str, Any]:
        """
        Execute the investigation.

        Returns a summary dict with at minimum:
          { "findings": [...], "actions_taken": [...], "token_usage": {...} }
        """
        ...

    def report_findings(self) -> list[dict[str, Any]]:
        """Return a copy of all collected findings."""
        return list(self._findings)

    def report_actions(self) -> list[dict[str, Any]]:
        """Return a copy of all executed actions."""
        return list(self._actions)

    def token_usage(self) -> dict[str, int]:
        """Return accumulated OpenAI token usage for this run."""
        return dict(self._token_usage)

    # ── Tool execution ──────────────────────────────────────────────────────

    async def call_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Dispatch to a tool implementation.

        Looks up ``_tool_<tool_name>`` on the subclass.  Records the action.
        """
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            raise NotImplementedError(
                f"Agent {self.agent_type!r} has no handler for tool {tool_name!r}"
            )

        start = time.perf_counter()
        try:
            result = await handler(**kwargs)
            success = True
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc)}
            success = False
            self._log.warning("Tool call failed", tool=tool_name, error=str(exc))

        duration_ms = int((time.perf_counter() - start) * 1000)
        self._actions.append(
            {
                "tool_name": tool_name,
                "input_args": kwargs,
                "output": result,
                "success": success,
                "duration_ms": duration_ms,
            }
        )
        return result

    # ── OpenAI agentic loop ─────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _run_agent_loop(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_iterations: int = 10,
        additional_tools: list[ToolDef] | None = None,
    ) -> str:
        """
        Drive a tool-using agentic loop using the OpenAI Responses API.

        The loop continues until the model returns a final text response
        (no more tool calls) or ``max_iterations`` is reached.

        Returns the model's final text output.
        """
        tools = self.tools + (additional_tools or [])
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for iteration in range(max_iterations):
            self._log.debug("LLM call", iteration=iteration)

            response = await self._client.responses.create(
                model=settings.OPENAI_MODEL,
                input=messages,
                tools=[
                    {"type": "function", "function": t} for t in tools
                ] if tools else [],
                temperature=settings.OPENAI_TEMPERATURE,
                max_output_tokens=settings.OPENAI_MAX_TOKENS,
            )

            # Accumulate token usage
            if hasattr(response, "usage") and response.usage:
                self._token_usage["prompt"] += response.usage.input_tokens or 0
                self._token_usage["completion"] += response.usage.output_tokens or 0
                self._token_usage["total"] += (
                    (response.usage.input_tokens or 0)
                    + (response.usage.output_tokens or 0)
                )

            # Process output items
            tool_calls_made = False
            final_text: str = ""

            for item in response.output:
                if item.type == "message":
                    for block in item.content:
                        if hasattr(block, "text"):
                            final_text = block.text
                elif item.type == "function_call":
                    tool_calls_made = True
                    fn_name: str = item.name
                    fn_args: dict[str, Any] = json.loads(item.arguments or "{}")

                    await self._emit_progress(f"Calling tool: {fn_name}")
                    tool_output = await self.call_tool(fn_name, **fn_args)

                    # Feed result back into the conversation
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": item.call_id,
                            "type": "function",
                            "function": {
                                "name": fn_name,
                                "arguments": item.arguments,
                            },
                        }],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": item.call_id,
                        "content": json.dumps(tool_output, default=str),
                    })

            if not tool_calls_made:
                return final_text

        self._log.warning("Max iterations reached", iterations=max_iterations)
        return final_text

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _add_finding(
        self,
        category: str,
        title: str,
        detail: str,
        severity: str = "medium",
        evidence: dict[str, Any] | None = None,
        recommended_action: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Append a structured finding to the internal list."""
        self._findings.append(
            {
                "category": category,
                "severity": severity,
                "title": title,
                "detail": detail,
                "evidence": evidence or {},
                "recommended_action": recommended_action,
                "confidence": confidence,
            }
        )

    async def _emit_progress(self, message: str) -> None:
        """Send a progress event to the WebSocket callback if registered."""
        if self.progress_callback:
            try:
                await self.progress_callback(self.agent_type, message)
            except Exception:  # noqa: BLE001
                pass

    def _build_context_summary(self) -> str:
        """Return a compact text summary of the incident context."""
        ctx = self.incident_context
        lines = [
            f"Incident ID  : {ctx.get('id', 'N/A')}",
            f"Title        : {ctx.get('title', 'N/A')}",
            f"Severity     : {ctx.get('severity', 'N/A')}",
            f"Description  : {ctx.get('description', 'N/A')}",
            f"Services     : {', '.join(ctx.get('affected_services', []))}",
        ]
        if ctx.get("prior_findings"):
            lines.append("Prior findings:")
            for f in ctx["prior_findings"][:5]:
                lines.append(f"  [{f.get('severity','?')}] {f.get('title','?')}")
        return "\n".join(lines)

    async def _run_concurrently(
        self, *coroutines: Any, return_exceptions: bool = True
    ) -> list[Any]:
        """Run multiple coroutines concurrently, returning all results."""
        return list(await asyncio.gather(*coroutines, return_exceptions=return_exceptions))
