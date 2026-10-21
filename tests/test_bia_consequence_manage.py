from __future__ import annotations

from werkzeug.datastructures import MultiDict

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.extensions import db


def _setup(login):
    context = ContextScope(name="Payments", author_id=login.id)
    ledger = Component(name="Ledger", context_scope=context)
    gateway = Component(name="Gateway", context_scope=context)
    db.session.add_all([context, ledger, gateway])
    db.session.commit()
    return context, ledger, gateway


def _legacy_group(component, prop="confidentiality"):
    rows = [
        Consequences(
            component=component,
            security_property=prop,
            consequence_category=category,
            consequence_worstcase=worst,
            consequence_realisticcase="minor",
            justification_worstcase=just,
        )
        for category, worst, just in (("financial", "minor", "Fines"), ("privacy", "major", "Data leak"), ("operational", "moderate", "Fines"))
    ]
    db.session.add_all(rows)
    db.session.commit()
    return rows


def _post(client, context, component, categories, prop="confidentiality", consequence_id="", group_ids="", query=""):
    data = MultiDict(
        [
            *[("consequence_category", category) for category in categories],
            ("component_id", str(component.id)),
            ("security_property", prop),
            ("consequence_worstcase", "major"),
            ("justification_worstcase", "Reviewed"),
            ("consequence_realisticcase", "moderate"),
            ("justification_realisticcase", ""),
            ("consequence_id", consequence_id),
            ("group_ids", group_ids),
        ]
    )
    return client.post(f"/bia/item/{context.id}/consequences{query}", data=data, follow_redirects=False)


def _rows(component):
    return Consequences.query.filter_by(component_id=component.id).order_by(Consequences.id).all()


def test_create_with_multiple_labels_stores_one_row(app, client, login):
    context, ledger, _gateway = _setup(login)

    response = _post(client, context, ledger, ["financial", "privacy"])

    assert response.status_code == 302
    (row,) = _rows(ledger)
    assert row.consequence_category == "financial,privacy"
    assert row.security_property == "confidentiality"


def test_create_for_existing_property_switches_to_edit(app, client, login):
    context, ledger, _gateway = _setup(login)
    legacy = _legacy_group(ledger)

    response = _post(client, context, ledger, ["regulatory"])

    assert response.status_code == 200
    body = response.data.decode()
    assert "already has a consequence for this security property" in body
    assert f'value="{",".join(str(row.id) for row in legacy)}"' in body
    assert 'selected value="regulatory"' in body
    assert len(_rows(ledger)) == 3


def test_edit_legacy_group_merges_into_one_row(app, client, login):
    context, ledger, _gateway = _setup(login)
    legacy = _legacy_group(ledger)
    ids = ",".join(str(row.id) for row in legacy)

    page = client.get(f"/bia/item/{context.id}/consequences?consequence_id={legacy[1].id}")
    body = page.data.decode()
    assert page.status_code == 200
    assert f'value="{ids}"' in body
    assert "Fines\n\nData leak" in body
    for category in ("financial", "operational", "privacy"):
        assert f'selected value="{category}"' in body

    response = _post(
        client, context, ledger, ["financial", "operational", "privacy"], consequence_id=str(legacy[0].id), group_ids=ids
    )

    assert response.status_code == 302
    (row,) = _rows(ledger)
    assert row.id == legacy[0].id
    assert row.consequence_category == "financial,operational,privacy"
    assert row.consequence_worstcase == "major"


def test_edit_with_stale_group_does_not_save(app, client, login):
    context, ledger, _gateway = _setup(login)
    legacy = _legacy_group(ledger)

    response = _post(
        client, context, ledger, ["financial"], consequence_id=str(legacy[0].id), group_ids=str(legacy[0].id)
    )

    assert response.status_code == 200
    assert "changed in the meantime" in response.data.decode()
    assert len(_rows(ledger)) == 3


def test_create_requires_a_label(app, client, login):
    context, ledger, _gateway = _setup(login)

    response = _post(client, context, ledger, [])

    assert response.status_code == 200
    assert _rows(ledger) == []


def test_retarget_onto_existing_group_is_rejected(app, client, login):
    context, ledger, gateway = _setup(login)
    (source,) = _legacy_group(ledger)[:1]
    db.session.add(Consequences(component=gateway, security_property="integrity", consequence_category="privacy"))
    db.session.commit()
    ids = ",".join(str(row.id) for row in _rows(ledger))

    response = _post(client, context, gateway, ["privacy"], prop="integrity", consequence_id=str(source.id), group_ids=ids)

    assert response.status_code == 200
    assert "The selected component already has a consequence" in response.data.decode()
    assert len(_rows(ledger)) == 3
    assert len(_rows(gateway)) == 1


def test_preselect_params_and_return_to(app, client, login):
    context, _ledger, gateway = _setup(login)

    page = client.get(
        f"/bia/item/{context.id}/consequences?component_id={gateway.id}&security_property=availability"
    )
    body = page.data.decode()
    assert f'selected value="{gateway.id}"' in body
    assert 'selected value="availability"' in body

    response = _post(client, context, gateway, ["operational"], prop="availability", query="?return_to=/bia/components")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/bia/components")


def test_list_shows_one_row_per_cia_group(app, client, login):
    context, ledger, _gateway = _setup(login)
    legacy = _legacy_group(ledger)
    db.session.add(Consequences(component=ledger, security_property="integrity", consequence_category="regulatory"))
    db.session.commit()

    body = client.get(f"/bia/item/{context.id}/consequences").data.decode()

    assert body.count(f'consequence_id={legacy[0].id}"') == 1
    for record in legacy[1:]:
        assert f'consequence_id={record.id}"' not in body
    assert "3 records, will be merged on edit" in body
    for label in ("Financial", "Operational", "Privacy", "Regulatory"):
        assert f">{label}</span>" in body


def test_delete_confirmation_names_the_consequence_and_group_size(app, client, login):
    context, ledger, _gateway = _setup(login)
    _legacy_group(ledger)
    db.session.add(Consequences(component=ledger, security_property="integrity", consequence_category="regulatory"))
    db.session.commit()

    body = client.get(f"/bia/item/{context.id}/consequences").data.decode()

    assert 'data-confirm="Delete this consequence? All 3 records for this property are removed.' in body
    assert 'data-confirm="Delete this consequence? This action cannot be undone."' in body
    assert "Delete this component?" not in body
