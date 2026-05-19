"""WebSocket connection manager for debate updates."""

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.snapshot_provider: Callable[[str], dict[str, Any] | None] | None = None

    async def connect(self, debate_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[debate_id].add(websocket)

    def disconnect(self, debate_id: str, websocket: WebSocket) -> None:
        self._connections[debate_id].discard(websocket)
        if not self._connections[debate_id]:
            self._connections.pop(debate_id, None)

    async def broadcast(self, debate_id: str, message: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self._connections.get(debate_id, set())):
            try:
                await websocket.send_json(message)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(debate_id, websocket)

    async def send_snapshot(self, debate_id: str, websocket: WebSocket) -> None:
        if self.snapshot_provider is None:
            return
        try:
            snapshot = self.snapshot_provider(debate_id)
        except FileNotFoundError:
            return
        if snapshot is not None:
            await websocket.send_json({"type": "state_snapshot", "state": snapshot})


manager = WebSocketManager()


@router.websocket("/ws/debates/{debate_id}")
async def debate_websocket(websocket: WebSocket, debate_id: str) -> None:
    await manager.connect(debate_id, websocket)
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "subscribe":
                await websocket.send_json({"type": "subscribed", "debate_id": debate_id})
                await manager.send_snapshot(debate_id, websocket)
    except WebSocketDisconnect:
        manager.disconnect(debate_id, websocket)
