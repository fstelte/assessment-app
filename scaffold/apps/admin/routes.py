"""Administrative routes handling user lifecycle and MFA management."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa

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
from ...models import AuditLog
from ..identity.models import MFASetting, Role, User, UserStatus
from ..bia.localization import translate_authentication_label
from ..bia.models import AuthenticationMethod, Component
from ..bia.services.authentication import clear_authentication_cache
from .forms import AuthenticationMethodDeleteForm, AuthenticationMethodForm, AuthenticationMethodToggleForm
from ...core.audit import log_event

bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="templates")


def _require_admin() -> None:
    if not current_user.is_authenticated or not current_user.has_role("admin"):
        abort(403)


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


@bp.get("/users")
@login_required
@require_fresh_login()
def list_users():
    _require_admin()

    records = User.query.order_by(User.created_at.desc()).all()
    available_roles = Role.query.order_by(Role.name.asc()).all()
    admin_count = User.query.filter(User.roles.any(Role.name == "admin")).count()
    protected_admin_ids: set[int] = set()
    if admin_count <= 1:
        protected_admin_ids = {user.id for user in records if user.has_role("admin")}

    assign_forms: dict[int, UserRoleAssignForm] = {}
    remove_forms: dict[int, dict[str, dict[str, object]]] = {}

    for user in records:
        assign_form = UserRoleAssignForm()
        role_choices = [
            (role.name, role.description or role.name.title())
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
    role_choices = [(role.name, role.description or role.name.title()) for role in available_roles]
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
