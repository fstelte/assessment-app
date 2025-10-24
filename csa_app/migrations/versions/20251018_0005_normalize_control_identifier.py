"""Update control schema to rely on section/domain/description only

Revision ID: 20251018_0005
Revises: 20251018_0004
Create Date: 2025-10-18
"""

from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20251018_0005"
down_revision = "20251018_0004"
branch_labels = None
depends_on = None

_CODE_PATTERN = re.compile(r"^([A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)")


def _derive_section(domain: str | None, existing: str | None) -> str | None:
    candidate = (existing or "").strip() or None
    if candidate:
        return candidate

    if not domain:
        return None

    match = _CODE_PATTERN.match(domain.strip())
    if match:
        return match.group(1).split(".")[0]

    return None


def upgrade() -> None:
    bind = op.get_bind()
    rows = list(
        bind.execute(
            sa.text("SELECT id, domain, identifier, title, section FROM controls ORDER BY id")
        ).mappings()
    )

    seen_domains: set[str] = set()

    for row in rows:
        domain = (row["domain"] or "").strip()
        identifier = (row["identifier"] or "").strip()
        title = (row["title"] or "").strip()
        section = (row["section"] or "").strip() or None

        if not domain:
            domain = identifier or title or f"Control {row['id']}"

        base_domain = domain
        counter = 1
        while domain in seen_domains:
            counter += 1
            domain = f"{base_domain} ({counter})"
        seen_domains.add(domain)

        section_value = _derive_section(domain, section) or None

        bind.execute(
            sa.text("UPDATE controls SET domain = :domain, section = :section WHERE id = :id"),
            {"domain": domain, "section": section_value, "id": row["id"]},
        )

    op.drop_index("ix_controls_identifier", table_name="controls")

    with op.batch_alter_table("controls", schema=None) as batch:
        batch.alter_column(
            "domain",
            existing_type=sa.String(length=120),
            type_=sa.String(length=255),
            nullable=False,
        )
        batch.drop_column("identifier")
        batch.drop_column("title")
        batch.drop_column("category")

    op.create_index("ix_controls_domain", "controls", ["domain"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_controls_domain", table_name="controls")

    with op.batch_alter_table("controls", schema=None) as batch:
        batch.add_column(sa.Column("category", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("title", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("identifier", sa.String(length=120), nullable=True))
        batch.alter_column(
            "domain",
            existing_type=sa.String(length=255),
            type_=sa.String(length=120),
            nullable=True,
        )

    rows = list(bind.execute(sa.text("SELECT id, domain, section FROM controls ORDER BY id")).mappings())

    for row in rows:
        domain = (row["domain"] or "").strip()
        section = (row["section"] or "").strip()
        identifier = domain.split()[0] if domain else None
        title = domain

        bind.execute(
            sa.text(
                "UPDATE controls SET identifier = :identifier, title = :title, category = NULL, domain = :domain WHERE id = :id"
            ),
            {
                "identifier": identifier,
                "title": title,
                "domain": domain,
                "id": row["id"]},
        )

    op.create_index("ix_controls_identifier", "controls", ["identifier"], unique=True)
