"""Add POA&M tables to SSP module

Revision ID: 20260403_0005
Revises: 20260403_0004
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260403_0005"
down_revision = "20260403_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ssp_poam_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "ssp_id",
            sa.Integer,
            sa.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weakness_description", sa.Text, nullable=False),
        sa.Column("resources_required", sa.Text, nullable=True),
        sa.Column("point_of_contact", sa.String(255), nullable=True),
        sa.Column("scheduled_completion", sa.Date, nullable=True),
        sa.Column("estimated_cost", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_progress",
                "completed",
                "cancelled",
                "delayed",
                name="ssp_poam_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="open",
        ),
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
        "ssp_poam_milestones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "item_id",
            sa.Integer,
            sa.ForeignKey("ssp_poam_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("scheduled_date", sa.Date, nullable=True),
        sa.Column("completed_date", sa.Date, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ssp_poam_milestones")
    op.drop_table("ssp_poam_items")
