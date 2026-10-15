import httpx
import pytest

from bookverse.providers.google_books import GoogleBooksProvider
from bookverse.providers.open_library import OpenLibraryProvider


class MockClient:
    def __init__(self, payload):
        self.payload = payload

    async def get(self, url, params):
        request = httpx.Request("GET", url)
        return httpx.Response(200, json=self.payload, request=request)


@pytest.mark.asyncio
async def test_open_library_skips_malformed_entries():
    provider = OpenLibraryProvider(
        MockClient({"docs": [None, {}, {"key": "/works/a", "title": "A"}]}),
        "https://openlibrary.org",
    )
    books = await provider.search("a", 1, 10)
    assert len(books) == 1
    assert books[0].authors == []
    assert books[0].access_type == "metadata"


@pytest.mark.asyncio
async def test_google_books_handles_missing_metadata():
    provider = GoogleBooksProvider(
        MockClient({"items": [{"id": "x", "volumeInfo": {"title": "Book"}}]}),
        "https://www.googleapis.com/books/v1",
    )
    books = await provider.search("book", 1, 10)
    assert books[0].title == "Book"
    assert books[0].published_year is None
