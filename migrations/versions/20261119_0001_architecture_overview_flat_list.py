"""Architecture overview becomes a flat list of files

Feature 20261119-182410-ssp-architecture-overview-multiple-files:

- Keep only the highest ``version_number`` per SSP; older history rows are
  deleted permanently (decision 20261119-1826). The number of pruned rows is
  logged (decision 20261120-0900, CHK001).
- Drop ``uq_ssp_architecture_overview_version`` and ``version_number``.

Downgrade re-adds ``version_number`` and numbers every remaining row 1..n per
SSP by ``uploaded_at, id``, so the newest file becomes current again. Pruned
history is not restored.

Revision ID: 20261119_0001
Revises: 20261118_0003
Create Date: 2026-11-20 09:30:00.000000
"""

from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261119_0001"
down_revision = "20261118_0003"
branch_labels = None
depends_on = None

TABLE = "ssp_architecture_overview_versions"
CONSTRAINT = "uq_ssp_architecture_overview_version"
_OLDER_THAN_CURRENT = (
    f"version_number < (SELECT MAX(m.version_number) FROM {TABLE} m WHERE m.ssp_id = {TABLE}.ssp_id)"
)

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    bind = op.get_bind()
    pruned, ssps = bind.execute(
        sa.text(f"SELECT COUNT(*), COUNT(DISTINCT ssp_id) FROM {TABLE} WHERE {_OLDER_THAN_CURRENT}")  # nosec B608
    ).one()
    bind.execute(sa.text(f"DELETE FROM {TABLE} WHERE {_OLDER_THAN_CURRENT}"))  # nosec B608
    logger.info("pruned %d historical architecture overview versions across %d SSPs", pruned, ssps)

    with op.batch_alter_table(TABLE) as batch_op:
        batch_op.drop_constraint(CONSTRAINT, type_="unique")
        batch_op.drop_column("version_number")


def downgrade() -> None:
    with op.batch_alter_table(TABLE) as batch_op:
        batch_op.add_column(sa.Column("version_number", sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(f"SELECT id, ssp_id FROM {TABLE} ORDER BY ssp_id, uploaded_at, id")  # nosec B608
    ).fetchall()
    numbers: dict[int, int] = {}
    updates = []
    for row_id, ssp_id in rows:
        numbers[ssp_id] = numbers.get(ssp_id, 0) + 1
        updates.append({"id": row_id, "number": numbers[ssp_id]})
    if updates:
        bind.execute(sa.text(f"UPDATE {TABLE} SET version_number = :number WHERE id = :id"), updates)  # nosec B608

    with op.batch_alter_table(TABLE) as batch_op:
        batch_op.alter_column("version_number", existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint(CONSTRAINT, ["ssp_id", "version_number"])
