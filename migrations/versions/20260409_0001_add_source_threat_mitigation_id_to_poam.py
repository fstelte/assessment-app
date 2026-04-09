"""Add source_threat_mitigation_id FK to ssp_poam_items

Revision ID: 20260409_0001
Revises: 20260408_0001
Create Date: 2026-04-09 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260409_0001"
down_revision = "20260408_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ssp_poam_items",
        sa.Column(
            "source_threat_mitigation_id",
            sa.Integer,
            sa.ForeignKey("threat_mitigation_actions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_poam_item_threat_mitigation",
        "ssp_poam_items",
        ["source_threat_mitigation_id"],
    )
    op.create_index(
        "ix_ssp_poam_items_source_threat_mitigation_id",
        "ssp_poam_items",
        ["source_threat_mitigation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ssp_poam_items_source_threat_mitigation_id", table_name="ssp_poam_items")
    op.drop_constraint("uq_poam_item_threat_mitigation", "ssp_poam_items", type_="unique")
    op.drop_column("ssp_poam_items", "source_threat_mitigation_id")
