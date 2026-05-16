from __future__ import annotations

import json
import time
from typing import Any, Optional

import redis


class Cache:
    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 60 * 60 * 24):
        self.ttl_seconds = ttl_seconds
        self._memory: dict[str, tuple[float, Any]] = {}
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True) if redis_url else None

    def get(self, key: str) -> Optional[Any]:
        if self._redis:
            value = self._redis.get(key)
            return json.loads(value) if value else None

        item = self._memory.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._memory.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self._redis:
            self._redis.setex(key, self.ttl_seconds, json.dumps(value, ensure_ascii=False))
            return
        self._memory[key] = (time.time() + self.ttl_seconds, value)
