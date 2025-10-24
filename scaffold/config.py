"""Application settings and environment helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

_DEFAULT_MODULES = [
    "scaffold.apps.auth.routes",
    "scaffold.apps.admin",
    "scaffold.apps.bia",
    "scaffold.apps.csa",
    "scaffold.apps.template",
]


@dataclass(slots=True)
class Settings:
    """Simple settings container fed by environment variables."""

    secret_key: str = "change-me"
    database_url: str = "sqlite:///instance/scaffold.db"
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "Lax"
    app_modules: List[str] = field(default_factory=lambda: list(_DEFAULT_MODULES))

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        modules = os.getenv("SCAFFOLD_APP_MODULES") or ""
        module_list = [m.strip() for m in modules.split(",") if m.strip()] or list(_DEFAULT_MODULES)
        return cls(
            secret_key=os.getenv("SECRET_KEY", defaults.secret_key),
            database_url=os.getenv("DATABASE_URL", defaults.database_url),
            session_cookie_secure=_as_bool(os.getenv("SESSION_COOKIE_SECURE", "true")),
            session_cookie_httponly=_as_bool(os.getenv("SESSION_COOKIE_HTTPONLY", "true")),
            session_cookie_samesite=os.getenv("SESSION_COOKIE_SAMESITE", defaults.session_cookie_samesite),
            app_modules=module_list,
        )

    def flask_config(self) -> dict[str, object]:
        """Return the Flask configuration dictionary."""

        return {
            "SECRET_KEY": self.secret_key,
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SESSION_COOKIE_SECURE": self.session_cookie_secure,
            "SESSION_COOKIE_HTTPONLY": self.session_cookie_httponly,
            "SESSION_COOKIE_SAMESITE": self.session_cookie_samesite,
        }


def _as_bool(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}
