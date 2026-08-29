"""Add adr_records and adr_secondary_principles tables

Revision ID: 20260829_0002
Revises: 20260829_0001
Create Date: 2026-08-29 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260829_0002"
down_revision = "20260829_0001"
branch_labels = None
depends_on = None

ADR_STATUS_VALUES = ("proposed", "accepted", "rejected", "deprecated", "superseded")


def upgrade() -> None:
    op.create_table(
        "adr_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ssp_id",
            sa.Integer(),
            sa.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*ADR_STATUS_VALUES, name="adr_status", native_enum=False),
            nullable=False,
            server_default="proposed",
        ),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("consequences", sa.Text(), nullable=True),
        sa.Column(
            "primary_principle_id",
            sa.Integer(),
            sa.ForeignKey("architecture_principles.id"),
            nullable=False,
        ),
        sa.Column(
            "supersedes_id",
            sa.Integer(),
            sa.ForeignKey("adr_records.id"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_on", sa.Date(), nullable=True),
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

    op.create_table(
        "adr_secondary_principles",
        sa.Column(
            "adr_id",
            sa.Integer(),
            sa.ForeignKey("adr_records.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "principle_id",
            sa.Integer(),
            sa.ForeignKey("architecture_principles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("adr_secondary_principles")
    op.drop_table("adr_records")
