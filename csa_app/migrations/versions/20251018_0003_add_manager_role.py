"""create manager role

Revision ID: 20251018_0003
Revises: 20251018_0002
Create Date: 2025-10-18 12:00:00

"""
from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251018_0003"
down_revision = "20251018_0002"
branch_labels = None
depends_on = None

roles_table = sa.table(
    "roles",
    sa.column("name", sa.String(length=50)),
    sa.column("description", sa.String(length=255)),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    existing = {
        row.name
        for row in bind.execute(sa.select(roles_table.c.name))
    }

    target_roles = [
        ("manager", "Assessment manager"),
    ]

    to_insert = []
    timestamp = datetime.now(timezone.utc)

    for name, description in target_roles:
        if name not in existing:
            to_insert.append(
                {
                    "name": name,
                    "description": description,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )

    if to_insert:
        bind.execute(sa.insert(roles_table), to_insert)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.delete(roles_table).where(roles_table.c.name == "manager"))
