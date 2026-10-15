from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_session
from ..models import Book, BookAuthor, BookGenre, ReadingEvent, User, UserBook
from ..repositories.books import serialize_book
from ..schemas_auth import LibraryItemInput
from .dependencies import current_user

router = APIRouter(prefix="/api/v1/library", tags=["personal library"])


@router.get("")
async def list_library(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    entries = await session.scalars(
        select(UserBook)
        .where(UserBook.user_id == user.id)
        .options(
            selectinload(UserBook.book).selectinload(Book.sources),
            selectinload(UserBook.book).selectinload(Book.authors).selectinload(BookAuthor.author),
            selectinload(UserBook.book).selectinload(Book.genres).selectinload(BookGenre.genre),
        )
        .order_by(UserBook.updated_at.desc())
    )
    result = []
    for entry in entries:
        result.append(
            {
                **await serialize_book(entry.book),
                "status": entry.status,
                "rating": entry.rating,
                "progress": entry.progress,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
            }
        )
    return {"items": result, "count": len(result)}


@router.put("/{book_id}")
async def update_library_item(
    book_id: UUID,
    payload: LibraryItemInput,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    book = await session.get(Book, book_id)
    if book is None:
        raise HTTPException(
            status_code=404, detail={"code": "book_not_found", "message": "Book not found"}
        )
    entry = await session.get(UserBook, {"user_id": user.id, "book_id": book_id})
    if entry is None:
        entry = UserBook(user_id=user.id, book_id=book_id)
        session.add(entry)
        previous_status = None
    else:
        previous_status = entry.status
    entry.status, entry.rating, entry.progress = payload.status, payload.rating, payload.progress
    if previous_status != payload.status:
        session.add(
            ReadingEvent(
                user_id=user.id,
                book_id=book_id,
                event_type=f"status:{payload.status}",
                progress=payload.progress,
            )
        )
    elif payload.progress is not None:
        session.add(
            ReadingEvent(
                user_id=user.id, book_id=book_id, event_type="progress", progress=payload.progress
            )
        )
    await session.commit()
    return {
        "book_id": str(book_id),
        "status": entry.status,
        "rating": entry.rating,
        "progress": entry.progress,
    }


@router.delete("/{book_id}", status_code=204)
async def remove_library_item(
    book_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    entry = await session.get(UserBook, {"user_id": user.id, "book_id": book_id})
    if entry is not None:
        session.add(ReadingEvent(user_id=user.id, book_id=book_id, event_type="removed"))
        await session.delete(entry)
        await session.commit()
    return Response(status_code=204)
