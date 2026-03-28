"""Shared Flask extension instances."""

from __future__ import annotations

import redis as _redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from rq import Queue


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
)
server_session = Session()

task_queue: Queue | None = None


def get_redis() -> _redis.Redis:
    """Return a thread-safe Redis connection from the app config."""
    from flask import current_app

    url = current_app.config["REDIS_URL"]
    return _redis.Redis.from_url(url, decode_responses=True)


def init_task_queue(app) -> None:
    global task_queue
    redis_url = app.config.get("REDIS_URL")
    if redis_url:
        task_queue = Queue("scaffold-tasks", connection=_redis.Redis.from_url(redis_url))


login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def _load_user(user_id: str):
    from .apps.identity.models import User

    if not user_id:
        return None
    try:
        return User.query.get(int(user_id))
    except ValueError:
        return None
