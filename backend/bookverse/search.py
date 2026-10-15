import asyncio
import logging

from .providers.base import BookProvider
from .schemas import ProviderStatus, SearchResponse

logger = logging.getLogger(__name__)


class AllProvidersFailed(Exception):
    pass


async def search_books(
    query: str, page: int, limit: int, providers: list[BookProvider], timeout: float = 5
) -> SearchResponse:
    async def call(provider: BookProvider):
        try:
            result = await asyncio.wait_for(provider.search(query, page, limit), timeout=timeout)
            return provider, result, None
        except Exception as exc:
            logger.warning("Book provider %s failed (%s)", provider.name, type(exc).__name__)
            return provider, [], type(exc).__name__

    results = await asyncio.gather(*(call(p) for p in providers))
    if not results or all(error for _, _, error in results):
        raise AllProvidersFailed
    books, statuses, seen = [], [], set()
    for provider, found, error in results:
        statuses.append(
            ProviderStatus(
                provider=provider.name,
                status="error" if error else "ok",
                result_count=len(found),
                message="Provider temporarily unavailable" if error else None,
            )
        )
        for book in found:
            identity = (
                book.title.casefold().strip(),
                tuple(a.casefold().strip() for a in book.authors),
            )
            if identity in seen:
                continue
            seen.add(identity)
            books.append(book)
    books.sort(key=lambda b: (b.title.casefold(), b.source))
    return SearchResponse(
        items=books[:limit],
        page=page,
        limit=limit,
        fetched_count=len(books),
        total=None,
        total_kind="fetched_results",
        providers=statuses,
    )
