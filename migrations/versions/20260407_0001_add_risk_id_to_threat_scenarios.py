"""Add risk_id to threat_scenarios

Revision ID: 20260407_0001
Revises: 20260404_0001
Create Date: 2026-04-07 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260407_0001"
down_revision = "20260404_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "threat_scenarios",
        sa.Column(
            "risk_id",
            sa.Integer,
            sa.ForeignKey("risk_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_threat_scenarios_risk_id", "threat_scenarios", ["risk_id"])


def downgrade() -> None:
    op.drop_index("ix_threat_scenarios_risk_id", table_name="threat_scenarios")
    op.drop_column("threat_scenarios", "risk_id")
