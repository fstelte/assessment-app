"""Add translation keys to DPIA questions

Revision ID: 20251121_0008
Revises: 20251120_0007
Create Date: 2025-11-16 15:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251121_0008"
down_revision = "20251120_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dpia_questions", sa.Column("text_key", sa.String(length=255), nullable=True))
    op.add_column("dpia_questions", sa.Column("help_key", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_dpia_questions_text_key", "dpia_questions", ["text_key"])


def downgrade() -> None:
    op.drop_constraint("uq_dpia_questions_text_key", "dpia_questions", type_="unique")
    op.drop_column("dpia_questions", "help_key")
    op.drop_column("dpia_questions", "text_key")
