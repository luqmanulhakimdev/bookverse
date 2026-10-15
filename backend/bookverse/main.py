from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .api.auth import router as auth_router
from .api.library import router as library_router
from .api.users import router as users_router
from .config import settings
from .database import get_session
from .providers import GoogleBooksProvider, OpenLibraryProvider
from .repositories.books import get_book, persist_book, serialize_book
from .search import AllProvidersFailed, search_books


@asynccontextmanager
async def lifespan(app: FastAPI):
    request_timeout = settings.provider_timeout_seconds
    timeout = httpx.Timeout(request_timeout, connect=min(request_timeout, 2.0))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        app.state.providers = [
            OpenLibraryProvider(client, settings.open_library_base_url),
            GoogleBooksProvider(client, settings.google_books_base_url),
        ]
        yield


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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/api/v1/books")
async def get_books(
    q: str = Query(min_length=2, max_length=120),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=40),
    provider: str | None = None,
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
        result = await search_books(" ".join(q.split()), page, limit, providers)
        for item in result.items:
            external_id = item.external_id or item.id
            stored = await persist_book(session, item)
            item.external_id = external_id
            item.id = str(stored.id)
        await session.commit()
        return result
    except AllProvidersFailed:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "upstream_unavailable",
                "message": "All book catalogs are temporarily unavailable",
            },
        ) from None


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
                "rights": s.license_or_rights,
            }
            for s in book.sources
        ],
    }
