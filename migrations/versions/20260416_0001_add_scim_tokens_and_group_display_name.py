"""Add scim_tokens table and scim_display_name to aad_group_mappings

Revision ID: 20260416_0001
Revises: 20260409_0001
Create Date: 2026-04-16 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260416_0001"
down_revision = "20260409_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "scim_tokens" not in existing_tables:
        op.create_table(
            "scim_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("token_hash", name="uq_scim_tokens_token_hash"),
        )

    existing_columns = {
        col["name"] for col in inspector.get_columns("aad_group_mappings")
    }
    if "scim_display_name" not in existing_columns:
        op.add_column(
            "aad_group_mappings",
            sa.Column("scim_display_name", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    with op.batch_alter_table("aad_group_mappings") as batch_op:
        batch_op.drop_column("scim_display_name")
    op.drop_table("scim_tokens")
