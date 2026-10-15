import asyncio
from typing import Protocol

import httpx

from ..schemas import Book


class BookProvider(Protocol):
    name: str

    async def search(self, query: str, page: int, limit: int) -> list[Book]: ...


class HttpProvider:
    name = "provider"

    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def get_json(self, url: str, params: dict) -> dict:
        response = None
        for attempt in range(2):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 and exc.response.status_code < 500:
                    raise
                if attempt == 1:
                    raise
            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
                httpx.RemoteProtocolError,
            ):
                if attempt == 1:
                    raise
            await asyncio.sleep(0.15 * (2**attempt))
        if response is None:
            raise httpx.RequestError("No provider response")
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Provider returned an invalid response")
        return payload
