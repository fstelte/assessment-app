import pytest
import fakeredis
import os

# Ensure FIELD_ENCRYPTION_KEYS is set for all tests.
# This is a test-only key — never use in production.
os.environ.setdefault(
    "FIELD_ENCRYPTION_KEYS",
    "t3xLB2zXmQvP8kRdNwJsYeHfCaGpUiOb4lV7hM1nDgA=",
)

from scaffold import create_app
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.apps.identity.models import Role, User, UserStatus


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Replace all Redis connections with an in-memory fake for every test."""
    server = fakeredis.FakeServer()
    fake = fakeredis.FakeRedis(server=server, decode_responses=True)
    monkeypatch.setattr("scaffold.extensions.get_redis", lambda: fake)
    return fake


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
            "scaffold.apps.dpia",
            "scaffold.apps.risk.api",
            "scaffold.apps.risk.routes",
            "scaffold.apps.template",
            "scaffold.apps.ssp",
        ],
        password_login_enabled=True,
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
