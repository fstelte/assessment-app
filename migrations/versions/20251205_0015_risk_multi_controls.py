"""Support multiple CSA control links per risk.

Revision ID: 20251205_0015_risk_multi_controls
Revises: 20251205_0014_risk_archive_ticket
Create Date: 2025-12-05 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251205_0015_risk_multi_controls"
down_revision = "20251205_0014_risk_archive_ticket"
branch_labels = None
depends_on = None


risk_items = sa.table(
    "risk_items",
    sa.column("id", sa.Integer),
    sa.column("csa_control_id", sa.Integer),
)

risk_control_links = sa.table(
    "risk_control_links",
    sa.column("risk_id", sa.Integer),
    sa.column("control_id", sa.Integer),
)


def upgrade() -> None:
    op.create_table(
        "risk_control_links",
        sa.Column("risk_id", sa.Integer(), nullable=False),
        sa.Column("control_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["risk_id"], ["risk_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["control_id"], ["csa_controls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("risk_id", "control_id"),
        sa.UniqueConstraint("risk_id", "control_id", name="uq_risk_control_link"),
    )

    bind = op.get_bind()
    existing_links = bind.execute(
        sa.select(risk_items.c.id, risk_items.c.csa_control_id).where(risk_items.c.csa_control_id.isnot(None))
    ).fetchall()
    if existing_links:
        bind.execute(
            risk_control_links.insert(),
            [
                {"risk_id": risk_id, "control_id": control_id}
                for risk_id, control_id in existing_links
                if control_id is not None
            ],
        )

    op.drop_constraint("ck_risk_control_required_for_mitigate", "risk_items", type_="check")
    op.drop_constraint("risk_items_csa_control_id_fkey", "risk_items", type_="foreignkey")
    op.drop_column("risk_items", "csa_control_id")


def downgrade() -> None:
    op.add_column("risk_items", sa.Column("csa_control_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "risk_items_csa_control_id_fkey",
        "risk_items",
        "csa_controls",
        ["csa_control_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    bind = op.get_bind()
    current_links = bind.execute(
        sa.select(risk_control_links.c.risk_id, risk_control_links.c.control_id)
        .order_by(risk_control_links.c.risk_id.asc(), risk_control_links.c.control_id.asc())
    ).fetchall()
    migrated: set[int] = set()
    for risk_id, control_id in current_links:
        if risk_id in migrated:
            continue
        bind.execute(
            sa.update(risk_items)
            .where(risk_items.c.id == risk_id)
            .values(csa_control_id=control_id)
        )
        migrated.add(risk_id)

    op.create_check_constraint(
        "ck_risk_control_required_for_mitigate",
        "risk_items",
        "treatment != 'mitigate' OR csa_control_id IS NOT NULL",
    )

    op.drop_table("risk_control_links")
