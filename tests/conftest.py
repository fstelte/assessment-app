import pytest

from scaffold import create_app
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.apps.identity.models import Role, User, UserStatus


@pytest.fixture
def app():
    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        session_cookie_httponly=True,
        session_cookie_samesite="Lax",
        app_modules=[
            "scaffold.apps.auth.routes",
            "scaffold.apps.admin",
            "scaffold.apps.bia",
            "scaffold.apps.csa",
            "scaffold.apps.template",
        ],
    )
    app = create_app(settings)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def active_user(app):
    with app.app_context():
        user = User()
        user.email = "user@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def login(client, active_user):
    response = client.post(
        "/auth/login",
        data={
            "email": active_user.email,
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    return response
