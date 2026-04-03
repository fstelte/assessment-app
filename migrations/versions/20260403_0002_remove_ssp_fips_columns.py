"""Remove FIPS rating columns from ssp_plans (stub — columns already dropped)

Revision ID: 20260403_0002
Revises: 20260403_0001
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20260403_0002"
down_revision = "20260403_0001"
branch_labels = None
depends_on = None

FIPS_RATING_VALUES = ("not_set", "low", "moderate", "high")


def upgrade() -> None:
    # Columns were dropped here; this stub exists to preserve the revision chain.
    pass


def downgrade() -> None:
    pass
