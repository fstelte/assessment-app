"""Response hardening borrowed from the legacy BIA deployment."""

from __future__ import annotations

from base64 import b64encode
from os import urandom

from flask import Flask, g


def _ensure_csp_nonce() -> str:
    nonce = getattr(g, "csp_nonce", None)
    if nonce is None:
        nonce = b64encode(urandom(16)).decode("ascii")
        g.csp_nonce = nonce
    return nonce


def init_security_headers(app: Flask) -> None:
    """Attach secure HTTP headers after every response."""

    @app.before_request
    def _prepare_nonce() -> None:
        _ensure_csp_nonce()

    @app.after_request
    def _apply_headers(response):  # type: ignore[override]
        nonce = _ensure_csp_nonce()
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        script_sources = " ".join(("'self'", "https://cdn.jsdelivr.net", f"'nonce-{nonce}'"))
        # Allow inline style elements from trusted sources and nonce-protected inline styles.
        # Note: adding 'unsafe-inline' for style elements relaxes CSP for styles; consider
        # replacing this with a library-specific fix (injecting nonce into created <style>
        # tags) for stronger security if you can.
        style_sources = " ".join(("'self'", "https://cdn.jsdelivr.net", f"'nonce-{nonce}'", "'unsafe-inline'"))
        policy = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            f"script-src {script_sources}; "
            f"style-src {style_sources}; "
            f"style-src-elem {style_sources}; "
            "style-src-attr 'unsafe-inline'; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )

        response.headers["Content-Security-Policy"] = policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
