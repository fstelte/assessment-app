"""Response hardening borrowed from the legacy BIA deployment."""

from __future__ import annotations

from flask import Flask


def init_security_headers(app: Flask) -> None:
    """Attach secure HTTP headers after every response.

    The configuration mirrors the original `bia_app` behaviour: clickjacking
    protection, MIME sniffing prevention, basic CSP, and conditional HSTS when
    secure cookies are enabled. The function is side-effect free and intended
    to be called once during application initialisation.
    """

    @app.after_request
    def _apply_headers(response):  # type: ignore[override]
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")

        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'",
        )
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response
