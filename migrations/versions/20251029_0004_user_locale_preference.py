"""Add locale preference to users

Revision ID: 20251029_0004
Revises: 20241024_0003
Create Date: 2025-10-29 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251029_0004"
down_revision = "20241024_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("users")}
    if "locale_preference" not in existing_columns:
        op.add_column(
            "users",
            sa.Column("locale_preference", sa.String(length=10), nullable=False, server_default=sa.text("'en'")),
        )
    op.execute("UPDATE users SET locale_preference = 'en' WHERE locale_preference IS NULL")
    if dialect_name != "sqlite":
        op.alter_column("users", "locale_preference", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "locale_preference")
