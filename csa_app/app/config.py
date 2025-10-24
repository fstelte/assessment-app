"""Configuration settings for the Flask application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Type

ROOT_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = Path(os.getenv("FLASK_INSTANCE_PATH", ROOT_DIR / "instance"))
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def _sqlite_uri(filename: str = "app.db") -> str:
    db_path = (INSTANCE_DIR / filename).resolve()
    return f"sqlite:///{db_path.as_posix()}"


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", _sqlite_uri())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_TIME_LIMIT = None

    TALISMAN_FORCE_HTTPS = False
    CONTENT_SECURITY_POLICY = {
        "default-src": ["'self'"],
        "style-src": ["'self'", "https://cdn.jsdelivr.net", "'unsafe-inline'"],
        "script-src": ["'self'", "https://cdn.jsdelivr.net"],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'", "https://cdn.jsdelivr.net"],
    }

    # MFA placeholders
    MFA_ISSUER_NAME = os.getenv("MFA_ISSUER_NAME", "Control Self Assessment")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV = "development"


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    ENV = "production"
    SESSION_COOKIE_SECURE = True
    TALISMAN_FORCE_HTTPS = True
    SECRET_KEY = os.getenv("SECRET_KEY")  # must be provided


CONFIG_BY_NAME: Dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
