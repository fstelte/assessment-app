"""Add tier_id to bia_components

Revision ID: 20260925_0001
Revises: 20260918_0001
Create Date: 2026-09-25 07:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260925_0001"
down_revision = "20260918_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("bia_components") as batch_op:
        batch_op.add_column(sa.Column("tier_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_bia_components_tier_id",
            "bia_tiers",
            ["tier_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("bia_components") as batch_op:
        batch_op.drop_constraint("fk_bia_components_tier_id", type_="foreignkey")
        batch_op.drop_column("tier_id")
