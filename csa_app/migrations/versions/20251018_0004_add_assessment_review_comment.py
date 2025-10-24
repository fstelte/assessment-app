"""add review comment to assessments

Revision ID: 20251018_0004
Revises: 20251018_0003
Create Date: 2025-10-18 13:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251018_0004"
down_revision = "20251018_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("review_comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "review_comment")
