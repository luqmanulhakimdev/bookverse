import os

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bookverse.models import Base, Book, BookSource
from bookverse.repositories.books import persist_book
from bookverse.schemas import Book as BookSchema

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not configured")


@pytest.mark.asyncio
async def test_postgres_catalog_source_uniqueness_and_persistence():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            item = BookSchema(
                id="/works/pg-test",
                title="Postgres Test",
                authors=["Test Writer"],
                source="open_library",
            )
            stored = await persist_book(session, item)
            await session.commit()
            source = await session.scalar(
                select(BookSource).where(
                    BookSource.provider == "open_library",
                    BookSource.external_id == "/works/pg-test",
                )
            )
            assert source is not None
            assert await session.get(Book, stored.id) is not None
            assert stored.id is not None
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
