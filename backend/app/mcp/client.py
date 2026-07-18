"""
MCPClient – base class for Model Context Protocol server integrations.

Each MCP server wrapper subclasses this and implements `list_tools()` and
`call_tool()` using either stdio transport (subprocess) or SSE/HTTP transport.

Reference: https://modelcontextprotocol.io/docs/concepts/transports
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class MCPClient(ABC):
    """
    Abstract base class for MCP server clients.

    Subclasses choose a transport (stdio or HTTP/SSE) and implement
    the two abstract methods.
    """

    #: Display name for logging
    server_name: str = "mcp"

    def __init__(self, **kwargs: Any) -> None:
        self._log = logger.bind(mcp_server=self.server_name)
        self._connected = False

    # ── Abstract interface ───────────────────────────────────────────────────

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the list of tools exposed by this MCP server."""
        ...

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server and return the result."""
        ...

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        self._connected = True
        self._log.debug("MCP server connected")

    async def disconnect(self) -> None:
        """Tear down the MCP server connection."""
        self._connected = False
        self._log.debug("MCP server disconnected")

    # ── Stdio transport helper ───────────────────────────────────────────────

    async def _stdio_request(
        self,
        proc: asyncio.subprocess.Process,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: int = 1,
    ) -> Any:
        """
        Send a JSON-RPC request over stdin and read the response from stdout.

        Suitable for MCP servers launched as child processes (stdio transport).
        """
        assert proc.stdin is not None and proc.stdout is not None

        request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        proc.stdin.write((request + "\n").encode())
        await proc.stdin.drain()

        line = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
        response = json.loads(line.decode().strip())

        if "error" in response:
            raise RuntimeError(
                f"MCP error from {self.server_name}: {response['error']}"
            )
        return response.get("result")


class StdioMCPClient(MCPClient):
    """
    MCP client that communicates with a server subprocess over stdio.

    Launches the server command as a child process and speaks JSON-RPC 2.0
    over stdin/stdout per the MCP spec.
    """

    #: Command to launch the MCP server
    server_command: list[str] = []
    #: Environment variables to pass to the subprocess
    server_env: dict[str, str] | None = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._proc: asyncio.subprocess.Process | None = None
        self._request_counter = 0

    async def connect(self) -> None:
        if not self.server_command:
            raise ValueError(f"{self.server_name}: server_command not set")

        import os

        env = {**os.environ, **(self.server_env or {})}
        self._proc = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        # MCP initialise handshake
        await self._stdio_request(
            self._proc,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "atlas-ai", "version": "0.1.0"},
            },
            request_id=0,
        )
        await self._connected_event()
        self._connected = True
        self._log.info("MCP stdio server started", command=self.server_command[0])

    async def _connected_event(self) -> None:
        """Send notifications/initialized per MCP spec."""
        assert self._proc and self._proc.stdin
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._proc.stdin.write((notif + "\n").encode())
        await self._proc.stdin.drain()

    async def disconnect(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._proc.kill()
            self._proc = None
        self._connected = False
        self._log.debug("MCP stdio server stopped")

    async def list_tools(self) -> list[dict[str, Any]]:
        assert self._proc, "Not connected"
        self._request_counter += 1
        result = await self._stdio_request(
            self._proc, "tools/list", request_id=self._request_counter
        )
        return result.get("tools", [])  # type: ignore[union-attr]

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        assert self._proc, "Not connected"
        self._request_counter += 1
        result = await self._stdio_request(
            self._proc,
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            request_id=self._request_counter,
        )
        # MCP returns content array; extract text
        content = result.get("content", []) if result else []  # type: ignore[union-attr]
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return "\n".join(texts) if texts else result
