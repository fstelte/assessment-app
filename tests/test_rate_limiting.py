"""Tests for rate limiting on authentication endpoints."""
import pytest
import fakeredis

from scaffold import create_app
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.apps.identity.models import User, UserStatus


@pytest.fixture
def rate_limit_app(monkeypatch):
    """App fixture with rate limiting enabled and fakeredis backend."""
    server = fakeredis.FakeServer()
    fake = fakeredis.FakeRedis(server=server, decode_responses=False)

    # Flask-Limiter needs a real-looking Redis URL; monkeypatch get_redis
    monkeypatch.setattr("scaffold.extensions.get_redis", lambda: fakeredis.FakeRedis(server=server, decode_responses=True))

    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        password_login_enabled=True,
        # Point limiter at a dummy URL; fakeredis intercepts actual use
        redis_url="redis://localhost:6379/0",
    )
    app = create_app(settings)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=True,
        RATELIMIT_STORAGE_URL="memory://",  # Use in-memory storage for limiter in tests
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def rl_client(rate_limit_app):
    return rate_limit_app.test_client()


@pytest.fixture
def existing_user(rate_limit_app):
    with rate_limit_app.app_context():
        user = User()
        user.email = "test@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        return user


def _post_login(client, email="wrong@example.com", password="bad"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_login_rate_limit_applied(rl_client, existing_user):
    """After 10 failed login attempts, the 11th should return 429."""
    for _ in range(10):
        resp = _post_login(rl_client)
        assert resp.status_code in (200, 302), f"Unexpected status on attempt: {resp.status_code}"

    eleventh = _post_login(rl_client)
    assert eleventh.status_code == 429


def test_login_success_not_blocked(rl_client, existing_user):
    """A single valid login attempt must not be rate-limited."""
    resp = _post_login(rl_client, email="test@example.com", password="Password123!")
    assert resp.status_code in (200, 302)
    assert resp.status_code != 429
