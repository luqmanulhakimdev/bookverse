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
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Provider returned an invalid response")
        return payload
