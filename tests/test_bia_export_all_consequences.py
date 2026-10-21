from __future__ import annotations

import re

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.extensions import db


def _legacy_bia(login):
    context = ContextScope(name="Payments", author_id=login.id)
    component = Component(name="Ledger", context_scope=context)
    db.session.add_all([context, component])
    for prop, category, worst in (
        ("confidentiality", "financial", "minor"),
        ("confidentiality", "privacy", "major"),
        ("confidentiality", "operational", "moderate"),
        ("integrity", "regulatory", "minor"),
    ):
        db.session.add(
            Consequences(
                component=component,
                security_property=prop,
                consequence_category=category,
                consequence_worstcase=worst,
                consequence_realisticcase="minor",
            )
        )
    db.session.commit()
    return context


def _rows(body):
    tbody = body[body.index("<tbody"):body.index("</tbody>")]
    return re.findall(r"<tr[^>]*>(.*?)</tr>", tbody, flags=re.S)


def test_detailed_export_has_one_row_per_cia_group(app, client, login):
    _legacy_bia(login)

    body = client.get("/bia/export_all_consequences?type=detailed").get_data(as_text=True)

    rows = _rows(body)
    assert len(rows) == 2
    confidentiality = next(row for row in rows if "Confidentiality" in row)
    assert "Financial, Operational, Privacy" in confidentiality
    assert re.search(r">\s*major\s*<", confidentiality)
    assert not re.search(r">\s*moderate\s*<", confidentiality)
    assert "will be merged on edit" not in body
    # Stats tile: total counts groups, not records.
    assert re.search(r"text-3xl font-semibold text-white\">\s*2\s*<", body)


def test_summary_export_counts_cia_groups(app, client, login):
    _legacy_bia(login)

    body = client.get("/bia/export_all_consequences?type=summary").get_data(as_text=True)

    row = next(row for row in _rows(body) if "Payments" in row)
    cells = re.findall(r"<td[^>]*>\s*(.*?)\s*</td>", row, flags=re.S)
    assert "2" in cells
    assert "4" not in cells
