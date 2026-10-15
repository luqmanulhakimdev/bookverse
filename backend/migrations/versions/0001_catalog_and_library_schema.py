"""Create normalized BookVerse catalog and library tables."""

import sqlalchemy as sa
from alembic import op

revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    uuid = sa.Uuid(as_uuid=True)
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "books",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("language", sa.String(12)),
        sa.Column("published_year", sa.Integer()),
        sa.Column("cover_url", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_books_title", "books", ["title"])
    op.create_table(
        "authors",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(300), nullable=False, unique=True),
    )
    op.create_index("ix_authors_name", "authors", ["name"])
    op.create_table(
        "genres",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
    )
    op.create_table(
        "book_sources",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("book_id", uuid, sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("access_type", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("access_url", sa.Text()),
        sa.Column("license_or_rights", sa.Text()),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("provider", "external_id", name="uq_book_source_provider_external"),
    )
    op.create_index("ix_book_sources_book_id", "book_sources", ["book_id"])
    op.create_index("ix_book_sources_provider", "book_sources", ["provider"])
    op.create_table(
        "book_authors",
        sa.Column("book_id", uuid, sa.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "author_id", uuid, sa.ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "book_genres",
        sa.Column("book_id", uuid, sa.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "genre_id", uuid, sa.ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_table(
        "user_books",
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("book_id", uuid, sa.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="want_to_read"),
        sa.Column("rating", sa.Integer()),
        sa.Column("progress", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('want_to_read','reading','finished')", name="ck_user_book_status"
        ),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_user_book_rating"
        ),
        sa.CheckConstraint(
            "progress IS NULL OR (progress >= 0 AND progress <= 100)", name="ck_user_book_progress"
        ),
    )
    op.create_table(
        "reading_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", uuid, sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("progress", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_reading_events_user_id", "reading_events", ["user_id"])
    op.create_index("ix_reading_events_book_id", "reading_events", ["book_id"])


def downgrade():
    op.drop_index("ix_reading_events_book_id", table_name="reading_events")
    op.drop_index("ix_reading_events_user_id", table_name="reading_events")
    op.drop_table("reading_events")
    op.drop_table("user_books")
    op.drop_table("book_genres")
    op.drop_table("book_authors")
    op.drop_index("ix_book_sources_provider", table_name="book_sources")
    op.drop_index("ix_book_sources_book_id", table_name="book_sources")
    op.drop_table("book_sources")
    op.drop_table("genres")
    op.drop_index("ix_authors_name", table_name="authors")
    op.drop_table("authors")
    op.drop_index("ix_books_title", table_name="books")
    op.drop_table("books")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
