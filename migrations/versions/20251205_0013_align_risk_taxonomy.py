"""Align risk taxonomy with BIA consequence labels

Revision ID: 20251205_0013
Revises: 20251205_0012
Create Date: 2025-12-05 11:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251205_0013"
down_revision = "20251205_0012"
branch_labels = None
depends_on = None


_IMPACT_REMAP = {
    "very_low": "insignificant",
    "low": "minor",
    "medium": "moderate",
    "high": "major",
    "very_high": "catastrophic",
}

_AREA_REMAP = {
    "confidentiality": "privacy",
    "integrity": "operational",
    "availability": "operational",
    "financial": "financial",
    "reputation": "operational",
    "compliance": "regulatory",
}


def upgrade() -> None:
    conn = op.get_bind()
    for previous, updated in _IMPACT_REMAP.items():
        conn.execute(
            sa.text("UPDATE risk_items SET impact = :updated WHERE impact = :previous"),
            {"updated": updated, "previous": previous},
        )
    for previous, updated in _AREA_REMAP.items():
        conn.execute(
            sa.text("UPDATE risk_impact_areas SET area = :updated WHERE area = :previous"),
            {"updated": updated, "previous": previous},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for previous, updated in _IMPACT_REMAP.items():
        conn.execute(
            sa.text("UPDATE risk_items SET impact = :old WHERE impact = :current"),
            {"old": previous, "current": updated},
        )
    for previous, updated in _AREA_REMAP.items():
        conn.execute(
            sa.text("UPDATE risk_impact_areas SET area = :old WHERE area = :current"),
            {"old": previous, "current": updated},
        )
