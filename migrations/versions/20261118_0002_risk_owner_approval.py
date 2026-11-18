"""Add owner approval columns to risk_items

The risk's owner (treatment_owner) approves or rejects the risk's assessment
and treatment (decisions 20261118-1038, -1045). Existing rows keep NULLs and
therefore start as "awaiting approval".

Downgrade drops the four columns and all approval data with them.

Revision ID: 20261118_0002
Revises: 20261118_0001
Create Date: 2026-11-18 11:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261118_0002"
down_revision = "20261118_0001"
branch_labels = None
depends_on = None

APPROVAL_STATUS_VALUES = ("approved", "rejected")


def upgrade() -> None:
    with op.batch_alter_table("risk_items") as batch_op:
        batch_op.add_column(
            sa.Column(
                "approval_status",
                sa.Enum(*APPROVAL_STATUS_VALUES, name="risk_approval_status", native_enum=False),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("approval_decided_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("approval_decided_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("approval_comment", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_risk_items_approval_decided_by_id",
            "users",
            ["approval_decided_by_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("risk_items") as batch_op:
        batch_op.drop_constraint("fk_risk_items_approval_decided_by_id", type_="foreignkey")
        batch_op.drop_column("approval_comment")
        batch_op.drop_column("approval_decided_by_id")
        batch_op.drop_column("approval_decided_at")
        batch_op.drop_column("approval_status")
