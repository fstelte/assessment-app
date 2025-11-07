"""Add Entra identity fields and group mapping table

Revision ID: 20251106_0005
Revises: 20251029_0004
Create Date: 2025-11-06 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251106_0005"
down_revision = "20251029_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "azure_oid" not in existing_columns:
        op.add_column("users", sa.Column("azure_oid", sa.String(length=255), nullable=True))
    if "aad_upn" not in existing_columns:
        op.add_column("users", sa.Column("aad_upn", sa.String(length=255), nullable=True))

    existing_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_azure_oid" not in existing_indexes:
        op.create_index("ix_users_azure_oid", "users", ["azure_oid"], unique=True)
    if "ix_users_aad_upn" not in existing_indexes:
        op.create_index("ix_users_aad_upn", "users", ["aad_upn"], unique=True)

    existing_tables = set(inspector.get_table_names())
    if "aad_group_mappings" not in existing_tables:
        op.create_table(
            "aad_group_mappings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("group_object_id", sa.String(length=255), nullable=False),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("group_object_id", name="uq_aad_group_mappings_group_object_id"),
        )
        op.create_index("ix_aad_group_mappings_role_id", "aad_group_mappings", ["role_id"])


def downgrade() -> None:
    op.drop_index("ix_aad_group_mappings_role_id", table_name="aad_group_mappings")
    op.drop_table("aad_group_mappings")

    op.drop_index("ix_users_aad_upn", table_name="users")
    op.drop_index("ix_users_azure_oid", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("aad_upn")
        batch_op.drop_column("azure_oid")
