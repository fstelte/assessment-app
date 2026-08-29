from scaffold.apps.bia.models import ContextScope
from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.apps.ssp.models import ADRRecord, ADRStatus, ArchitecturePrinciple, SSPlan
from scaffold.extensions import db


def _make_user(app, email="author@example.com"):
    with app.app_context():
        user = User()
        user.email = email
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()


def _make_admin(app, email="admin@example.com"):
    with app.app_context():
        role = Role.query.filter_by(name="admin").first()
        if role is None:
            role = Role()
            role.name = "admin"
            db.session.add(role)
        admin = User()
        admin.email = email
        admin.status = UserStatus.ACTIVE
        admin.set_password("Password123!")
        admin.roles.append(role)
        db.session.add(admin)
        db.session.commit()


def _login(client, email="author@example.com", password="Password123!"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def _make_ssp(app):
    with app.app_context():
        scope = ContextScope(name="Test Scope")
        db.session.add(scope)
        db.session.flush()
        ssp = SSPlan(context_scope_id=scope.id)
        db.session.add(ssp)
        db.session.commit()
        return ssp.id


def _make_principle(app, name="Principle"):
    with app.app_context():
        principle = ArchitecturePrinciple(name=name, description="x")
        db.session.add(principle)
        db.session.commit()
        return principle.id


def test_adr_requires_primary_principle(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _make_principle(app)

    response = client.post(
        f"/ssp/{ssp_id}/adrs/add",
        data={"title": "Use managed DB", "status": "proposed", "context": "ctx", "decision": "dec"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert ADRRecord.query.count() == 0


def test_adr_creation_persists_secondary_principles(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    primary_id = _make_principle(app, "Primary Principle")
    secondary_id = _make_principle(app, "Secondary Principle")

    response = client.post(
        f"/ssp/{ssp_id}/adrs/add",
        data={
            "title": "Use managed DB",
            "primary_principle_id": str(primary_id),
            "secondary_principle_ids": [str(secondary_id)],
            "status": "proposed",
            "context": "ctx",
            "decision": "dec",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        adr = ADRRecord.query.filter_by(title="Use managed DB").first()
        assert adr is not None
        assert adr.primary_principle_id == primary_id
        assert [p.id for p in adr.secondary_principles] == [secondary_id]


def test_invalid_status_transition_rejected(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    principle_id = _make_principle(app)

    with app.app_context():
        adr = ADRRecord(
            ssp_id=ssp_id,
            title="Original decision",
            status=ADRStatus.REJECTED,
            context="ctx",
            decision="dec",
            primary_principle_id=principle_id,
        )
        db.session.add(adr)
        db.session.commit()
        adr_id = adr.id

    response = client.post(
        f"/ssp/{ssp_id}/adrs/{adr_id}/edit",
        data={
            "adr_id": str(adr_id),
            "title": "Original decision",
            "status": "accepted",  # Rejected -> Accepted is not an allowed transition
            "context": "ctx",
            "decision": "dec",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(ADRRecord, adr_id).status == ADRStatus.REJECTED


def test_supersede_flips_prior_status_and_links_resolve_both_ways(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    principle_id = _make_principle(app)

    with app.app_context():
        old_adr = ADRRecord(
            ssp_id=ssp_id,
            title="Old decision",
            status=ADRStatus.ACCEPTED,
            context="ctx",
            decision="dec",
            primary_principle_id=principle_id,
        )
        db.session.add(old_adr)
        db.session.commit()
        old_adr_id = old_adr.id

    response = client.post(
        f"/ssp/{ssp_id}/adrs/add",
        data={
            "title": "New decision",
            "primary_principle_id": str(principle_id),
            "status": "accepted",
            "context": "ctx",
            "decision": "dec",
            "supersedes_id": str(old_adr_id),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        old_adr = db.session.get(ADRRecord, old_adr_id)
        new_adr = ADRRecord.query.filter_by(title="New decision").first()
        assert old_adr.status == ADRStatus.SUPERSEDED
        assert new_adr is not None
        assert old_adr.superseded_by.id == new_adr.id
        assert new_adr.supersedes.id == old_adr.id


def test_double_supersede_rejected(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    principle_id = _make_principle(app)

    with app.app_context():
        old_adr = ADRRecord(
            ssp_id=ssp_id,
            title="Old",
            status=ADRStatus.ACCEPTED,
            context="ctx",
            decision="dec",
            primary_principle_id=principle_id,
        )
        db.session.add(old_adr)
        db.session.commit()
        old_id = old_adr.id

    client.post(
        f"/ssp/{ssp_id}/adrs/add",
        data={
            "title": "First supersede",
            "primary_principle_id": str(principle_id),
            "status": "accepted",
            "context": "ctx",
            "decision": "dec",
            "supersedes_id": str(old_id),
        },
        follow_redirects=True,
    )

    response = client.post(
        f"/ssp/{ssp_id}/adrs/add",
        data={
            "title": "Second supersede",
            "primary_principle_id": str(principle_id),
            "status": "accepted",
            "context": "ctx",
            "decision": "dec",
            "supersedes_id": str(old_id),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert ADRRecord.query.filter_by(title="Second supersede").count() == 0


def test_cross_ssp_supersede_rejected(app, client):
    _make_user(app)
    _login(client)
    ssp_a_id = _make_ssp(app)
    ssp_b_id = _make_ssp(app)
    principle_id = _make_principle(app)

    with app.app_context():
        adr_in_a = ADRRecord(
            ssp_id=ssp_a_id,
            title="ADR in SSP A",
            status=ADRStatus.ACCEPTED,
            context="ctx",
            decision="dec",
            primary_principle_id=principle_id,
        )
        db.session.add(adr_in_a)
        db.session.commit()
        adr_a_id = adr_in_a.id

    response = client.post(
        f"/ssp/{ssp_b_id}/adrs/add",
        data={
            "title": "Cross-SSP supersede attempt",
            "primary_principle_id": str(principle_id),
            "status": "accepted",
            "context": "ctx",
            "decision": "dec",
            "supersedes_id": str(adr_a_id),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert ADRRecord.query.filter_by(title="Cross-SSP supersede attempt").count() == 0
        assert db.session.get(ADRRecord, adr_a_id).status == ADRStatus.ACCEPTED


def test_principle_delete_allowed_after_referencing_adr_removed(app, client):
    _make_admin(app)
    ssp_id = _make_ssp(app)
    principle_id = _make_principle(app)

    with app.app_context():
        adr = ADRRecord(
            ssp_id=ssp_id,
            title="Blocks delete",
            status=ADRStatus.PROPOSED,
            context="ctx",
            decision="dec",
            primary_principle_id=principle_id,
        )
        db.session.add(adr)
        db.session.commit()
        adr_id = adr.id

    _login(client, email="admin@example.com")

    response = client.post(
        f"/admin/principles/{principle_id}/delete",
        data={f"delete-{principle_id}-principle_id": str(principle_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(ArchitecturePrinciple, principle_id) is not None

    with app.app_context():
        db.session.delete(db.session.get(ADRRecord, adr_id))
        db.session.commit()

    response = client.post(
        f"/admin/principles/{principle_id}/delete",
        data={f"delete-{principle_id}-principle_id": str(principle_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(ArchitecturePrinciple, principle_id) is None
