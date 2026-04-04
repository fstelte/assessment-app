"""Add context_scope_id to threat_models

Revision ID: 20260404_0001
Revises: 20260403_0006
Create Date: 2026-04-04 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260404_0001"
down_revision = "20260403_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "threat_models",
        sa.Column("context_scope_id", sa.Integer, sa.ForeignKey("bia_context_scope.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_threat_models_context_scope_id", "threat_models", ["context_scope_id"])


def downgrade() -> None:
    op.drop_index("ix_threat_models_context_scope_id", table_name="threat_models")
    op.drop_column("threat_models", "context_scope_id")
