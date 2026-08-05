"""Cooldown stores for intraday alerting (plan §14, M7).

At nightly cadence the database dedup in ``app.alerts.rules`` is enough;
intraday alerts need sub-day cooldowns that survive across pollers, which
is what Redis SETNX + TTL provides. Without Redis the in-memory store
keeps a single-process collector correct — an honest fallback, clearly
weaker across restarts.
"""

from __future__ import annotations

import time
from typing import Any, Protocol


class CooldownStore(Protocol):
    def acquire(self, key: str, ttl_seconds: int) -> bool:
        """True if the caller won the key (alert may fire); False = cooling."""
        ...


class InMemoryCooldownStore:
    """Single-process cooldowns; the clock is injectable for tests."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._expiry: dict[str, float] = {}

    def acquire(self, key: str, ttl_seconds: int) -> bool:
        now = self._clock()
        expiry = self._expiry.get(key)
        if expiry is not None and expiry > now:
            return False
        self._expiry[key] = now + ttl_seconds
        return True


class RedisCooldownStore:
    """SETNX + TTL on any redis-py-compatible client."""

    def __init__(self, client: Any, *, prefix: str = "darkpool:cooldown:") -> None:
        self._client = client
        self._prefix = prefix

    def acquire(self, key: str, ttl_seconds: int) -> bool:
        return bool(self._client.set(self._prefix + key, "1", nx=True, ex=ttl_seconds))


def make_cooldown_store(redis_url: str | None) -> CooldownStore:
    """Redis when reachable, in-memory otherwise. Never crashes the caller."""
    if redis_url:
        try:
            import redis

            client = redis.Redis.from_url(redis_url)
            client.ping()
            return RedisCooldownStore(client)
        except Exception:  # noqa: BLE001 — any failure means: fall back
            pass
    return InMemoryCooldownStore()
