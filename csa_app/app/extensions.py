"""Central registry for Flask extensions."""

from __future__ import annotations

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect

# SQLAlchemy database instance shared across models
# The metadata and session will be accessed via this object.
db = SQLAlchemy()

# Flask-Migrate wires Alembic migrations to SQLAlchemy models.
migrate = Migrate()

# Flask-Login handles session management and authentication.
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_message_category = "warning"

# CSRFProtect integrates CSRF protection into Flask-WTF forms.
csrf = CSRFProtect()

# Talisman enforces security headers such as HSTS and CSP.
talisman = Talisman()


@login_manager.user_loader
def load_user(user_id: str):
	"""Resolve the logged-in user from the session."""
	if not user_id:
		return None
	from .models import User

	try:
		lookup_id = int(user_id)
	except (TypeError, ValueError):
		return None

	return db.session.get(User, lookup_id)
