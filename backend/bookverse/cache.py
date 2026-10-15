import hashlib
import json
import logging
from typing import Protocol

from redis.asyncio import Redis

from .schemas import SearchResponse

logger = logging.getLogger(__name__)


class SearchCache(Protocol):
    async def get(self, key: str) -> SearchResponse | None: ...
    async def set(self, key: str, value: SearchResponse, ttl: int) -> None: ...
    async def ping(self) -> bool: ...


def make_search_cache_key(
    query: str,
    language: str | None,
    page: int,
    limit: int,
    providers: list[str],
    access_type: str | None = None,
) -> str:
    raw = json.dumps(
        {
            "q": query.casefold().strip(),
            "language": language,
            "page": page,
            "limit": limit,
            "providers": sorted(providers),
            "access_type": access_type,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "bookverse:search:" + hashlib.sha256(raw.encode()).hexdigest()


class RedisSearchCache:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> SearchResponse | None:
        try:
            value = await self.redis.get(key)
            return SearchResponse.model_validate_json(value) if value else None
        except Exception as exc:
            logger.info("Search cache read unavailable (%s)", type(exc).__name__)
            return None

    async def set(self, key: str, value: SearchResponse, ttl: int) -> None:
        try:
            await self.redis.set(key, value.model_dump_json(), ex=ttl)
        except Exception as exc:
            logger.info("Search cache write unavailable (%s)", type(exc).__name__)

    async def ping(self) -> bool:
        try:
            return bool(await self.redis.ping())
        except Exception:
            return False
