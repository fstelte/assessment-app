"""Add used_for_authorization and authorization_note to component environments

Revision ID: 20260918_0001
Revises: 20260830_0001
Create Date: 2026-09-18 17:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260918_0001"
down_revision = "20260830_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bia_component_environments",
        sa.Column("used_for_authorization", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "bia_component_environments",
        sa.Column("authorization_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bia_component_environments", "authorization_note")
    op.drop_column("bia_component_environments", "used_for_authorization")
