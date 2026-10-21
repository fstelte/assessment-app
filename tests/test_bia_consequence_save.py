from __future__ import annotations

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.apps.bia.utils import save_cia_consequence
from scaffold.extensions import db


def _component():
    context = ContextScope(name="Payments")
    component = Component(name="Ledger", context_scope=context)
    db.session.add_all([context, component])
    db.session.commit()
    return component


def test_creates_one_row_with_joined_labels(app):
    component = _component()

    saved = save_cia_consequence(
        component, "confidentiality", ["financial", "privacy"], "major", "Fines", "moderate", "Likely", replace_ids=[]
    )
    db.session.commit()

    rows = Consequences.query.filter_by(component_id=component.id).all()
    assert rows == [saved]
    assert saved.consequence_category == "financial,privacy"
    assert saved.get_categories() == ["financial", "privacy"]
    assert saved.consequence_worstcase == "major"
    assert saved.justification_realisticcase == "Likely"


def test_replaces_group_keeping_lowest_id(app):
    component = _component()
    legacy = [
        Consequences(component=component, security_property="confidentiality", consequence_category=category)
        for category in ("financial", "operational", "privacy")
    ]
    other = Consequences(component=component, security_property="integrity", consequence_category="regulatory")
    db.session.add_all([*legacy, other])
    db.session.commit()
    ids = [row.id for row in legacy]

    saved = save_cia_consequence(
        component,
        "confidentiality",
        ["financial", "operational", "privacy"],
        "catastrophic",
        "Merged",
        "major",
        None,
        replace_ids=list(reversed(ids)),
    )
    db.session.commit()

    assert saved.id == min(ids)
    remaining = Consequences.query.filter_by(component_id=component.id).order_by(Consequences.id).all()
    assert [row.id for row in remaining] == [min(ids), other.id]
    assert saved.consequence_category == "financial,operational,privacy"
    assert saved.consequence_worstcase == "catastrophic"
    assert other.consequence_category == "regulatory"
