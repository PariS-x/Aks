"""Session storage.

In-memory with expiry, behind a tiny interface so it can be swapped for Redis
or a database without touching the engine (needed for multiplayer rooms).
"""

from __future__ import annotations

import asyncio
import time
from typing import Generic, Optional, Protocol, TypeVar

T = TypeVar("T")


class SessionStore(Protocol[T]):
    async def get(self, key: str) -> Optional[T]: ...
    async def put(self, key: str, value: T) -> None: ...


class MemoryStore(Generic[T]):
    def __init__(self, ttl_s: int = 60 * 60 * 6, max_items: int = 5000):
        self.ttl, self.max = ttl_s, max_items
        self._d: dict[str, tuple[float, T]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def lock(self, key: str) -> asyncio.Lock:
        """Per-session lock so two requests cannot advance the same game at once."""
        return self._locks.setdefault(key, asyncio.Lock())

    async def get(self, key: str) -> Optional[T]:
        item = self._d.get(key)
        if not item:
            return None
        ts, val = item
        if time.time() - ts > self.ttl:
            self._d.pop(key, None)
            return None
        return val

    async def put(self, key: str, value: T) -> None:
        if len(self._d) >= self.max:
            oldest = min(self._d, key=lambda k: self._d[k][0])
            self._d.pop(oldest, None)
            self._locks.pop(oldest, None)
        self._d[key] = (time.time(), value)
