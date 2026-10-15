from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    open_library_base_url: str = "https://openlibrary.org"
    google_books_base_url: str = "https://www.googleapis.com/books/v1"
    provider_timeout_seconds: float = 5
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://bookverse:bookverse@localhost:5432/bookverse"


settings = Settings()
