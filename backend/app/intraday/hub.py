"""In-process pub/sub for the live dashboard feed.

The collector publishes; each connected websocket holds its own bounded
queue. A slow consumer drops its own oldest messages — it never blocks the
collector or other clients.
"""

from __future__ import annotations

import asyncio
from typing import Any


class LiveHub:
    def __init__(self, *, queue_size: int = 500) -> None:
        self._queue_size = queue_size
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def publish(self, message: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                try:  # drop that subscriber's oldest message, keep the newest
                    queue.get_nowait()
                    queue.put_nowait(message)
                except asyncio.QueueEmpty:  # pragma: no cover — racy edge
                    pass


#: The process-wide hub the API's websocket endpoint serves from.
live_hub = LiveHub()
