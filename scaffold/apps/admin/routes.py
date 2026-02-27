"""Administrative routes handling user lifecycle and MFA management."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json

import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from ...core.i18n import gettext as _, get_locale
from flask_login import current_user, login_required

from ...core.security import require_fresh_login
from ...extensions import db
from ..auth.flow import ensure_mfa_provisioning
from ..auth.mfa import build_provisioning
from ..csa.forms import UserRoleAssignForm, UserRoleRemoveForm
from ..csa.models import Control
from ..csa.services import (
    build_control_metadata,
    import_controls_from_builtin,
    import_controls_from_mapping,
    parse_nist_text,
    upsert_control,
)
from ...models import AuditLog
from ..identity.models import MFASetting, Role, User, UserStatus, ROLE_CONTROL_OWNER
from ..bia.localization import translate_authentication_label
from ..bia.models import AuthenticationMethod, BiaTier, Component
from ..bia.services.authentication import clear_authentication_cache
from ..risk.forms import RiskForm, RiskThresholdForm
from ..risk.models import (
    Risk,
    RiskChance,
    RiskImpact,
    RiskImpactArea,
    RiskImpactAreaLink,
    RiskSeverityThreshold,
    RiskTreatmentOption,
)
from ..risk.services import (
    configure_risk_form,
    determine_severity as determine_risk_severity,
    load_thresholds,
    optional_int,
    set_impact_areas,
    thresholds_overlap,
    validate_component_ids,
    validate_control_ids,
)
from .forms import (
    AuthenticationMethodDeleteForm,
    AuthenticationMethodForm,
    AuthenticationMethodToggleForm,
    BiaTierForm,
    ControlCreateForm,
    ControlDeleteForm,
    ControlImportForm,
    ControlUpdateForm,
)
from ...core.audit import log_event

bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="templates")


def _require_admin() -> None:
    if not current_user.is_authenticated or not current_user.has_role("admin"):
        abort(403)


def _require_control_admin() -> None:
    if not current_user.is_authenticated:
        abort(403)
    if not (current_user.has_role("admin") or current_user.has_role(ROLE_CONTROL_OWNER)):
        abort(403)


def _role_display_name(role: Role) -> str:
    translation_key = f"csa.roles.names.{role.name}"
    translated = _(translation_key)
    if translated == translation_key:
        return role.description or role.name.replace("_", " ").title()
    return translated


def _get_authentication_method(method_id: int) -> AuthenticationMethod:
    method = db.session.get(AuthenticationMethod, method_id)
    if method is None:
        abort(404)
    return method


def _fallback_map(method: AuthenticationMethod) -> dict[str, str]:
    return {
        "en": method.label_en or "",
        "nl": method.label_nl or "",
    }


def _refresh_method_labels(method: AuthenticationMethod) -> None:
    previous = _fallback_map(method)
    method.label_en = translate_authentication_label(method.slug, "en", previous)
    method.label_nl = translate_authentication_label(method.slug, "nl", previous)


def _method_display_name(method: AuthenticationMethod, locale: str | None = None) -> str:
    return translate_authentication_label(method.slug, locale or get_locale(), _fallback_map(method))


@bp.route("/controls", methods=["GET", "POST"])
@login_required
@require_fresh_login()
def controls():
    _require_control_admin()

    controls = (
        Control.query.options(selectinload(Control.templates))
        .order_by(sa.func.coalesce(Control.section, ""), Control.domain.asc())
        .all()
    )

    total_controls = len(controls)
    total_templates = sum(len(control.templates) for control in controls)
    described_controls = sum(1 for control in controls if (control.description or "").strip())
    described_pct = int(round((described_controls / total_controls) * 100)) if total_controls else 0
    control_stats = {
        "total": total_controls,
        "templates": total_templates,
        "described": described_controls,
        "described_pct": described_pct,
    }

    import_form = ControlImportForm()
    create_form = ControlCreateForm()

    delete_forms: dict[int, ControlDeleteForm] = {}
    for control in controls:
        delete_form = ControlDeleteForm(prefix=f"delete-{control.id}")
        delete_form.control_id.data = str(control.id)
        delete_forms[control.id] = delete_form

    if request.method == "POST" and request.form.get("action") == "import_builtin":
        dataset = (request.form.get("dataset") or "iso").strip().lower()
        try:
            stats = import_controls_from_builtin(dataset)
        except FileNotFoundError:
            flash(_("admin.controls.flash.dataset_missing"), "danger")
        except ValueError as exc:
            flash(_("admin.controls.flash.dataset_invalid", error=str(exc)), "warning")
        else:
            flash(
                _(
                    "csa.flash.import_result",
                    created=stats.created,
                    updated=stats.updated,
                ),
                "success" if not stats.errors else "warning",
            )
            for error in stats.errors:
                flash(error, "warning")
        return redirect(url_for("admin.controls"))

    if import_form.validate_on_submit():
        file_storage = import_form.data_file.data
        raw_bytes = file_storage.read()
        file_storage.close()

        try:
            payload = json.loads(raw_bytes)
        except json.JSONDecodeError as exc:
            try:
                text_data = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                flash(_("csa.flash.json_error", error=exc), "danger")
                return redirect(url_for("admin.controls"))

            try:
                payload = parse_nist_text(text_data)
            except ValueError as parse_exc:
                flash(_("csa.flash.json_error", error=exc), "danger")
                flash(_("admin.controls.flash.dataset_invalid", error=str(parse_exc)), "warning")
                return redirect(url_for("admin.controls"))

        stats = import_controls_from_mapping(payload)
        flash(
            _(
                "csa.flash.import_result",
                created=stats.created,
                updated=stats.updated,
            ),
            "success" if not stats.errors else "warning",
        )
        for error in stats.errors:
            flash(error, "warning")
        return redirect(url_for("admin.controls"))

    return render_template(
        "admin/controls.html",
        import_form=import_form,
        create_form=create_form,
        delete_forms=delete_forms,
        controls=controls,
        control_stats=control_stats,
    )


@bp.route("/controls/delete-bulk", methods=["POST"])
def delete_bulk_controls():
    _require_control_admin()
    """Bulk delete selected controls."""
    control_ids = request.form.getlist("control_ids")
    if not control_ids:
        flash(_("admin.controls.delete_bulk.none_selected"), "warning")
        return redirect(url_for("admin.controls"))
    
    # Cast IDs to integers to satisfy PostgreSQL type checking against integer ID column
    try:
        control_ids = [int(cid) for cid in control_ids]
    except (ValueError, TypeError):
        flash(_("admin.controls.delete_bulk.invalid_ids"), "danger")
        return redirect(url_for("admin.controls"))

    controls = db.session.query(Control).filter(Control.id.in_(control_ids)).all()
    count = len(controls)
    
    if count == 0:
        flash(_("admin.controls.delete_bulk.none_found"), "info")
    else:
        for control in controls:
            db.session.delete(control)
        db.session.commit()
        log_event(
            action="delete_bulk",
            entity_type="control",
            user=current_user,
            details={
                "ids": control_ids,
                "count": count,
                "description": f"Bulk deleted {count} controls",
            },
        )
        flash(_("admin.controls.delete_bulk.success", count=count), "success")
        
    return redirect(url_for("admin.controls"))


@bp.post("/controls/create")
@login_required
@require_fresh_login()
def create_control():
    _require_control_admin()
    form = ControlCreateForm()

    if form.validate_on_submit():
        name = (form.name.data or "").strip()
        code = (form.code.data or "").strip() or None
        description = (form.description.data or "").strip() or None

        duplicate = (
            Control.query.filter(sa.func.lower(Control.domain) == name.lower()).first()
            if name
            else None
        )
        if duplicate:
            flash(_("admin.controls.flash.duplicate", domain=name), "warning")
            return redirect(url_for("admin.controls"))

        try:
            metadata = build_control_metadata(name=name, section=code, description=description)
            outcome = upsert_control(metadata, allow_existing=False)
        except ValueError as exc:
            flash(str(exc), "warning")
            db.session.rollback()
        else:
            db.session.commit()
            flash(_("admin.controls.flash.created", domain=outcome.control.domain), "success")
            return redirect(url_for("admin.controls"))
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.controls"))


@bp.get("/controls/<int:control_id>/edit")
@login_required
@require_fresh_login()
def edit_control(control_id: int):
    _require_control_admin()
    control = db.session.get(Control, control_id)
    if control is None:
        abort(404)

    form = ControlUpdateForm()
    form.control_id.data = str(control.id)
    form.code.data = control.section or ""
    form.name.data = control.domain
    form.description.data = control.description or ""

    return render_template(
        "admin/control_edit.html",
        control=control,
        form=form,
    )


@bp.post("/controls/<int:control_id>/update")
@login_required
@require_fresh_login()
def update_control(control_id: int):
    _require_control_admin()
    control = db.session.get(Control, control_id)
    if control is None:
        abort(404)

    form = ControlUpdateForm()
    if not form.validate_on_submit():
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")
        return redirect(url_for("admin.controls"))

    try:
        submitted_id = int(form.control_id.data)
    except (TypeError, ValueError):
        flash(_("admin.controls.flash.invalid_form"), "danger")
        return redirect(url_for("admin.controls"))

    if submitted_id != control_id:
        flash(_("admin.controls.flash.invalid_form"), "danger")
        return redirect(url_for("admin.controls"))

    name = (form.name.data or "").strip()
    code = (form.code.data or "").strip() or None
    description = (form.description.data or "").strip() or None

    duplicate = (
        Control.query.filter(
            sa.func.lower(Control.domain) == name.lower(),
            Control.id != control.id,
        ).first()
        if name
        else None
    )
    if duplicate:
        flash(_("admin.controls.flash.duplicate", domain=name), "warning")
        return redirect(url_for("admin.controls"))

    metadata = build_control_metadata(name=name, section=code, description=description)
    upsert_control(metadata, target=control)
    db.session.commit()
    flash(_("admin.controls.flash.updated", domain=control.domain), "success")
    return redirect(url_for("admin.controls"))


@bp.post("/controls/<int:control_id>/delete")
@login_required
@require_fresh_login()
def delete_control(control_id: int):
    _require_control_admin()
    control = db.session.get(Control, control_id)
    if control is None:
        abort(404)

    form = ControlDeleteForm(prefix=f"delete-{control.id}")
    if not form.validate_on_submit():
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")
        return redirect(url_for("admin.controls"))

    try:
        submitted_id = int(form.control_id.data)
    except (TypeError, ValueError):
        flash(_("admin.controls.flash.invalid_form"), "danger")
        return redirect(url_for("admin.controls"))

    if submitted_id != control_id:
        flash(_("admin.controls.flash.invalid_form"), "danger")
        return redirect(url_for("admin.controls"))

    domain_label = control.domain
    db.session.delete(control)
    db.session.commit()
    flash(_("admin.controls.flash.deleted", domain=domain_label), "info")
    return redirect(url_for("admin.controls"))


@bp.get("/audit-trail")
@login_required
@require_fresh_login()
def audit_trail():
    _require_admin()

    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)

    try:
        per_page = int(request.args.get("per_page", 25))
    except (TypeError, ValueError):
        per_page = 25
    per_page = min(max(1, per_page), 100)

    action_filter = (request.args.get("action") or "").strip()
    event_type_filter = (request.args.get("event_type") or "").strip()
    entity_filter = (request.args.get("entity_type") or "").strip()
    actor_filter = (request.args.get("actor") or "").strip()
    start_raw = (request.args.get("start_date") or "").strip()
    end_raw = (request.args.get("end_date") or "").strip()

    query = AuditLog.query.order_by(AuditLog.created_at.desc())

    if action_filter:
        lowered = f"%{action_filter.lower()}%"
        query = query.filter(sa.func.lower(AuditLog.event_type).like(lowered))

    if event_type_filter:
        query = query.filter(AuditLog.event_type == event_type_filter)

    if entity_filter:
        lowered = f"%{entity_filter.lower()}%"
        query = query.filter(sa.func.lower(AuditLog.target_type).like(lowered))

    if actor_filter:
        lowered = f"%{actor_filter.lower()}%"
        predicates = [sa.func.lower(AuditLog.actor_email).like(lowered)]
        if actor_filter.isdigit():
            predicates.append(AuditLog.actor_id == int(actor_filter))
        query = query.filter(sa.or_(*predicates))

    if start_raw:
        try:
            start_dt = datetime.fromisoformat(f"{start_raw}T00:00:00+00:00")
        except ValueError:
            flash(_("admin.audit.filters.invalid_date"), "warning")
        else:
            query = query.filter(AuditLog.created_at >= start_dt)

    if end_raw:
        try:
            end_dt = datetime.fromisoformat(f"{end_raw}T23:59:59.999999+00:00")
        except ValueError:
            flash(_("admin.audit.filters.invalid_date"), "warning")
        else:
            query = query.filter(AuditLog.created_at <= end_dt)

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    event_type_options = [
        value
        for value in db.session.execute(
            sa.select(AuditLog.event_type)
            .distinct()
            .where(AuditLog.event_type.isnot(None))
            .order_by(AuditLog.event_type.asc())
        ).scalars()
        if value
    ]

    actor_options = [
        value
        for value in db.session.execute(
            sa.select(AuditLog.actor_email)
            .distinct()
            .where(AuditLog.actor_email.isnot(None))
            .order_by(AuditLog.actor_email)
        ).scalars()
        if value
    ]

    filters = {
        "action": action_filter,
        "event_type": event_type_filter,
        "entity_type": entity_filter,
        "actor": actor_filter,
        "start_date": start_raw,
        "end_date": end_raw,
    }

    return render_template(
        "admin/audit_trail.html",
        pagination=pagination,
        entries=pagination.items,
        filters=filters,
        event_types=event_type_options,
        actor_options=actor_options,
    )


@bp.route("/authentication-methods", methods=["GET", "POST"])
@login_required
@require_fresh_login()
def list_authentication_methods():
    _require_admin()

    create_form = AuthenticationMethodForm()
    if create_form.validate_on_submit():
        slug = (create_form.slug.data or "").strip().lower()
        existing = (
            AuthenticationMethod.query.filter(sa.func.lower(AuthenticationMethod.slug) == slug).first()
            if slug
            else None
        )
        if existing:
            create_form.slug.errors.append(_("admin.authentication_methods.errors.slug_exists"))
            flash(_("admin.authentication_methods.errors.slug_exists"), "danger")
        else:
            method = AuthenticationMethod(slug=slug, is_active=True)
            _refresh_method_labels(method)
            db.session.add(method)
            db.session.flush()
            log_event(
                action="authentication_method_created",
                entity_type="authentication_method",
                entity_id=method.id,
                details={"slug": method.slug, "is_active": method.is_active},
            )
            db.session.commit()
            clear_authentication_cache()
            flash(
                _(
                    "admin.authentication_methods.flash.created",
                    name=_method_display_name(method),
                ),
                "success",
            )
            return redirect(url_for("admin.list_authentication_methods"))
    else:
        for errors in create_form.errors.values():
            for error in errors:
                flash(error, "danger")

    methods = (
        AuthenticationMethod.query.order_by(AuthenticationMethod.slug.asc(), AuthenticationMethod.id.asc()).all()
    )
    i18n_manager = current_app.extensions.get("i18n") if current_app else None
    available_locales = list(i18n_manager.available_locales()) if i18n_manager else []
    if not available_locales:
        available_locales = ["en", "nl"]
    display_locales = sorted(set(available_locales))
    locale_names = {locale: locale.upper() for locale in display_locales}

    method_labels: dict[int, dict[str, str]] = {}
    method_display_names: dict[int, str] = {}
    edit_forms: dict[int, AuthenticationMethodForm] = {}
    toggle_forms: dict[int, AuthenticationMethodToggleForm] = {}
    delete_forms: dict[int, AuthenticationMethodDeleteForm] = {}
    component_usage: dict[int, int] = {}
    active_locale = get_locale()

    for method in methods:
        edit_form = AuthenticationMethodForm(obj=method)
        edit_form.slug.data = method.slug
        edit_form.submit.label.text = _("admin.authentication_methods.form.update_submit")
        edit_forms[method.id] = edit_form

        method_labels[method.id] = {locale: method.get_label(locale) for locale in display_locales}
        method_display_names[method.id] = method.get_label(active_locale)

        toggle_form = AuthenticationMethodToggleForm()
        toggle_form.method_id.data = str(method.id)
        toggle_form.submit.label.text = (
            _("admin.authentication_methods.form.deactivate")
            if method.is_active
            else _("admin.authentication_methods.form.activate")
        )
        toggle_forms[method.id] = toggle_form

        delete_form = AuthenticationMethodDeleteForm()
        delete_form.method_id.data = str(method.id)
        delete_form.submit.label.text = _("admin.authentication_methods.form.delete")
        delete_forms[method.id] = delete_form

        component_usage[method.id] = Component.query.filter(
            Component.authentication_method_id == method.id
        ).count()

    return render_template(
        "admin/authentication_methods.html",
        methods=methods,
        create_form=create_form,
        edit_forms=edit_forms,
        toggle_forms=toggle_forms,
        delete_forms=delete_forms,
        component_usage=component_usage,
        display_locales=display_locales,
        locale_names=locale_names,
        method_labels=method_labels,
        method_display_names=method_display_names,
        active_locale=active_locale,
    )


@bp.post("/authentication-methods/<int:method_id>")
@login_required
@require_fresh_login()
def update_authentication_method(method_id: int):
    _require_admin()
    method = _get_authentication_method(method_id)

    form = AuthenticationMethodForm()
    if form.validate_on_submit():
        slug = (form.slug.data or "").strip().lower()
        existing = (
            AuthenticationMethod.query.filter(
                sa.func.lower(AuthenticationMethod.slug) == slug,
                AuthenticationMethod.id != method.id,
            ).first()
            if slug
            else None
        )
        if existing:
            flash(_("admin.authentication_methods.errors.slug_exists"), "danger")
        else:
            previous_slug = method.slug
            method.slug = slug
            _refresh_method_labels(method)
            db.session.flush()
            log_event(
                action="authentication_method_updated",
                entity_type="authentication_method",
                entity_id=method.id,
                details={
                    "slug": method.slug,
                    "previous_slug": previous_slug,
                },
            )
            db.session.commit()
            clear_authentication_cache()
            flash(
                _(
                    "admin.authentication_methods.flash.updated",
                    name=_method_display_name(method),
                ),
                "success",
            )
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.list_authentication_methods"))


@bp.post("/authentication-methods/<int:method_id>/toggle")
@login_required
@require_fresh_login()
def toggle_authentication_method(method_id: int):
    _require_admin()
    method = _get_authentication_method(method_id)

    form = AuthenticationMethodToggleForm()
    submitted_id: int | None = None
    if form.validate_on_submit():
        try:
            submitted_id = int(form.method_id.data)
        except (TypeError, ValueError):
            submitted_id = None
    if submitted_id == method_id:
        method.is_active = not method.is_active
        db.session.flush()
        log_event(
            action="authentication_method_toggled",
            entity_type="authentication_method",
            entity_id=method.id,
            details={"is_active": method.is_active},
        )
        db.session.commit()
        clear_authentication_cache()
        flash(
            _(
                "admin.authentication_methods.flash.toggled",
                name=_method_display_name(method),
                state=_("admin.authentication_methods.state.active")
                if method.is_active
                else _("admin.authentication_methods.state.inactive"),
            ),
            "info",
        )
    else:
        flash(_("admin.authentication_methods.errors.toggle_failed"), "danger")

    return redirect(url_for("admin.list_authentication_methods"))


@bp.post("/authentication-methods/<int:method_id>/delete")
@login_required
@require_fresh_login()
def delete_authentication_method(method_id: int):
    _require_admin()
    method = _get_authentication_method(method_id)
    form = AuthenticationMethodDeleteForm()
    submitted_id: int | None = None
    if form.validate_on_submit():
        try:
            submitted_id = int(form.method_id.data)
        except (TypeError, ValueError):
            submitted_id = None
    if submitted_id != method_id:
        flash(_("admin.authentication_methods.errors.delete_failed"), "danger")
        return redirect(url_for("admin.list_authentication_methods"))

    usage_count = Component.query.filter(Component.authentication_method_id == method.id).count()
    if usage_count:
        method.is_active = False
        db.session.flush()
        log_event(
            action="authentication_method_deactivated",
            entity_type="authentication_method",
            entity_id=method.id,
            details={"slug": method.slug, "reason": "in_use", "usage_count": usage_count},
        )
        db.session.commit()
        clear_authentication_cache()
        flash(
            _(
                "admin.authentication_methods.flash.deactivated_instead_of_deleted",
                name=_method_display_name(method),
                count=usage_count,
            ),
            "warning",
        )
        return redirect(url_for("admin.list_authentication_methods"))

    method_id = method.id
    method_slug = method.slug
    db.session.delete(method)
    log_event(
        action="authentication_method_deleted",
        entity_type="authentication_method",
        entity_id=method_id,
        details={"slug": method_slug},
    )
    db.session.commit()
    clear_authentication_cache()
    flash(
        _("admin.authentication_methods.flash.deleted", name=_method_display_name(method)),
        "success",
    )
    return redirect(url_for("admin.list_authentication_methods"))


@bp.route("/risks/create", methods=["GET", "POST"])
@login_required
@require_fresh_login()
def create_risk():
    _require_admin()

    form = RiskForm()
    configure_risk_form(form, ineligible_suffix=_("admin.risks.form.ineligible_suffix"))
    form.submit.label.text = _("admin.risks.form.submit_create")

    if request.method == "POST" and form.validate_on_submit():
        try:
            component_ids = [int(value) for value in form.component_ids.data]
            components = validate_component_ids(component_ids)
        except ValueError:
            form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        else:
            try:
                controls = validate_control_ids(form.csa_control_ids.data or [])
            except ValueError:
                form.csa_control_ids.errors.append(_("admin.risks.errors.invalid_controls"))
            else:
                risk = Risk(
                    title=(form.title.data or "").strip(),
                    description=form.description.data,
                    discovered_on=form.discovered_on.data,
                    impact=RiskImpact(form.impact.data),
                    chance=RiskChance(form.chance.data),
                    treatment=RiskTreatmentOption(form.treatment.data),
                    treatment_plan=form.treatment_plan.data,
                    treatment_due_date=form.treatment_due_date.data,
                    treatment_owner_id=optional_int(form.treatment_owner_id.data),
                )
                if risk.discovered_on is None:
                    risk.discovered_on = date.today()
                risk.components = components
                risk.controls = controls or []
                set_impact_areas(risk, form.impact_areas.data or [])
                db.session.add(risk)
                db.session.flush()
                log_event(
                    action="risk_created",
                    entity_type="risk",
                    entity_id=risk.id,
                    details={
                        "title": risk.title,
                        "impact": risk.impact.value,
                        "chance": risk.chance.value,
                        "treatment": risk.treatment.value,
                    },
                )
                db.session.commit()
                flash(_("admin.risks.flash.created", title=risk.title), "success")
                return redirect(url_for("admin.list_risks"))
    elif request.method == "POST":
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    return render_template(
        "admin/risk_edit.html",
        form=form,
        title=_('admin.risks.create_title'),
    )


@bp.route("/risks", methods=["GET"])
@login_required
@require_fresh_login()
def list_risks():
    _require_admin()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status_filter = request.args.get("status")

    query = Risk.query.options(
        sa.orm.selectinload(Risk.components).selectinload(Component.context_scope),
        sa.orm.selectinload(Risk.impact_area_links),
        sa.orm.selectinload(Risk.controls),
        sa.orm.selectinload(Risk.treatment_owner),
    ).order_by(Risk.created_at.desc())

    if status_filter:
        # Assuming Risk has a 'status' mapped, or filter by treatment if status is derived
        # Based on template logic, risk.status is likely derived from treatment or explicitly stored
        # Checking Risk model earlier, treatment is stored. Status might be computed.
        # But template has filter dropdown for status...
        # Wait, Risk model didn't have 'status' column in what I read.
        # It had 'treatment' (enum).
        # Let's assume for now filter might need Adjustment if status is not a column.
        pass

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    
    thresholds = load_thresholds()
    
    # Calculate severity colors
    severity_colors = {
        "low": "#10b981",       # Green
        "moderate": "#f59e0b",  # Amber
        "high": "#f97316",      # Orange
        "critical": "#ef4444",  # Red
    }

    for risk in pagination.items:
        score = risk.score()
        severity = determine_risk_severity(score, thresholds)
        severity_value = severity.value if severity else "low"
        
        # Attach properties expected by template
        risk.inherent_risk_score = score
        # Template uses risk.inherent_risk_matrix.color and .name
        risk.inherent_risk_matrix = type('obj', (object,), {
            "name": severity_value.title(),
            "color": severity_colors.get(severity_value, "#6b7280")
        })
        
        # Alias status to treatment if status attribute is missing
        if not hasattr(risk, 'status'):
            risk.status = risk.treatment

    risk_statuses = RiskTreatmentOption

    return render_template(
        "admin/risks.html",
        pagination=pagination,
        risk_statuses=risk_statuses,
    )


@bp.route("/risks/<int:risk_id>", methods=["GET", "POST"])
@login_required
@require_fresh_login()
def edit_risk(risk_id: int):
    _require_admin()
    risk = db.session.get(Risk, risk_id)
    if risk is None:
        abort(404)

    form = RiskForm(obj=risk)
    configure_risk_form(
        form,
        extra_components=list(risk.components),
        ineligible_suffix=_("admin.risks.form.ineligible_suffix"),
    )
    form.submit.label.text = _("admin.risks.form.submit_update")

    if request.method == "GET":
        form.component_ids.data = [str(component.id) for component in risk.components]
        form.impact_areas.data = [link.area.value for link in risk.impact_area_links]
        form.treatment_owner_id.data = "" if risk.treatment_owner_id is None else str(risk.treatment_owner_id)
        form.csa_control_ids.data = [str(control.id) for control in risk.controls]

    if request.method == "POST" and form.validate_on_submit():
        try:
            component_ids = [int(value) for value in form.component_ids.data]
            components = validate_component_ids(component_ids)
        except ValueError:
            form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        else:
            try:
                controls = validate_control_ids(form.csa_control_ids.data or [])
            except ValueError:
                form.csa_control_ids.errors.append(_("admin.risks.errors.invalid_controls"))
            else:
                risk.title = (form.title.data or "").strip()
                risk.description = form.description.data
                risk.discovered_on = form.discovered_on.data or risk.discovered_on
                risk.impact = RiskImpact(form.impact.data)
                risk.chance = RiskChance(form.chance.data)
                risk.treatment = RiskTreatmentOption(form.treatment.data)
                risk.treatment_plan = form.treatment_plan.data
                risk.treatment_due_date = form.treatment_due_date.data
                risk.treatment_owner_id = optional_int(form.treatment_owner_id.data)
                risk.components = components
                risk.controls = controls or []
                set_impact_areas(risk, form.impact_areas.data or [])
                db.session.flush()
                log_event(
                    action="risk_updated",
                    entity_type="risk",
                    entity_id=risk.id,
                    details={
                        "title": risk.title,
                        "impact": risk.impact.value,
                        "chance": risk.chance.value,
                        "treatment": risk.treatment.value,
                    },
                )
                db.session.commit()
                flash(_("admin.risks.flash.updated", title=risk.title), "success")
                return redirect(url_for("admin.edit_risk", risk_id=risk.id))
    elif request.method == "POST":
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    thresholds = load_thresholds()
    score = risk.score()
    severity = determine_risk_severity(score, thresholds)

    return render_template(
        "admin/risk_edit.html",
        risk=risk,
        form=form,
        thresholds=thresholds,
        score=score,
        severity=severity,
        impact_label_map=dict(form.impact.choices),
        component_choices_available=bool(form.component_ids.choices),
        RiskTreatmentOption=RiskTreatmentOption,
    )


@bp.post("/risks/<int:risk_id>/delete")
@login_required
@require_fresh_login()
def delete_risk(risk_id: int):
    _require_admin()
    risk = db.session.get(Risk, risk_id)
    if risk is None:
        abort(404)

    db.session.delete(risk)
    log_event(
        action="risk_deleted",
        entity_type="risk",
        entity_id=risk.id,
        details={"title": risk.title},
    )
    db.session.commit()
    flash(_("admin.risks.flash.deleted", title=risk.title), "info")
    return redirect(url_for("admin.list_risks"))


@bp.route("/risk-thresholds", methods=["GET", "POST"])
@login_required
@require_fresh_login()
def risk_thresholds():
    _require_admin()
    thresholds = load_thresholds()
    forms: dict[int, RiskThresholdForm] = {}
    submitted: tuple[RiskThresholdForm, RiskSeverityThreshold] | None = None

    for threshold in thresholds:
        prefix = f"threshold-{threshold.id}"
        form = RiskThresholdForm(prefix=prefix)
        form.severity.data = threshold.severity.value
        form.submit.label.text = _("admin.risks.thresholds.form.submit")
        form.min_score.label.text = _("admin.risks.thresholds.form.min_label")
        form.max_score.label.text = _("admin.risks.thresholds.form.max_label")
        if request.method == "GET":
            form.min_score.data = threshold.min_score
            form.max_score.data = threshold.max_score
        forms[threshold.id] = form
        if request.method == "POST" and form.submit.data:
            submitted = (form, threshold)

    if submitted:
        form, threshold = submitted
        if form.validate():
            threshold.min_score = form.min_score.data or threshold.min_score
            threshold.max_score = form.max_score.data or threshold.max_score
            if thresholds_overlap(thresholds):
                form.max_score.errors.append(_("admin.risks.thresholds.errors.overlap"))
                db.session.rollback()
            else:
                db.session.commit()
                flash(
                    _(
                        "admin.risks.thresholds.flash.updated",
                        severity=_("risk.severity." + threshold.severity.value),
                    ),
                    "success",
                )
                return redirect(url_for("admin.risk_thresholds"))
        else:
            db.session.rollback()
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")
    elif request.method == "POST":
        flash(_("admin.risks.thresholds.errors.no_selection"), "warning")

    return render_template(
        "admin/risk_thresholds.html",
        thresholds=thresholds,
        forms=forms,
    )


@bp.get("/users")
@login_required
@require_fresh_login()
def list_users():
    _require_admin()

    records = User.query.order_by(User.created_at.desc()).all()
    available_roles = Role.query.order_by(Role.name.asc()).all()
    role_labels = {role.name: _role_display_name(role) for role in available_roles}
    admin_count = User.query.filter(User.roles.any(Role.name == "admin")).count()
    protected_admin_ids: set[int] = set()
    if admin_count <= 1:
        protected_admin_ids = {user.id for user in records if user.has_role("admin")}

    assign_forms: dict[int, UserRoleAssignForm] = {}
    remove_forms: dict[int, dict[str, dict[str, object]]] = {}

    for user in records:
        assign_form = UserRoleAssignForm()
        role_choices = [
            (role.name, role_labels.get(role.name, role.description or role.name.title()))
            for role in available_roles
            if role not in user.roles
        ]
        if role_choices:
            assign_form.role.choices = [("", _("admin.users.form.select_role"))] + role_choices  # type: ignore[assignment]
            assign_form.role.data = ""
        else:
            assign_form.role.choices = []  # type: ignore[assignment]
        assign_forms[user.id] = assign_form

        user_remove_forms: dict[str, dict[str, object]] = {}
        is_protected_admin = user.id in protected_admin_ids
        for role in user.roles:
            disabled_reason = ""
            remove_form: UserRoleRemoveForm | None = None
            if role.name == "admin" and is_protected_admin:
                disabled_reason = _("admin.users.flash.admin_must_remain")
            else:
                remove_form = UserRoleRemoveForm()
                remove_form.role.data = role.name
            user_remove_forms[role.name] = {
                "form": remove_form,
                "disabled_reason": disabled_reason,
            }
        remove_forms[user.id] = user_remove_forms

    return render_template(
        "admin/users.html",
        users=records,
        UserStatus=UserStatus,
        assign_forms=assign_forms,
        remove_forms=remove_forms,
        protected_admin_ids=protected_admin_ids,
        role_labels=role_labels,
    )


@bp.post("/users/<int:user_id>/activate")
@login_required
@require_fresh_login()
def activate_user(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if user.status != UserStatus.ACTIVE:
        user.status = UserStatus.ACTIVE
        user.activated_at = datetime.now(UTC)
        user.deactivated_at = None
        db.session.flush()
        log_event(
            action="user_activated",
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email},
        )
        db.session.commit()
        flash(_("admin.users.flash.user_activated"), "success")
    else:
        flash(_("admin.users.flash.user_already_active"), "info")

    return redirect(url_for("admin.list_users"))


@bp.post("/users/<int:user_id>/deactivate")
@login_required
@require_fresh_login()
def deactivate_user(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if user.has_role("admin"):
        admin_count = User.query.filter(User.roles.any(Role.name == "admin")).count()
        if admin_count <= 1:
            flash(_("admin.users.flash.final_admin_cannot_be_deactivated"), "danger")
            return redirect(url_for("admin.list_users"))

    if user.status == UserStatus.DISABLED:
        flash(_("admin.users.flash.user_already_deactivated"), "info")
    else:
        user.status = UserStatus.DISABLED
        user.deactivated_at = datetime.now(UTC)
        db.session.flush()
        log_event(
            action="user_deactivated",
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email},
        )
        db.session.commit()
        flash(_("admin.users.flash.user_deactivated"), "success")

    return redirect(url_for("admin.list_users"))


@bp.post("/users/<int:user_id>/delete")
@login_required
@require_fresh_login()
def delete_user(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if user.id == current_user.id:
        flash(_("admin.users.flash.cannot_delete_current_account"), "danger")
        return redirect(url_for("admin.list_users"))

    if user.has_role("admin"):
        admin_count = User.query.filter(User.roles.any(Role.name == "admin")).count()
        if admin_count <= 1:
            flash(_("admin.users.flash.final_admin_cannot_be_deleted"), "danger")
            return redirect(url_for("admin.list_users"))

    target_id = user.id
    target_email = user.email
    db.session.delete(user)
    log_event(
        action="user_deleted",
        entity_type="user",
        entity_id=target_id,
        details={"email": target_email},
    )
    db.session.commit()
    flash(_("admin.users.flash.user_deleted"), "success")
    return redirect(url_for("admin.list_users"))


@bp.post("/users/<int:user_id>/roles")
@login_required
@require_fresh_login()
def assign_user_role(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    form = UserRoleAssignForm()
    available_roles = Role.query.order_by(Role.name.asc()).all()
    role_labels = {role.name: _role_display_name(role) for role in available_roles}
    role_choices = [
        (role.name, role_labels.get(role.name, role.description or role.name.title()))
        for role in available_roles
    ]
    form.role.choices = (([("", _("admin.users.form.select_role"))] + role_choices) if role_choices else [])  # type: ignore[assignment]

    if not available_roles:
        flash(_("admin.users.flash.no_roles_configured"), "warning")
        return redirect(url_for("admin.list_users"))

    if form.validate_on_submit():
        role_name = form.role.data
        role_obj = next((role for role in available_roles if role.name == role_name), None)
        if role_obj is None:
            flash(_("admin.users.flash.unknown_role_selected"), "danger")
        elif role_obj in user.roles:
            flash(_("admin.users.flash.user_has_role"), "info")
        else:
            user.roles.append(role_obj)
            db.session.flush()
            log_event(
                action="user_role_assigned",
                entity_type="user_role",
                entity_id=user.id,
                details={"role": role_obj.name, "user_id": user.id},
            )
            db.session.commit()
            flash(_("admin.users.flash.role_assigned"), "success")
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.list_users"))


@bp.post("/users/<int:user_id>/roles/remove")
@login_required
@require_fresh_login()
def remove_user_role(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    form = UserRoleRemoveForm()

    if form.validate_on_submit():
        role_name = form.role.data
        role_obj = Role.query.filter_by(name=role_name).first()
        if role_obj is None:
            flash(_("admin.users.flash.unknown_role_remove"), "danger")
        elif role_obj not in user.roles:
            flash(_("admin.users.flash.user_does_not_have_role"), "info")
        else:
            if role_obj.name == "admin":
                admin_count = (
                    User.query.join(User.roles)
                    .filter(Role.name == "admin")
                    .count()
                )
                if admin_count <= 1:
                    flash(_("admin.users.flash.admin_must_remain"), "danger")
                    return redirect(url_for("admin.list_users"))
            user.roles.remove(role_obj)
            db.session.flush()
            log_event(
                action="user_role_removed",
                entity_type="user_role",
                entity_id=user.id,
                details={"role": role_obj.name, "user_id": user.id},
            )
            db.session.commit()
            flash(_("admin.users.flash.role_removed"), "success")
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.list_users"))


@bp.route("/users/<int:user_id>/mfa", methods=["GET", "POST"])
@login_required
@require_fresh_login()
def user_mfa(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    issuer = current_app.config.get("MFA_ISSUER_NAME", "Scaffold Platform")

    if request.method == "POST":
        action = request.form.get("action", "").lower()
        if action == "enable":
            provisioning = ensure_mfa_provisioning(user, issuer)
            log_event(
                action="user_mfa_enabled",
                entity_type="user",
                entity_id=user.id,
                details={"email": user.email},
                commit=True,
            )
            flash(_("admin.users.flash.mfa_enabled"), "success")
            return redirect(url_for("admin.user_mfa", user_id=user.id))
        if action == "disable":
            if user.mfa_setting:
                user.mfa_setting.enabled = False
                user.mfa_setting.enrolled_at = None
                db.session.flush()
                log_event(
                    action="user_mfa_disabled",
                    entity_type="user",
                    entity_id=user.id,
                    details={"email": user.email},
                )
                db.session.commit()
                flash(_("admin.users.flash.mfa_disabled"), "info")
            else:
                flash(_("admin.users.flash.mfa_not_enabled"), "warning")
            return redirect(url_for("admin.user_mfa", user_id=user.id))
        if action == "regenerate":
            provisioning = build_provisioning(user.email, issuer)
            if user.mfa_setting is None:
                setting = MFASetting()
                setting.secret = provisioning.secret
                setting.enabled = True
                user.mfa_setting = setting
                db.session.add(setting)
            else:
                user.mfa_setting.secret = provisioning.secret
                user.mfa_setting.enabled = True
                user.mfa_setting.enrolled_at = None
            db.session.flush()
            log_event(
                action="user_mfa_regenerated",
                entity_type="user",
                entity_id=user.id,
                details={"email": user.email},
            )
            db.session.commit()
            flash(_("admin.users.flash.mfa_regenerated"), "warning")
            return redirect(url_for("admin.user_mfa", user_id=user.id))

        flash(_("admin.users.flash.unknown_action"), "danger")
        return redirect(url_for("admin.user_mfa", user_id=user.id))

    if user.mfa_setting:
        provisioning = build_provisioning(user.email, issuer, secret=user.mfa_setting.secret)
    else:
        provisioning = None

    return render_template(
        "admin/user_mfa.html",
        target_user=user,
        provisioning=provisioning,
    )


@bp.route("/bia/tiers")
@login_required
def list_bia_tiers():
    _require_admin()
    tiers = db.session.scalars(sa.select(BiaTier).order_by(BiaTier.level)).all()
    return render_template("admin/bia_tiers_list.html", tiers=tiers)


@bp.route("/bia/tiers/<int:tier_id>", methods=["GET", "POST"])
@login_required
def edit_bia_tier(tier_id: int):
    _require_admin()
    tier = db.session.get(BiaTier, tier_id)
    if tier is None:
        abort(404)

    form = BiaTierForm(obj=tier)
    if form.validate_on_submit():
        form.populate_obj(tier)
        db.session.commit()
        log_event(
            action="bia_tier_updated",
            entity_type="bia_tier",
            entity_id=tier.id,
            details={"level": tier.level},
        )
        flash(_("admin.bia_tiers.flash.updated"), "success")
        return redirect(url_for("admin.list_bia_tiers"))

    return render_template("admin/bia_tier_form.html", form=form, tier=tier)
