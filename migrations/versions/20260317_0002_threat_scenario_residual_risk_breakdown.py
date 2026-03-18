"""Replace residual_risk text with residual_likelihood/impact/score/level

Revision ID: 20260317_0002
Revises: 20260317_0001
Create Date: 2026-03-17 00:00:01.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260317_0002"
down_revision = "20260317_0001"
branch_labels = None
depends_on = None

RISK_LEVEL_VALUES = ("low", "medium", "high", "critical")


def upgrade() -> None:
    with op.batch_alter_table("threat_scenarios") as batch_op:
        batch_op.drop_column("residual_risk")
        batch_op.add_column(sa.Column("residual_likelihood", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("residual_impact", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("residual_risk_score", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "residual_risk_level",
                sa.Enum(*RISK_LEVEL_VALUES, name="residual_risk_level_enum", native_enum=False),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("threat_scenarios") as batch_op:
        batch_op.drop_column("residual_risk_level")
        batch_op.drop_column("residual_risk_score")
        batch_op.drop_column("residual_impact")
        batch_op.drop_column("residual_likelihood")
        batch_op.add_column(sa.Column("residual_risk", sa.Text(), nullable=True))
