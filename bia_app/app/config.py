# app/config.py
# Configuratie-instellingen voor de applicatie.

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Laad variabelen vanuit de root .env zodat alle apps dezelfde configuratie delen
ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if ROOT_ENV_PATH.exists():
    load_dotenv(ROOT_ENV_PATH, override=False)

# Laat eventuele project-specifieke overrides uit het lokale pad ook gelden
load_dotenv()

# Bepaal de basisdirectory van het project
basedir = os.path.abspath(os.path.dirname(__file__))


def _get_value(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    if value:
        return value.strip()
    return default


def _get_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_password_login_enabled(default: bool = False) -> bool:
    for key in (
        "PASSWORD_LOGIN_ENABLED",
        "SAML_PASSWORD_LOGIN_ENABLED",
        "ENTRA_PASSWORD_LOGIN_ENABLED",
        "AZURE_PASSWORD_LOGIN_ENABLED",
    ):
        value = os.environ.get(key)
        if value is not None:
            return value.strip().lower() in {"1", "true", "yes", "on"}
    return default

class Config:
    """Basisconfiguratie"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'een-zeer-geheim-wachtwoord'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SAML integration
    SAML_SP_ENTITY_ID = _get_value('SAML_SP_ENTITY_ID')
    SAML_SP_ACS_URL = _get_value('SAML_SP_ACS_URL')
    SAML_SP_SLS_URL = _get_value('SAML_SP_SLS_URL')
    SAML_SP_CERT = _get_value('SAML_SP_CERT')
    SAML_SP_PRIVATE_KEY = _get_value('SAML_SP_PRIVATE_KEY')
    SAML_IDP_ENTITY_ID = _get_value('SAML_IDP_ENTITY_ID')
    SAML_IDP_SSO_URL = _get_value('SAML_IDP_SSO_URL')
    SAML_IDP_SLO_URL = _get_value('SAML_IDP_SLO_URL')
    SAML_IDP_CERT = _get_value('SAML_IDP_CERT')
    SAML_NAMEID_FORMAT = _get_value('SAML_NAMEID_FORMAT', 'urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified')
    SAML_SIGN_AUTHN_REQUESTS = _get_bool('SAML_SIGN_AUTHN_REQUESTS')
    SAML_SIGN_LOGOUT_REQUESTS = _get_bool('SAML_SIGN_LOGOUT_REQUESTS')
    SAML_SIGN_LOGOUT_RESPONSES = _get_bool('SAML_SIGN_LOGOUT_RESPONSES')
    SAML_WANT_MESSAGE_SIGNED = _get_bool('SAML_WANT_MESSAGE_SIGNED')
    SAML_WANT_ASSERTION_SIGNED = _get_bool('SAML_WANT_ASSERTION_SIGNED', default=True)
    SAML_ALLOWED_GROUP_IDS = _get_value('SAML_ALLOWED_GROUP_IDS')
    SAML_ALLOWED_GROUP_IDS_LIST = [gid.strip() for gid in SAML_ALLOWED_GROUP_IDS.split(',') if gid.strip()]
    SAML_ROLE_MAP = _get_value('SAML_ROLE_MAP')
    SAML_ATTRIBUTE_GROUPS = _get_value('SAML_ATTRIBUTE_GROUPS', 'http://schemas.microsoft.com/identity/claims/groups')
    SAML_ATTRIBUTE_EMAIL = _get_value('SAML_ATTRIBUTE_EMAIL', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress')
    SAML_ATTRIBUTE_FIRST_NAME = _get_value('SAML_ATTRIBUTE_FIRST_NAME', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname')
    SAML_ATTRIBUTE_LAST_NAME = _get_value('SAML_ATTRIBUTE_LAST_NAME', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname')
    SAML_ATTRIBUTE_DISPLAY_NAME = _get_value('SAML_ATTRIBUTE_DISPLAY_NAME', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name')
    SAML_ATTRIBUTE_OBJECT_ID = _get_value('SAML_ATTRIBUTE_OBJECT_ID', 'http://schemas.microsoft.com/identity/claims/objectidentifier')
    SAML_ATTRIBUTE_UPN = _get_value('SAML_ATTRIBUTE_UPN', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn')
    SAML_STRICT = _get_bool('SAML_STRICT', default=True)
    SAML_DEBUG = _get_bool('SAML_DEBUG')
    PASSWORD_LOGIN_ENABLED = _get_password_login_enabled()

    # Session Security Configuration (OWASP recommendations)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)  # 12-hour session timeout
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent XSS attacks
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    REMEMBER_COOKIE_SECURE = True  # Secure remember me cookies
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(hours=12)  # Also limit remember me duration
    
    # Additional security headers
    WTF_CSRF_TIME_LIMIT = None  # Let session timeout handle this

class SQLiteConfig(Config):
    # Configureer de SQLite database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'instance', 'bia_tool.db')

# Als er een complete DATABASE_URL is opgegeven, gebruik die rechtstreeks
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    class EnvironmentConfig(Config):
        SQLALCHEMY_DATABASE_URI = DATABASE_URL

    DefaultConfig = EnvironmentConfig
    print("Using database configuration: EnvironmentConfig")
else:
    DefaultConfig = SQLiteConfig
    print("Using database configuration: SQLiteConfig")

CONFIG_BY_NAME = {
    'default': DefaultConfig,
    'production': DefaultConfig,
    'sqlite': SQLiteConfig,
    'development': SQLiteConfig,
}
