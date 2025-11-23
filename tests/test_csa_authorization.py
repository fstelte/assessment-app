from __future__ import annotations

from scaffold.apps.csa.models import Assessment, AssessmentAssignment, AssessmentTemplate, Control
from scaffold.apps.identity.models import (
    ROLE_ASSESSMENT_MANAGER,
    Role,
    User,
    ensure_default_roles,
)
from scaffold.extensions import db


def _ensure_template() -> None:
    control = Control()
    control.section = "1.1"
    control.domain = "Control A"
    control.description = "Example control"

    template = AssessmentTemplate()
    template.control = control
    template.name = "Template A"

    db.session.add(control)
    db.session.add(template)
    db.session.commit()


def _create_assessment_for_user(user: User) -> Assessment:
    template = AssessmentTemplate.query.first()
    assert template is not None

    assessment = Assessment()
    assessment.template = template
    assessment.created_by = user
    assessment.mark_started()

    assignment = AssessmentAssignment()
    assignment.assessment = assessment
    assignment.assignee = user
    assignment.assigned_by = user
    assignment.is_primary = True

    db.session.add_all([assessment, assignment])
    db.session.commit()
    return assessment


def test_regular_user_can_start_assessment(app, client, active_user, login):
    with app.app_context():
        ensure_default_roles()
        _ensure_template()

    response = client.get("/csa/assessments/start")
    assert response.status_code == 200
    assert b"Start Assessment" in response.data


def test_regular_user_cannot_assign_assessment(app, client, active_user, login):
    with app.app_context():
        ensure_default_roles()

    response = client.get("/csa/assessments/assign")
    assert response.status_code == 403


def test_manager_can_assign_assessment(app, client, active_user):
    with app.app_context():
        ensure_default_roles()
        manager_role = Role.query.filter_by(name=ROLE_ASSESSMENT_MANAGER).first()
        if manager_role is None:
            manager_role = Role()
            manager_role.name = ROLE_ASSESSMENT_MANAGER
            manager_role.description = "Assessment manager"
            db.session.add(manager_role)
            db.session.commit()

        user = User.find_by_email(active_user.email)
        assert user is not None
        if manager_role not in user.roles:
            user.roles.append(manager_role)

        _ensure_template()
        db.session.commit()

    login_response = client.post(
        "/auth/login",
        data={
            "email": active_user.email,
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.get("/csa/assessments/assign")
    assert response.status_code == 200
    assert b"Assign Assessment" in response.data


def test_manager_can_delete_assessment(app, client, active_user):
    with app.app_context():
        ensure_default_roles()
        _ensure_template()
        manager_role = Role.query.filter_by(name=ROLE_ASSESSMENT_MANAGER).first()
        if manager_role is None:
            manager_role = Role()
            manager_role.name = ROLE_ASSESSMENT_MANAGER
            manager_role.description = "Assessment manager"
            db.session.add(manager_role)
            db.session.commit()

        user = User.find_by_email(active_user.email)
        assert user is not None
        if manager_role not in user.roles:
            user.roles.append(manager_role)
            db.session.commit()

        assessment = _create_assessment_for_user(user)
        assessment_id = assessment.id

    login_response = client.post(
        "/auth/login",
        data={
            "email": active_user.email,
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.post(f"/csa/assessments/{assessment_id}/delete", follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        assert Assessment.query.get(assessment_id) is None


def test_regular_user_cannot_delete_assessment(app, client, active_user):
    with app.app_context():
        ensure_default_roles()
        _ensure_template()
        user = User.find_by_email(active_user.email)
        assert user is not None
        assessment = _create_assessment_for_user(user)
        assessment_id = assessment.id

    login_response = client.post(
        "/auth/login",
        data={
            "email": active_user.email,
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.post(f"/csa/assessments/{assessment_id}/delete")
    assert response.status_code == 403

    with app.app_context():
        assert Assessment.query.get(assessment_id) is not None
