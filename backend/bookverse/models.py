from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    books: Mapped[list["UserBook"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Book(TimestampMixin, Base):
    __tablename__ = "books"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(12))
    published_year: Mapped[int | None] = mapped_column(Integer)
    cover_url: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list["BookSource"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    authors: Mapped[list["BookAuthor"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    genres: Mapped[list["BookGenre"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class BookSource(Base):
    __tablename__ = "book_sources"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_book_source_provider_external"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String(500))
    access_type: Mapped[str] = mapped_column(String(20), default="unknown")
    source_url: Mapped[str | None] = mapped_column(Text)
    access_url: Mapped[str | None] = mapped_column(Text)
    license_or_rights: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    book: Mapped[Book] = relationship(back_populates="sources")


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    books: Mapped[list["BookAuthor"]] = relationship(back_populates="author")


class BookAuthor(Base):
    __tablename__ = "book_authors"
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    book: Mapped[Book] = relationship(back_populates="authors")
    author: Mapped[Author] = relationship(back_populates="books")


class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    books: Mapped[list["BookGenre"]] = relationship(back_populates="genre")


class BookGenre(Base):
    __tablename__ = "book_genres"
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[UUID] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )
    book: Mapped[Book] = relationship(back_populates="genres")
    genre: Mapped[Genre] = relationship(back_populates="books")


class UserBook(TimestampMixin, Base):
    __tablename__ = "user_books"
    __table_args__ = (
        CheckConstraint(
            "status IN ('want_to_read','reading','finished')", name="ck_user_book_status"
        ),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_user_book_rating"
        ),
        CheckConstraint(
            "progress IS NULL OR (progress >= 0 AND progress <= 100)", name="ck_user_book_progress"
        ),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(20), default="want_to_read")
    rating: Mapped[int | None] = mapped_column(Integer)
    progress: Mapped[int | None] = mapped_column(Integer)
    user: Mapped[User] = relationship(back_populates="books")
    book: Mapped[Book] = relationship()


class ReadingEvent(Base):
    __tablename__ = "reading_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    progress: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
