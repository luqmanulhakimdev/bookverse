import httpx
import pytest

from bookverse.cache import RedisSearchCache, make_search_cache_key
from bookverse.rate_limit import SlidingWindowLimiter
from bookverse.schemas import SearchResponse


class MemoryRedis:
    def __init__(self, broken=False):
        self.data = {}
        self.broken = broken

    async def get(self, key):
        if self.broken:
            raise ConnectionError("redis host details")
        return self.data.get(key)

    async def set(self, key, value, ex):
        if self.broken:
            raise ConnectionError("redis host details")
        self.data[key] = value

    async def ping(self):
        if self.broken:
            raise ConnectionError
        return True


@pytest.mark.asyncio
async def test_search_cache_round_trip_and_key_separates_filters():
    cache = RedisSearchCache(MemoryRedis())
    key = make_search_cache_key("Book", None, 1, 20, ["google", "open"])
    result = SearchResponse(items=[], page=1, limit=20, fetched_count=0, providers=[])
    await cache.set(key, result, 60)
    assert await cache.get(key) == result
    assert key != make_search_cache_key("Book", "en", 1, 20, ["google", "open"])
    assert key != make_search_cache_key("Book", None, 1, 20, ["open"])


@pytest.mark.asyncio
async def test_redis_failure_degrades_to_cache_miss():
    cache = RedisSearchCache(MemoryRedis(broken=True))
    assert await cache.get("search") is None
    await cache.set(
        "search", SearchResponse(items=[], page=1, limit=20, fetched_count=0, providers=[]), 60
    )
    assert await cache.ping() is False


def test_rate_limiter_uses_sliding_window_and_expires_old_events():
    limiter = SlidingWindowLimiter(10)
    assert limiter.allow("ip", "auth", 2, now=0)
    assert limiter.allow("ip", "auth", 2, now=1)
    assert not limiter.allow("ip", "auth", 2, now=2)
    assert limiter.allow("ip", "auth", 2, now=10)


@pytest.mark.asyncio
async def test_provider_retries_transient_upstream_status():
    class RetryingClient:
        def __init__(self):
            self.calls = 0

        async def get(self, url, params):
            self.calls += 1
            request = httpx.Request("GET", url)
            if self.calls == 1:
                return httpx.Response(503, request=request)
            return httpx.Response(200, json={"ok": True}, request=request)

    from bookverse.providers.base import HttpProvider

    client = RetryingClient()
    provider = HttpProvider(client, "https://example.test")
    assert await provider.get_json("https://example.test", {}) == {"ok": True}
    assert client.calls == 2
