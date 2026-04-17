"""Make aad_group_mappings.role_id nullable for SCIM group provisioning

Revision ID: 20260417_0001
Revises: 20260416_0001
Create Date: 2026-04-17 00:00:00.000000

Without this change, Entra's SCIM connector fails to create groups because
role_id has a NOT NULL constraint. Groups arrive without a role assignment
(the admin maps them later via the UI), causing every POST /scim/v2/Groups
to return a 500 and Entra to report it as a provisioning failure.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260417_0001"
down_revision = "20260416_0001"
branch_labels = None
depends_on = None


def _get_fk_name(bind, table: str, referred_table: str) -> str | None:
    """Return the name of the FK constraint from *table* pointing to *referred_table*."""
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table):
        if fk.get("referred_table") == referred_table:
            return fk.get("name")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    fk_name = _get_fk_name(bind, "aad_group_mappings", "roles")

    with op.batch_alter_table("aad_group_mappings") as batch_op:
        batch_op.alter_column(
            "role_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        if fk_name:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_aad_group_mappings_role_id",
            "roles",
            ["role_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM aad_group_mappings WHERE role_id IS NULL"))

    fk_name = _get_fk_name(bind, "aad_group_mappings", "roles")

    with op.batch_alter_table("aad_group_mappings") as batch_op:
        if fk_name:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_aad_group_mappings_role_id_cascade",
            "roles",
            ["role_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "role_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
