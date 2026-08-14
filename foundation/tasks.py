from __future__ import annotations

import asyncio
import time
import uuid
import json
from typing import Any, Awaitable, Callable


class TaskStore:
    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 86400):
        self.items: dict[str, dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.redis = None
        if redis_url:
            from redis.asyncio import Redis
            self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def _save(self, item: dict[str, Any]) -> None:
        self.items[item["task_id"]] = item
        if self.redis:
            payload = {**item}
            result = payload.get("result")
            if hasattr(result, "model_dump"):
                payload["result"] = result.model_dump()
            await self.redis.setex(f"foundation:task:{item['task_id']}", self.ttl_seconds,
                                   json.dumps(payload, ensure_ascii=False))

    async def create(self, app_id: str, runner: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
        task_id = f"task_{uuid.uuid4().hex}"
        item = {"task_id": task_id, "app_id": app_id, "status": "queued", "result": None,
                "error": None, "created_at": time.time(), "updated_at": time.time()}
        await self._save(item)
        asyncio.create_task(self._run(item, runner))
        return item

    async def _run(self, item: dict[str, Any], runner: Callable[[], Awaitable[Any]]) -> None:
        item.update(status="processing", updated_at=time.time())
        await self._save(item)
        try:
            item.update(status="completed", result=await runner(), updated_at=time.time())
        except asyncio.CancelledError:
            item.update(status="cancelled", updated_at=time.time())
        except Exception as exc:
            item.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)},
                        updated_at=time.time())
        await self._save(item)

    async def get(self, task_id: str, app_id: str) -> dict[str, Any] | None:
        item = self.items.get(task_id)
        if not item and self.redis:
            raw = await self.redis.get(f"foundation:task:{task_id}")
            item = json.loads(raw) if raw else None
        return item if item and item["app_id"] == app_id else None
