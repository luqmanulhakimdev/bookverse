from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class Book(BaseModel):
    id: str
    external_id: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    description: str | None = None
    language: str | None = None
    published_year: int | None = None
    cover_url: HttpUrl | None = None
    source: str
    source_url: HttpUrl | None = None
    access_type: Literal["metadata", "preview", "read", "borrow", "download", "unknown"] = "unknown"
    access_url: HttpUrl | None = None
    license_or_rights: str | None = None


class ProviderStatus(BaseModel):
    provider: str
    status: Literal["ok", "error"]
    result_count: int
    message: str | None = None


class SearchResponse(BaseModel):
    items: list[Book]
    page: int
    limit: int
    fetched_count: int
    total: int | None = None
    total_kind: Literal["provider_estimate", "fetched_results"] = "fetched_results"
    providers: list[ProviderStatus]
