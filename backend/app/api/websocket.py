"""
WebSocket router – real-time agent progress streaming.

Endpoint:
  WS /ws/incidents/{incident_id}/progress

Clients connect before triggering an investigation to receive live
agent progress events as JSON messages.

Message format::

    {
        "type": "progress",
        "agent": "kubernetes",
        "message": "Checking pod status...",
        "timestamp": "2024-01-01T00:00:00Z"
    }
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages active WebSocket connections keyed by incident ID."""

    def __init__(self) -> None:
        # incident_id → list of active websocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, incident_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if incident_id not in self._connections:
            self._connections[incident_id] = []
        self._connections[incident_id].append(websocket)
        logger.debug("WS connected", incident_id=incident_id)

    def disconnect(self, incident_id: str, websocket: WebSocket) -> None:
        if incident_id in self._connections:
            try:
                self._connections[incident_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[incident_id]:
                del self._connections[incident_id]
        logger.debug("WS disconnected", incident_id=incident_id)

    async def broadcast(
        self,
        incident_id: str,
        agent: str,
        message: str,
        event_type: str = "progress",
    ) -> None:
        """Send a JSON event to all subscribers of an incident."""
        if incident_id not in self._connections:
            return

        payload: dict[str, Any] = {
            "type": event_type,
            "agent": agent,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        dead: list[WebSocket] = []
        for ws in list(self._connections[incident_id]):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)

        for ws in dead:
            self.disconnect(incident_id, ws)

    def get_connection_count(self, incident_id: str) -> int:
        return len(self._connections.get(incident_id, []))


# Module-level singleton shared across requests
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/incidents/{incident_id}/progress")
async def incident_progress(
    websocket: WebSocket,
    incident_id: uuid.UUID,
) -> None:
    """
    Stream real-time investigation progress for an incident.

    The client should connect before calling POST /incidents/{id}/investigate.
    Receives JSON events until the investigation completes.
    """
    inc_id = str(incident_id)
    await manager.connect(inc_id, websocket)

    try:
        # Send initial connection acknowledgement
        await websocket.send_json(
            {
                "type": "connected",
                "incident_id": inc_id,
                "message": "Connected to Atlas AI progress stream",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Keep connection alive; the investigation background task
        # broadcasts progress via manager.broadcast()
        while True:
            # Await client messages (e.g. ping/close)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive"})

    except WebSocketDisconnect:
        manager.disconnect(inc_id, websocket)
        logger.info("WS client disconnected", incident_id=inc_id)


# ---------------------------------------------------------------------------
# Progress callback factory (used by services to inject into coordinator)
# ---------------------------------------------------------------------------


def make_progress_callback(incident_id: str):
    """
    Return an async callable that broadcasts agent progress to WS subscribers.

    Usage::

        callback = make_progress_callback(str(incident.id))
        coordinator = MultiAgentCoordinator(incident, db, progress_callback=callback)
    """

    async def _callback(agent: str, message: str) -> None:
        await manager.broadcast(incident_id, agent, message)

    return _callback
