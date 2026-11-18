"""Add residual impact/chance and mitigated_at to risk_items

Risks carry a residual assessment and a mitigated marker so the risk workspace
can show the actual score: residual when mitigated, initial otherwise
(decisions 20261118-0751 and 20261118-0800). Existing rows keep NULLs, so their
actual score equals their initial score.

Downgrade drops the three columns and the residual/mitigated data with them.

Revision ID: 20261118_0001
Revises: 20261107_0001
Create Date: 2026-11-18 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261118_0001"
down_revision = "20261107_0001"
branch_labels = None
depends_on = None

RISK_IMPACT_VALUES = ("insignificant", "minor", "moderate", "major", "catastrophic")
RISK_CHANCE_VALUES = ("rare", "unlikely", "possible", "likely", "almost_certain")


def upgrade() -> None:
    with op.batch_alter_table("risk_items") as batch_op:
        batch_op.add_column(sa.Column("mitigated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "residual_impact",
                sa.Enum(*RISK_IMPACT_VALUES, name="risk_impact", native_enum=False),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "residual_chance",
                sa.Enum(*RISK_CHANCE_VALUES, name="risk_chance", native_enum=False),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("risk_items") as batch_op:
        batch_op.drop_column("residual_chance")
        batch_op.drop_column("residual_impact")
        batch_op.drop_column("mitigated_at")
