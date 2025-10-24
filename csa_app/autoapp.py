import logging
import os
from pathlib import Path

from app import create_app


logging.basicConfig(level=os.getenv("APP_LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = create_app()
uri = app.config.get("SQLALCHEMY_DATABASE_URI", "<unset>")
instance_path = Path(app.instance_path).resolve() if app.instance_path else None
logger.info("Using SQLAlchemy database URI: %s", uri)
logger.info("Instance path resolved to: %s", instance_path)
