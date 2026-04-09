"""Encrypt sensitive MFA fields (secret and backup_codes)

Revision ID: 20260408_0001
Revises: 20260407_0001
Create Date: 2026-04-08 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260408_0001"
down_revision = "20260407_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("mfa_settings") as batch_op:
        batch_op.alter_column(
            "secret",
            existing_type=sa.String(64),
            type_=sa.Text(),
            nullable=False,
        )
        batch_op.alter_column(
            "backup_codes",
            existing_type=sa.Text(),
            type_=sa.Text(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("mfa_settings") as batch_op:
        batch_op.alter_column(
            "secret",
            existing_type=sa.Text(),
            type_=sa.String(64),
            nullable=False,
        )
        batch_op.alter_column(
            "backup_codes",
            existing_type=sa.Text(),
            type_=sa.Text(),
            nullable=True,
        )
