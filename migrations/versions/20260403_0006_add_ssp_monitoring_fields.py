"""Add continuous monitoring fields to ssp_plans

Revision ID: 20260403_0006
Revises: 20260403_0005
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260403_0006"
down_revision = "20260403_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ssp_plans", sa.Column("monitoring_kpis_kris", sa.Text, nullable=True))
    op.add_column("ssp_plans", sa.Column("monitoring_what", sa.Text, nullable=True))
    op.add_column("ssp_plans", sa.Column("monitoring_who", sa.Text, nullable=True))
    op.add_column("ssp_plans", sa.Column("monitoring_tools", sa.Text, nullable=True))
    op.add_column("ssp_plans", sa.Column("monitoring_frequency", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("ssp_plans", "monitoring_frequency")
    op.drop_column("ssp_plans", "monitoring_tools")
    op.drop_column("ssp_plans", "monitoring_who")
    op.drop_column("ssp_plans", "monitoring_what")
    op.drop_column("ssp_plans", "monitoring_kpis_kris")
