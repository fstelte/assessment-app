"""Bearer token authentication for SCIM endpoints."""

from __future__ import annotations

import hashlib
from datetime import datetime, UTC
from functools import wraps

from flask import abort, request

from ...extensions import db
from .models import SCIMToken


def require_scim_token(f):
    """Decorator that validates the SCIM bearer token on every request."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            abort(401)
        raw_token = auth_header[7:]
        if not raw_token:
            abort(401)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = SCIMToken.query.filter_by(
            token_hash=token_hash, is_active=True
        ).first()
        if not token:
            abort(401)
        token.last_used_at = datetime.now(UTC)
        db.session.commit()
        return f(*args, **kwargs)

    return decorated
