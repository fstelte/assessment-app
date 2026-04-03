"""Drop system_type column from bia_context_scope (replaced by tier)

Revision ID: 20260403_0004
Revises: 20260403_0003
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260403_0004"
down_revision = "20260403_0003"
branch_labels = None
depends_on = None

SYSTEM_TYPE_VALUES = ("major_application", "general_support_system")


def upgrade() -> None:
    op.drop_column("bia_context_scope", "system_type")


def downgrade() -> None:
    op.add_column(
        "bia_context_scope",
        sa.Column(
            "system_type",
            sa.Enum(
                *SYSTEM_TYPE_VALUES,
                name="context_scope_system_type",
                native_enum=False,
            ),
            nullable=True,
        ),
    )
