"""Add ticket link and archive metadata to risks

Revision ID: 20251205_0014
Revises: 20251205_0013
Create Date: 2025-12-05 15:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251205_0014"
down_revision = "20251205_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("risk_items", sa.Column("ticket_url", sa.String(length=500), nullable=True))
    op.add_column("risk_items", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_items", "closed_at")
    op.drop_column("risk_items", "ticket_url")
