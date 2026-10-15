"""Persist source record links separately from access links."""

import sqlalchemy as sa
from alembic import op

revision = "0003_source_url"
down_revision = "0002_refresh"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("book_sources", sa.Column("source_url", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("book_sources", "source_url")
