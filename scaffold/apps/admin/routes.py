"""Administrative routes handling user lifecycle and MFA management."""

from __future__ import annotations

from datetime import UTC, datetime

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
from ...core.i18n import gettext as _
from flask_login import current_user, login_required

from ...core.security import require_fresh_login
from ...extensions import db
from ..auth.flow import ensure_mfa_provisioning
from ..auth.mfa import build_provisioning
from ..csa.forms import UserRoleAssignForm, UserRoleRemoveForm
from ..identity.models import MFASetting, Role, User, UserStatus

bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="templates")


def _require_admin() -> None:
    if not current_user.is_authenticated or not current_user.has_role("admin"):
        abort(403)


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

    db.session.delete(user)
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
            flash(_("admin.users.flash.mfa_enabled"), "success")
            return redirect(url_for("admin.user_mfa", user_id=user.id))
        if action == "disable":
            if user.mfa_setting:
                user.mfa_setting.enabled = False
                user.mfa_setting.enrolled_at = None
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
