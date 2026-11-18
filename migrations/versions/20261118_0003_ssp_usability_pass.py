"""SSP usability pass: option lists, BIA-sourced interconnections, Jira and ADR links

Feature 20261118-144354-ssp-metadata-interconnections-adr:

- ``ssp_options`` (admin-managed laws/regulations/policies and monitoring
  frequencies) and the ``ssp_plan_laws`` link table (decision 20261118-1500).
- ``ssp_plans.monitoring_frequency`` (free text) becomes
  ``monitoring_frequency_id``. Existing values are grouped by normalised form
  (strip, collapse whitespace, casefold) and seeded as one option per group,
  named with the first-seen trimmed spelling (decision 20261118-1530, CHK007).
- ``ssp_plans.adr_register_url``, ``ssp_poam_items.jira_url`` and
  ``adr_records.external_url`` (decisions 20261118-1510, -1515).
- ``ssp_interconnections.source``: rows whose normalised name appears in the
  scope's BIA ``interfaces`` are backfilled as ``bia`` (decision 20261118-1455).
- ``adr_records.context``/``decision`` become nullable, and
  ``status_before_supersede`` is added (decision 20261118-1530, CHK001).

``ssp_plans.laws_regulations`` stays as a dormant column.

Downgrade restores the free-text frequency from the linked option name, fills
NULL ADR context/decision with an empty string and drops everything else that
this revision added, including all option data.

Revision ID: 20261118_0003
Revises: 20261118_0002
Create Date: 2026-11-18 16:00:00.000000
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261118_0003"
down_revision = "20261118_0002"
branch_labels = None
depends_on = None

OPTION_KIND_VALUES = ("law_regulation", "monitoring_frequency")
SOURCE_VALUES = ("bia", "manual")
ADR_STATUS_VALUES = ("proposed", "accepted", "rejected", "deprecated", "superseded")


def _normalise(value: str) -> str:
    # Inline copy of scaffold.apps.ssp.services.normalise_name: migrations must
    # not import application code.
    return " ".join(value.split()).casefold()


def _parse_interfaces(raw: str | None) -> list[str]:
    return [entry.strip() for entry in re.split(r"[\n;]+", raw or "") if entry.strip()]


def upgrade() -> None:
    op.create_table(
        "ssp_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "kind",
            sa.Enum(*OPTION_KIND_VALUES, name="ssp_option_kind", native_enum=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "name", name="uq_ssp_options_kind_name"),
    )
    op.create_table(
        "ssp_plan_laws",
        sa.Column(
            "ssp_id",
            sa.Integer(),
            sa.ForeignKey("ssp_plans.id", ondelete="CASCADE", name="fk_ssp_plan_laws_ssp_id"),
            primary_key=True,
        ),
        sa.Column(
            "option_id",
            sa.Integer(),
            sa.ForeignKey("ssp_options.id", ondelete="CASCADE", name="fk_ssp_plan_laws_option_id"),
            primary_key=True,
        ),
    )

    with op.batch_alter_table("ssp_plans") as batch_op:
        batch_op.add_column(sa.Column("monitoring_frequency_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("adr_register_url", sa.String(500), nullable=True))
        batch_op.create_foreign_key(
            "fk_ssp_plans_monitoring_frequency_id",
            "ssp_options",
            ["monitoring_frequency_id"],
            ["id"],
            ondelete="SET NULL",
        )

    conn = op.get_bind()
    _migrate_frequencies(conn)

    with op.batch_alter_table("ssp_plans") as batch_op:
        batch_op.drop_column("monitoring_frequency")

    with op.batch_alter_table("ssp_interconnections") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source",
                sa.Enum(*SOURCE_VALUES, name="ssp_interconnection_source", native_enum=False),
                nullable=False,
                server_default="manual",
            )
        )
    _backfill_interconnection_source(conn)

    with op.batch_alter_table("ssp_poam_items") as batch_op:
        batch_op.add_column(sa.Column("jira_url", sa.String(500), nullable=True))

    with op.batch_alter_table("adr_records") as batch_op:
        batch_op.add_column(sa.Column("external_url", sa.String(500), nullable=True))
        batch_op.add_column(
            sa.Column(
                "status_before_supersede",
                sa.Enum(*ADR_STATUS_VALUES, name="adr_status_before_supersede", native_enum=False),
                nullable=True,
            )
        )
        batch_op.alter_column("context", existing_type=sa.Text(), nullable=True)
        batch_op.alter_column("decision", existing_type=sa.Text(), nullable=True)


def _migrate_frequencies(conn) -> None:
    rows = conn.execute(
        sa.text(
            "SELECT id, monitoring_frequency FROM ssp_plans "
            "WHERE monitoring_frequency IS NOT NULL ORDER BY id"
        )
    ).fetchall()
    option_ids: dict[str, int] = {}
    now = datetime.now(UTC)
    for plan_id, raw in rows:
        name = (raw or "").strip()
        if not name:
            continue
        key = _normalise(name)
        if key not in option_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO ssp_options (kind, name, is_active, created_at, updated_at) "
                    "VALUES ('monitoring_frequency', :name, :active, :now, :now)"
                ),
                {"name": " ".join(name.split()), "active": True, "now": now},
            )
            option_ids[key] = conn.execute(
                sa.text("SELECT id FROM ssp_options WHERE kind = 'monitoring_frequency' AND name = :name"),
                {"name": " ".join(name.split())},
            ).scalar_one()
        conn.execute(
            sa.text("UPDATE ssp_plans SET monitoring_frequency_id = :option_id WHERE id = :plan_id"),
            {"option_id": option_ids[key], "plan_id": plan_id},
        )


def _backfill_interconnection_source(conn) -> None:
    rows = conn.execute(
        sa.text(
            "SELECT i.id, i.system_name, s.interfaces FROM ssp_interconnections i "
            "JOIN ssp_plans p ON p.id = i.ssp_id "
            "JOIN bia_context_scope s ON s.id = p.context_scope_id"
        )
    ).fetchall()
    for row_id, system_name, interfaces in rows:
        names = {_normalise(entry) for entry in _parse_interfaces(interfaces)}
        if system_name and _normalise(system_name) in names:
            conn.execute(
                sa.text("UPDATE ssp_interconnections SET source = 'bia' WHERE id = :id"),
                {"id": row_id},
            )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("UPDATE adr_records SET context = '' WHERE context IS NULL"))
    conn.execute(sa.text("UPDATE adr_records SET decision = '' WHERE decision IS NULL"))
    with op.batch_alter_table("adr_records") as batch_op:
        batch_op.alter_column("decision", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column("context", existing_type=sa.Text(), nullable=False)
        batch_op.drop_column("status_before_supersede")
        batch_op.drop_column("external_url")

    with op.batch_alter_table("ssp_poam_items") as batch_op:
        batch_op.drop_column("jira_url")

    with op.batch_alter_table("ssp_interconnections") as batch_op:
        batch_op.drop_column("source")

    with op.batch_alter_table("ssp_plans") as batch_op:
        batch_op.add_column(sa.Column("monitoring_frequency", sa.String(100), nullable=True))
    conn.execute(
        sa.text(
            "UPDATE ssp_plans SET monitoring_frequency = ("
            "SELECT substr(o.name, 1, 100) FROM ssp_options o WHERE o.id = ssp_plans.monitoring_frequency_id)"
        )
    )
    with op.batch_alter_table("ssp_plans") as batch_op:
        batch_op.drop_constraint("fk_ssp_plans_monitoring_frequency_id", type_="foreignkey")
        batch_op.drop_column("adr_register_url")
        batch_op.drop_column("monitoring_frequency_id")

    op.drop_table("ssp_plan_laws")
    op.drop_table("ssp_options")
