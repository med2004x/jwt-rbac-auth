import json
from collections.abc import Sequence
from typing import Protocol

from redis.asyncio import Redis


class TokenStore(Protocol):
    async def store_refresh_token(self, token_identifier: str, user_id: int, ttl_seconds: int) -> None: ...
    async def is_refresh_token_active(self, token_identifier: str) -> bool: ...
    async def revoke_refresh_token(self, token_identifier: str, ttl_seconds: int) -> None: ...
    async def publish_audit_event(self, event_name: str, event_payload: dict[str, str]) -> None: ...
    async def read_audit_events(self) -> Sequence[dict[str, str]]: ...


class RedisTokenStore:
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def store_refresh_token(self, token_identifier: str, user_id: int, ttl_seconds: int) -> None:
        await self._redis.set(f"refresh:{token_identifier}", user_id, ex=ttl_seconds)

    async def is_refresh_token_active(self, token_identifier: str) -> bool:
        return bool(await self._redis.exists(f"refresh:{token_identifier}"))

    async def revoke_refresh_token(self, token_identifier: str, ttl_seconds: int) -> None:
        pipeline = self._redis.pipeline()
        pipeline.delete(f"refresh:{token_identifier}")
        pipeline.set(f"revoked:{token_identifier}", "1", ex=ttl_seconds)
        await pipeline.execute()

    async def publish_audit_event(self, event_name: str, event_payload: dict[str, str]) -> None:
        serialized_event = json.dumps({"event_name": event_name, **event_payload})
        await self._redis.lpush("audit-events", serialized_event)

    async def read_audit_events(self) -> Sequence[dict[str, str]]:
        audit_messages = await self._redis.lrange("audit-events", 0, -1)
        return [json.loads(message) for message in audit_messages]

