from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bookverse.models import Author, Base, BookSource, Genre
from bookverse.repositories.books import get_book, persist_book, serialize_book
from bookverse.schemas import Book


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
            access_type="metadata",
        )
        first = await persist_book(session, item)
        await session.commit()
        second = await persist_book(session, item)
        await session.commit()
        assert first.id == second.id
        assert await session.scalar(select(func.count()).select_from(BookSource)) == 1
        assert await session.scalar(select(func.count()).select_from(Author)) == 1
        assert await session.scalar(select(func.count()).select_from(Genre)) == 1
        loaded = await get_book(session, first.id)
        payload = await serialize_book(loaded)
        assert payload["authors"] == ["A. Writer"]
        assert payload["genres"] == ["Fantasy"]
        assert payload["sources"][0]["external_id"] == "/works/test"
    await engine.dispose()
