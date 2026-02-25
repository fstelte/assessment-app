"""Shared Flask extension instances."""

from __future__ import annotations

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


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
