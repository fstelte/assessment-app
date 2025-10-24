"""Add theme preference column to users"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251018_0002"
down_revision = "20251018_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "theme_preference" in existing_columns:
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "theme_preference",
                sa.String(length=20),
                nullable=False,
                server_default="dark",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "theme_preference" not in existing_columns:
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("theme_preference")
