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

class Config:
    """Basisconfiguratie"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'een-zeer-geheim-wachtwoord'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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
