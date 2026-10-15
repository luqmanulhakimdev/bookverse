from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .api.auth import router as auth_router
from .api.library import router as library_router
from .api.recommendations import router as recommendations_router
from .api.users import router as users_router
from .cache import RedisSearchCache, make_search_cache_key
from .config import settings
from .database import get_session
from .providers import GoogleBooksProvider, GutenbergProvider, OpenLibraryProvider
from .rate_limit import SlidingWindowLimiter
from .repositories.books import attach_source, get_book, persist_book, serialize_book
from .schemas import ProviderStatus, SearchResponse
from .search import AllProvidersFailed, search_books


@asynccontextmanager
async def lifespan(app: FastAPI):
    request_timeout = settings.provider_timeout_seconds
    timeout = httpx.Timeout(request_timeout, connect=min(request_timeout, 2.0))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        app.state.redis = redis_client
        app.state.cache = RedisSearchCache(redis_client)
        app.state.providers = [
            OpenLibraryProvider(client, settings.open_library_base_url),
            GoogleBooksProvider(client, settings.google_books_base_url),
            GutenbergProvider(client, settings.gutenberg_api_url),
        ]
        try:
            yield
        finally:
            await redis_client.aclose()


app = FastAPI(title="BookVerse API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(library_router)
app.include_router(recommendations_router)
rate_limiter = SlidingWindowLimiter()


@app.middleware("http")
async def apply_rate_limits(request, call_next):
    if request.url.path.startswith("/api/v1/"):
        client_ip = request.client.host if request.client else "unknown"
        auth_path = request.url.path.startswith("/api/v1/auth/")
        limit = (
            settings.auth_rate_limit_per_minute
            if auth_path
            else settings.global_rate_limit_per_minute
        )
        bucket = "auth" if auth_path else "api"
        if not rate_limiter.allow(client_ip, bucket, limit):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "rate_limited",
                        "message": "Too many requests. Try again shortly.",
                    }
                },
                headers={"Retry-After": "60"},
            )
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={"code": "database_unavailable", "message": "Database is not ready"},
        ) from None
    redis_ready = await app.state.cache.ping()
    return {
        "status": "ready",
        "dependencies": {"database": "ok", "redis": "ok" if redis_ready else "degraded"},
    }


@app.get("/api/v1/books")
async def get_books(
    q: str = Query(min_length=2, max_length=120),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=40),
    provider: str | None = None,
    language: str | None = Query(default=None, min_length=2, max_length=12),
    access_type: str | None = Query(
        default=None, pattern="^(metadata|preview|read|borrow|download|unknown)$"
    ),
    session: AsyncSession = Depends(get_session),
):
    providers = app.state.providers
    if provider:
        providers = [p for p in providers if p.name == provider]
        if not providers:
            raise HTTPException(
                status_code=422, detail={"code": "invalid_provider", "message": "Unknown provider"}
            )
    try:
        normalized_query = " ".join(q.split())
        cache_key = make_search_cache_key(
            normalized_query, language, page, limit, [p.name for p in providers], access_type
        )
        cached = await app.state.cache.get(cache_key)
        if cached is not None:
            return cached
        result = await search_books(
            normalized_query,
            page,
            limit,
            providers,
            timeout=settings.provider_timeout_seconds,
            max_concurrency=settings.max_provider_concurrency,
            language=language,
            access_type=access_type,
        )
        for item in result.items:
            external_id = item.external_id or item.id
            source_records = item.sources
            stored = await persist_book(session, item)
            for source_record in source_records:
                if (
                    source_record.provider == item.source
                    and source_record.external_id == external_id
                ):
                    continue
                await attach_source(session, stored.id, source_record)
            item.external_id = external_id
            item.id = str(stored.id)
        await session.commit()
        await app.state.cache.set(cache_key, result, settings.search_cache_ttl_seconds)
        return result
    except AllProvidersFailed:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "upstream_unavailable",
                "message": "All book catalogs are temporarily unavailable",
            },
        ) from None


@app.get("/api/v1/gutenberg/popular", response_model=SearchResponse)
async def get_popular_gutenberg_books(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
):
    """Return Project Gutenberg's most-downloaded titles for discovery."""
    provider = next((p for p in app.state.providers if p.name == "gutenberg"), None)
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "provider_unavailable", "message": "Project Gutenberg is unavailable"},
        )
    try:
        books = await provider.popular(page, limit)
        for item in books:
            external_id = item.external_id or item.id
            stored = await persist_book(session, item)
            item.external_id = external_id
            item.id = str(stored.id)
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_unavailable", "message": "Project Gutenberg is temporarily unavailable"},
        ) from None
    return SearchResponse(
        items=books,
        page=page,
        limit=limit,
        fetched_count=len(books),
        total=None,
        total_kind="fetched_results",
        providers=[ProviderStatus(provider="gutenberg", status="ok", result_count=len(books))],
    )


@app.get("/api/v1/books/{book_id}")
async def get_book_details(book_id: str, session: AsyncSession = Depends(get_session)):
    from uuid import UUID

    try:
        parsed_id = UUID(book_id)
    except ValueError:
        raise HTTPException(
            status_code=422, detail={"code": "invalid_book_id", "message": "Book id must be a UUID"}
        ) from None
    book = await get_book(session, parsed_id)
    if not book:
        raise HTTPException(
            status_code=404, detail={"code": "book_not_found", "message": "Book not found"}
        )
    return await serialize_book(book)


@app.get("/api/v1/books/{book_id}/availability")
async def get_book_availability(book_id: str, session: AsyncSession = Depends(get_session)):
    from uuid import UUID

    try:
        parsed_id = UUID(book_id)
    except ValueError:
        raise HTTPException(
            status_code=422, detail={"code": "invalid_book_id", "message": "Book id must be a UUID"}
        ) from None
    book = await get_book(session, parsed_id)
    if not book:
        raise HTTPException(
            status_code=404, detail={"code": "book_not_found", "message": "Book not found"}
        )
    return {
        "book_id": book_id,
        "sources": [
            {
                "provider": s.provider,
                "access_type": s.access_type,
                "access_url": s.access_url,
                "source_url": s.source_url,
                "rights": s.license_or_rights,
            }
            for s in book.sources
        ],
    }
