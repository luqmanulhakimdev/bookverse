from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bookverse.models import Author, Base, BookSource, Genre
from bookverse.repositories.books import attach_source, get_book, persist_book, serialize_book
from bookverse.schemas import Book, BookSourceInfo


async def test_persist_book_is_idempotent_and_preserves_source_identity():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        item = Book(
            id="/works/test",
            title="Test Book",
            authors=["A. Writer"],
            genres=["Fantasy"],
            source="open_library",
            source_url="https://openlibrary.org/works/test",
            access_type="metadata",
        )
        first = await persist_book(session, item)
        await session.commit()
        second = await persist_book(session, item)
        assert await session.scalar(select(func.count()).select_from(BookSource)) == 1
        await attach_source(
            session,
            second.id,
            BookSourceInfo(
                provider="google_books",
                external_id="google-id",
                source_url="https://books.google.com/books?id=google-id",
                access_type="preview",
                access_url="https://books.google.com/preview/google-id",
            ),
        )
        await session.commit()
        assert first.id == second.id
        assert await session.scalar(select(func.count()).select_from(BookSource)) == 2
        assert await session.scalar(select(func.count()).select_from(Author)) == 1
        assert await session.scalar(select(func.count()).select_from(Genre)) == 1
        loaded = await get_book(session, first.id)
        payload = await serialize_book(loaded)
        assert payload["authors"] == ["A. Writer"]
        assert payload["genres"] == ["Fantasy"]
        assert payload["sources"][0]["external_id"] == "/works/test"
        assert payload["sources"][0]["source_url"] == "https://openlibrary.org/works/test"
        assert {source["provider"] for source in payload["sources"]} == {
            "open_library",
            "google_books",
        }
    await engine.dispose()
