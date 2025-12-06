"""REST API endpoints for the risk management domain."""

from __future__ import annotations

import sqlalchemy as sa
from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required

from ...core.security import require_fresh_login
from ...extensions import db
from ..bia.models import Component
from ..identity.models import ROLE_ADMIN
from .models import Risk
from .services import (
    RiskValidationError,
    apply_payload_to_risk,
    load_thresholds,
    serialize_risk,
)

bp = Blueprint(
    "risk_api",
    __name__,
    url_prefix="/api/risks",
)


def register(app):
    """Register the risk API blueprint with the Flask app."""

    app.register_blueprint(bp)
    app.logger.info("Risk API module registered.")


def _require_admin() -> None:
    if not current_user.is_authenticated or not current_user.has_role(ROLE_ADMIN):
        abort(403)


def _risk_query():
    return Risk.query.options(
        sa.orm.selectinload(Risk.components).selectinload(Component.context_scope),
        sa.orm.selectinload(Risk.impact_area_links),
        sa.orm.selectinload(Risk.controls),
        sa.orm.selectinload(Risk.treatment_owner),
    )


@bp.route("", methods=["GET"])
@login_required
@require_fresh_login()
def list_risks():
    """Return all recorded risks with derived severity fields."""

    _require_admin()
    thresholds = load_thresholds()
    risks = _risk_query().order_by(Risk.created_at.desc()).all()
    return jsonify({"success": True, "data": [serialize_risk(risk, thresholds) for risk in risks]})


@bp.route("/<int:risk_id>", methods=["GET"])
@login_required
@require_fresh_login()
def get_risk(risk_id: int):
    """Return a single risk entry."""

    _require_admin()
    risk = _risk_query().filter(Risk.id == risk_id).first()
    if risk is None:
        abort(404)
    thresholds = load_thresholds()
    return jsonify({"success": True, "data": serialize_risk(risk, thresholds)})


@bp.route("", methods=["POST"])
@login_required
@require_fresh_login()
def create_risk():
    """Create a new risk entry from JSON payload."""

    _require_admin()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "errors": {"payload": ["JSON body is required."]}}), 400

    risk = Risk()
    try:
        apply_payload_to_risk(risk, payload)
    except RiskValidationError as exc:
        return jsonify({"success": False, "errors": exc.errors}), 400

    db.session.add(risk)
    db.session.commit()
    thresholds = load_thresholds()
    created = _risk_query().filter(Risk.id == risk.id).one()
    return jsonify({"success": True, "data": serialize_risk(created, thresholds)}), 201


@bp.route("/<int:risk_id>", methods=["PUT"])
@login_required
@require_fresh_login()
def update_risk(risk_id: int):
    """Update an existing risk entry."""

    _require_admin()
    risk = _risk_query().filter(Risk.id == risk_id).first()
    if risk is None:
        abort(404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "errors": {"payload": ["JSON body is required."]}}), 400

    try:
        apply_payload_to_risk(risk, payload)
    except RiskValidationError as exc:
        return jsonify({"success": False, "errors": exc.errors}), 400

    db.session.commit()
    thresholds = load_thresholds()
    refreshed = _risk_query().filter(Risk.id == risk.id).one()
    return jsonify({"success": True, "data": serialize_risk(refreshed, thresholds)})


@bp.route("/<int:risk_id>", methods=["DELETE"])
@login_required
@require_fresh_login()
def delete_risk(risk_id: int):
    """Delete a risk entry."""

    _require_admin()
    risk = db.session.get(Risk, risk_id)
    if risk is None:
        abort(404)
    db.session.delete(risk)
    db.session.commit()
    return jsonify({"success": True})
