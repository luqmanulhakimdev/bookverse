from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_session
from ..models import Book, BookAuthor, BookGenre, User, UserBook
from ..recommendations import recommend_books
from ..repositories.books import get_book, serialize_book
from .dependencies import current_user

router = APIRouter(tags=["recommendations"])
BOOK_FEATURES = (
    selectinload(Book.sources),
    selectinload(Book.authors).selectinload(BookAuthor.author),
    selectinload(Book.genres).selectinload(BookGenre.genre),
)


async def similar_response(session: AsyncSession, book_id: UUID, limit: int):
    target = await get_book(session, book_id)
    if target is None:
        raise HTTPException(
            status_code=404, detail={"code": "book_not_found", "message": "Book not found"}
        )
    candidates = list(await session.scalars(select(Book).options(*BOOK_FEATURES).limit(1000)))
    ranked = recommend_books(candidates, [target], {str(book_id)}, limit)
    return {
        "items": [
            {**await serialize_book(row["book"]), "score": row["score"], "reasons": row["reasons"]}
            for row in ranked
        ],
        "count": len(ranked),
    }


@router.get("/api/v1/books/{book_id}/similar")
@router.get("/api/v1/recommendations/{book_id}/similar", include_in_schema=False)
async def similar_books(
    book_id: UUID,
    limit: int = Query(12, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
):
    return await similar_response(session, book_id, limit)


@router.get("/api/v1/recommendations")
async def personalized_recommendations(
    limit: int = Query(20, ge=1, le=40),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    library = list(
        await session.scalars(
            select(UserBook)
            .where(UserBook.user_id == user.id)
            .options(
                selectinload(UserBook.book).selectinload(Book.sources),
                selectinload(UserBook.book)
                .selectinload(Book.authors)
                .selectinload(BookAuthor.author),
                selectinload(UserBook.book).selectinload(Book.genres).selectinload(BookGenre.genre),
            )
        )
    )
    seed_entries = [
        entry
        for entry in library
        if entry.status in {"reading", "finished"} or entry.rating is not None
    ]
    if not seed_entries:
        return {
            "items": [],
            "count": 0,
            "message": "Add a rating or mark a book as reading or finished to get recommendations.",
        }
    candidates = list(await session.scalars(select(Book).options(*BOOK_FEATURES).limit(1000)))
    excluded = {str(entry.book_id) for entry in library}
    ranked = recommend_books(candidates, seed_entries, excluded, limit)
    return {
        "items": [
            {**await serialize_book(row["book"]), "score": row["score"], "reasons": row["reasons"]}
            for row in ranked
        ],
        "count": len(ranked),
    }
