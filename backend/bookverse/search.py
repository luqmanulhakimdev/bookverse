import asyncio
import logging

from .providers.base import BookProvider
from .schemas import BookSourceInfo, ProviderStatus, SearchResponse

logger = logging.getLogger(__name__)


class AllProvidersFailed(Exception):
    pass


async def search_books(
    query: str,
    page: int,
    limit: int,
    providers: list[BookProvider],
    timeout: float = 5,
    max_concurrency: int = 3,
    language: str | None = None,
    access_type: str | None = None,
) -> SearchResponse:
    semaphore = asyncio.Semaphore(max_concurrency)

    async def call(provider: BookProvider):
        try:
            async with semaphore:
                result = await asyncio.wait_for(
                    provider.search(query, page, limit), timeout=timeout
                )
            return provider, result, None
        except Exception as exc:
            logger.warning("Book provider %s failed (%s)", provider.name, type(exc).__name__)
            return provider, [], type(exc).__name__

    results = await asyncio.gather(*(call(p) for p in providers))
    if not results or all(error for _, _, error in results):
        raise AllProvidersFailed
    books, statuses, seen = [], [], {}
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
            source_info = BookSourceInfo(
                provider=book.source,
                external_id=book.external_id or book.id,
                source_url=book.source_url,
                access_type=book.access_type,
                access_url=book.access_url,
                license_or_rights=book.license_or_rights,
            )
            if identity in seen:
                matched = seen[identity]
                if not any(
                    existing.provider == source_info.provider
                    and existing.external_id == source_info.external_id
                    for existing in matched.sources
                ):
                    matched.sources.append(source_info)
                matched.genres = sorted(set(matched.genres + book.genres))
                matched.description = matched.description or book.description
                matched.cover_url = matched.cover_url or book.cover_url
                matched.language = matched.language or book.language
                matched.published_year = matched.published_year or book.published_year
                continue
            seen[identity] = book
            book.sources = [source_info]
            books.append(book)
    books.sort(key=lambda b: (b.title.casefold(), b.source))
    if language:
        books = [book for book in books if (book.language or "").casefold() == language.casefold()]
    if access_type:
        books = [book for book in books if book.access_type == access_type]
    return SearchResponse(
        items=books[:limit],
        page=page,
        limit=limit,
        fetched_count=len(books),
        total=None,
        total_kind="fetched_results",
        providers=statuses,
    )
