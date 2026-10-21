from __future__ import annotations

import re

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.extensions import db


def _component(context, name, *props):
    component = Component(name=name, context_scope=context)
    db.session.add(component)
    for prop in props:
        db.session.add(Consequences(component=component, security_property=prop, consequence_category="privacy"))
    return component


def _delete_ids(body):
    return re.findall(r"/bia/delete_consequence/(\d+)", body)


def test_all_consequences_shows_one_row_per_cia_group(app, client, login):
    context = ContextScope(name="Payments", author_id=login.id)
    db.session.add(context)
    ledger = _component(context, "Ledger", "confidentiality", "confidentiality", "confidentiality", "integrity")
    db.session.commit()
    first_c = min(c.id for c in ledger.consequences if c.security_property == "confidentiality")

    body = client.get("/bia/consequences").data.decode()

    ids = _delete_ids(body)
    assert len(ids) == 2
    assert str(first_c) in ids
    assert ">Confidentiality</span>" in body and ">Integrity</span>" in body
    assert ">Privacy</span>" in body


def test_all_consequences_paginates_by_component(app, client, login):
    app.config["BIA_COMPONENTS_PER_PAGE"] = 2
    context = ContextScope(name="Payments", author_id=login.id)
    db.session.add(context)
    _component(context, "Alpha", "confidentiality", "integrity", "availability")
    _component(context, "Bravo", "confidentiality", "confidentiality")
    _component(context, "Charlie", "integrity")
    _component(context, "Delta")  # no consequences: not listed
    db.session.commit()

    first = client.get("/bia/consequences?page=1").data.decode()
    second = client.get("/bia/consequences?page=2").data.decode()

    # Page 1: Alpha (3 groups) + Bravo (1 group); a component is never split.
    assert len(_delete_ids(first)) == 4
    assert "Charlie" not in first
    assert len(_delete_ids(second)) == 1
    assert "Charlie" in second
    assert "Delta" not in first + second
    assert re.search(r">\s*3\s+components\s*<", first)
