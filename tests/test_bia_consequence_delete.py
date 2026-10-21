from __future__ import annotations

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.extensions import db


def _setup(author_id=None):
    context = ContextScope(name="Payments", author_id=author_id)
    component = Component(name="Ledger", context_scope=context)
    group = [
        Consequences(component=component, security_property=prop, consequence_category=category)
        for prop, category in (("confidentiality", "financial"), ("Confidentiality ", "privacy"), ("confidentiality", "operational"))
    ]
    other = Consequences(component=component, security_property="integrity", consequence_category="regulatory")
    db.session.add_all([context, component, *group, other])
    db.session.commit()
    return component, group, other


def _remaining(component):
    return [row.id for row in Consequences.query.filter_by(component_id=component.id).all()]


def test_json_delete_removes_whole_group(app, client, login):
    component, group, other = _setup(login.id)

    response = client.post(f"/bia/delete_consequence/{group[1].id}", json={})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert _remaining(component) == [other.id]


def test_form_delete_redirects_back_with_flash(app, client, login):
    component, group, other = _setup(login.id)

    response = client.post(
        f"/bia/delete_consequence/{group[0].id}",
        data={},
        headers={"Referer": "http://localhost/bia/consequences?filter=x"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/bia/consequences?filter=x"
    assert _remaining(component) == [other.id]
    with client.session_transaction() as sess:
        assert ("success", "Consequence deleted.") in sess["_flashes"]


def test_form_delete_ignores_foreign_referrer(app, client, login):
    _component, group, _other = _setup(login.id)

    response = client.post(
        f"/bia/delete_consequence/{group[0].id}",
        data={},
        headers={"Referer": "https://evil.example/phish"},
    )

    assert response.status_code == 302
    assert "evil.example" not in response.headers["Location"]


def test_delete_requires_edit_rights(app, client, login):
    component, group, _other = _setup(author_id=None)

    response = client.post(f"/bia/delete_consequence/{group[0].id}", json={})

    assert response.status_code == 403
    assert len(_remaining(component)) == 4
