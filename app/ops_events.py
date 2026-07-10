"""Fire-and-forget tool invocation events for mission-control SSE."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import UTC, datetime
from typing import Any

_recent: deque[dict[str, Any]] = deque(maxlen=500)
_subscribers: list[asyncio.Queue[dict[str, Any]]] = []


def emit_tool_event(tool: str, agent_id: str, meta: dict[str, Any]) -> None:
    """Record a tool call; never raise — dashboard must not break MCP tools."""
    try:
        event = {
            "ts": datetime.now(UTC).isoformat(),
            "tool": tool,
            "agent_id": agent_id,
            "meta": meta,
        }
        _recent.append(event)
        for queue in list(_subscribers):
            try:
                queue.put_nowait(event)
            except Exception:
                pass
    except Exception:
        pass


def recent_events(limit: int = 200) -> list[dict[str, Any]]:
    items = list(_recent)
    return items[-limit:]


async def event_stream():
    """Async generator for SSE subscribers with 15s heartbeat."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _subscribers.append(queue)
    try:
        for item in list(_recent)[-50:]:
            yield item
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield event
            except asyncio.TimeoutError:
                yield {"type": "heartbeat", "ts": datetime.now(UTC).isoformat()}
    finally:
        if queue in _subscribers:
            _subscribers.remove(queue)


def format_sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"