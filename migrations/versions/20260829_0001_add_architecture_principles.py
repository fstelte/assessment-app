"""Add architecture_principles table

Revision ID: 20260829_0001
Revises: 20260608_0002
Create Date: 2026-08-29 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260829_0001"
down_revision = "20260608_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "architecture_principles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_architecture_principles_name",
        "architecture_principles",
        ["name"],
    )


def downgrade() -> None:
    op.drop_index("ix_architecture_principles_name", table_name="architecture_principles")
    op.drop_table("architecture_principles")
