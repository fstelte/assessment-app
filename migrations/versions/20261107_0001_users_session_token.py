"""Add users.session_token for restore-safe session identity

Sessions and remember-me cookies carry this token instead of ``users.id``
(decision 20261107-0848). Every existing user gets a fresh token, so all
sessions from before this migration end once.

Downgrade only together with rolling back the code: after dropping the column,
``User.get_id()`` in the new code refers to a column that no longer exists.

Revision ID: 20261107_0001
Revises: 20260925_0001
Create Date: 2026-11-07 09:30:00.000000
"""

from __future__ import annotations

import secrets

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261107_0001"
down_revision = "20260925_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("session_token", sa.String(length=64), nullable=True))

    conn = op.get_bind()
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("session_token", sa.String))
    for (user_id,) in conn.execute(sa.select(users.c.id)).fetchall():
        conn.execute(
            users.update().where(users.c.id == user_id).values(session_token=secrets.token_hex(32))
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("session_token", existing_type=sa.String(length=64), nullable=False)
        batch_op.create_index("ix_users_session_token", ["session_token"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_session_token")
        batch_op.drop_column("session_token")
