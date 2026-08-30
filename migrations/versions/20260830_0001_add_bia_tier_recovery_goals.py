"""Add rto_goal_seconds and rpo_goal_seconds to bia_tiers

Revision ID: 20260830_0001
Revises: 20260829_0003
Create Date: 2026-08-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260830_0001"
down_revision = "20260829_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bia_tiers", sa.Column("rto_goal_seconds", sa.Integer(), nullable=True))
    op.add_column("bia_tiers", sa.Column("rpo_goal_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("bia_tiers", "rpo_goal_seconds")
    op.drop_column("bia_tiers", "rto_goal_seconds")
