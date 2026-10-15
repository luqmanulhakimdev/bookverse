from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    open_library_base_url: str = "https://openlibrary.org"
    google_books_base_url: str = "https://www.googleapis.com/books/v1"
    gutenberg_api_url: str = "https://gutendex.com/books/"
    provider_timeout_seconds: float = Field(default=5, gt=0, le=60)
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://bookverse:bookverse@localhost:5432/bookverse"
    jwt_secret: str = Field(
        default="change-this-development-secret-before-deployment", min_length=32
    )
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    refresh_cookie_secure: bool = False
    redis_url: str = "redis://localhost:6379/0"
    search_cache_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    max_provider_concurrency: int = Field(default=3, ge=1, le=20)
    global_rate_limit_per_minute: int = Field(default=300, ge=1)
    auth_rate_limit_per_minute: int = Field(default=30, ge=1)


settings = Settings()
