"""Broadcast JSON events to connected WebSocket clients."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiohttp import web


class WebSocketHub:
    def __init__(self) -> None:
        self._clients: set[web.WebSocketResponse] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def add(self, ws: web.WebSocketResponse) -> None:
        self._clients.add(ws)

    def remove(self, ws: web.WebSocketResponse) -> None:
        self._clients.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def broadcast(self, data: str) -> None:
        dead: list[web.WebSocketResponse] = []
        for ws in list(self._clients):
            try:
                await ws.send_str(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    def broadcast_json(self, payload: dict[str, Any]) -> None:
        if self._loop is None or not self._clients:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(json.dumps(payload)), self._loop)