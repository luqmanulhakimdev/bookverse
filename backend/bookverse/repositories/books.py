from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Author, Book, BookAuthor, BookSource
from ..schemas import Book as BookSchema


async def persist_book(session: AsyncSession, item: BookSchema) -> Book:
    source_id = item.external_id or item.id
    source = await session.scalar(
        select(BookSource)
        .where(BookSource.provider == item.source, BookSource.external_id == source_id)
        .options(
            selectinload(BookSource.book).selectinload(Book.authors).selectinload(BookAuthor.author)
        )
    )
    if source:
        book = source.book
        source.access_type = item.access_type
        source.access_url = str(item.access_url) if item.access_url else None
        source.last_synced_at = func.now()
    else:
        book = Book(
            title=item.title,
            description=item.description,
            language=item.language,
            published_year=item.published_year,
            cover_url=str(item.cover_url) if item.cover_url else None,
        )
        book.authors = []
        session.add(book)
        await session.flush()
        session.add(
            BookSource(
                book_id=book.id,
                provider=item.source,
                external_id=source_id,
                access_type=item.access_type,
                access_url=str(item.access_url) if item.access_url else None,
            )
        )
    book.title = item.title
    book.description = item.description or book.description
    book.language = item.language or book.language
    book.published_year = item.published_year or book.published_year
    book.cover_url = str(item.cover_url) if item.cover_url else book.cover_url
    existing = {link.author.name.casefold() for link in book.authors}
    for position, name in enumerate(item.authors):
        if name.casefold() in existing:
            continue
        author = await session.scalar(select(Author).where(Author.name == name))
        if author is None:
            author = Author(name=name)
            session.add(author)
            await session.flush()
        book.authors.append(BookAuthor(author=author, position=position))
        existing.add(name.casefold())
    await session.flush()
    return book


async def get_book(session: AsyncSession, book_id: UUID) -> Book | None:
    return await session.scalar(
        select(Book)
        .where(Book.id == book_id)
        .options(
            selectinload(Book.sources), selectinload(Book.authors).selectinload(BookAuthor.author)
        )
    )


async def serialize_book(book: Book) -> dict:
    authors = sorted(book.authors, key=lambda a: a.position)
    source = book.sources[0] if book.sources else None
    return {
        "id": str(book.id),
        "title": book.title,
        "authors": [a.author.name for a in authors],
        "description": book.description,
        "language": book.language,
        "published_year": book.published_year,
        "cover_url": book.cover_url,
        "sources": [
            {
                "provider": s.provider,
                "external_id": s.external_id,
                "access_type": s.access_type,
                "access_url": s.access_url,
            }
            for s in book.sources
        ],
        "source": source.provider if source else "bookverse",
        "source_url": source.access_url if source else None,
        "access_type": source.access_type if source else "unknown",
        "access_url": source.access_url if source else None,
    }
