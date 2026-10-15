import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .providers import GoogleBooksProvider, OpenLibraryProvider
from .search import AllProvidersFailed, search_books


@asynccontextmanager
async def lifespan(app: FastAPI):
    request_timeout = float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "5"))
    timeout = httpx.Timeout(request_timeout, connect=min(request_timeout, 2.0))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        app.state.providers = [
            OpenLibraryProvider(
                client, os.getenv("OPEN_LIBRARY_BASE_URL", "https://openlibrary.org")
            ),
            GoogleBooksProvider(
                client, os.getenv("GOOGLE_BOOKS_BASE_URL", "https://www.googleapis.com/books/v1")
            ),
        ]
        yield


app = FastAPI(title="BookVerse API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


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
):
    providers = app.state.providers
    if provider:
        providers = [p for p in providers if p.name == provider]
        if not providers:
            raise HTTPException(
                status_code=422, detail={"code": "invalid_provider", "message": "Unknown provider"}
            )
    try:
        return await search_books(" ".join(q.split()), page, limit, providers)
    except AllProvidersFailed:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "upstream_unavailable",
                "message": "All book catalogs are temporarily unavailable",
            },
        ) from None
