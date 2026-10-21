from __future__ import annotations

import re

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.extensions import db


def _legacy_bia(login):
    context = ContextScope(name="Payments", author_id=login.id)
    component = Component(name="Ledger", context_scope=context)
    db.session.add_all([context, component])
    for category, worst in (("financial", "minor"), ("privacy", "major"), ("operational", "moderate")):
        db.session.add(
            Consequences(
                component=component,
                security_property="confidentiality",
                consequence_category=category,
                consequence_worstcase=worst,
                consequence_realisticcase="minor",
            )
        )
    db.session.commit()
    return context, component


def _consequence_section(body):
    start = body.index('id="section-consequences"')
    return body[start:body.index("</table>", start)]


def test_detail_page_groups_consequences_and_counts_groups(app, client, login):
    context, _component = _legacy_bia(login)

    body = client.get(f"/bia/item/{context.id}").data.decode()

    section = _consequence_section(body)
    assert section.count(">Confidentiality</span>") == 1
    for label in ("Financial", "Operational", "Privacy"):
        assert f">{label}</span>" in section
    assert 'data-impact="major"' in section
    assert "will be merged on edit" not in section
    # Component table count shows one CIA group, not three records.
    assert re.search(r'rounded-full px-2\.5 py-0\.5 bg-slate-500/15[^>]*>\s*1\s*<', body)


def test_components_list_counts_cia_groups(app, client, login):
    _context, component = _legacy_bia(login)

    response = client.get("/bia/components")

    assert response.status_code == 200
    link = re.search(
        rf'href="/bia/consequences/{component.id}"[^>]*>\s*(\d+)\s*</a>', response.get_data(as_text=True)
    )
    assert link and link.group(1) == "1"


def test_item_export_uses_grouped_consequences(app, client, login):
    context, _component = _legacy_bia(login)

    response = client.get(f"/bia/item/{context.id}/export")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert _consequence_section(body).count(">Confidentiality</span>") == 1
