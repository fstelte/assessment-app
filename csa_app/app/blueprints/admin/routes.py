"""Routes for administrator functionality."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...auth.mfa import build_provisioning
from ...extensions import db
from ...forms import ControlImportForm, UserRoleAssignForm, UserRoleRemoveForm
from ...models import MFASetting, Role, User, UserStatus
from ...services.control_importer import import_controls_from_mapping, import_controls_from_file
from . import bp


def _require_admin() -> None:
    if not current_user.has_role("admin"):
        abort(403)

@bp.route("/")
@login_required
def dashboard():
    _require_admin()
    return redirect(url_for("admin.users"))


@bp.route("/users", methods=["GET"])
@login_required
def users():
    _require_admin()
    records = User.query.order_by(User.created_at.desc()).all()
    admin_count = (
        User.query.filter(User.roles.any(Role.name == "admin"))
        .count()
    )
    protected_admin_ids: set[int] = set()
    if admin_count <= 1:
        protected_admin_ids = {user.id for user in records if user.has_role("admin")}

    available_roles = Role.query.order_by(Role.name.asc()).all()
    assign_forms: dict[int, UserRoleAssignForm] = {}
    remove_forms: dict[int, dict[str, dict[str, object]]] = {}

    for user in records:
        form = UserRoleAssignForm()
        role_choices = [
            (role.name, role.description or role.name.title())
            for role in available_roles
            if role not in user.roles
        ]
        if role_choices:
            form.role.choices = [("", "Selecteer een rol...")] + role_choices
            form.role.data = ""
        else:
            form.role.choices = []
        assign_forms[user.id] = form

        user_remove_forms: dict[str, dict[str, object]] = {}
        is_protected_admin = user.id in protected_admin_ids
        for role in user.roles:
            disabled_reason = ""
            remove_form: UserRoleRemoveForm | None = None
            if role.name == "admin" and is_protected_admin:
                disabled_reason = "Er moet altijd minstens één administrator zijn."
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
        flash("Gebruiker is geactiveerd.", "success")
    else:
        flash("Gebruiker was al actief.", "info")

    return redirect(url_for("admin.users"))


@bp.post("/users/<int:user_id>/deactivate")
@login_required
def deactivate_user(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if user.has_role("admin"):
        admin_count = (
            User.query.filter(User.roles.any(Role.name == "admin"))
            .count()
        )
        if admin_count <= 1:
            flash("De laatste administrator kan niet worden gedeactiveerd.", "danger")
            return redirect(url_for("admin.users"))

    if user.status == UserStatus.DISABLED:
        flash("Gebruiker was al gedeactiveerd.", "info")
    else:
        user.status = UserStatus.DISABLED
        user.deactivated_at = datetime.now(UTC)
        db.session.commit()
        flash("Gebruiker is gedeactiveerd.", "success")

    return redirect(url_for("admin.users"))


@bp.post("/users/<int:user_id>/delete")
@login_required
def delete_user(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if user.id == current_user.id:
        flash("U kunt uw eigen account niet verwijderen terwijl u bent aangemeld.", "danger")
        return redirect(url_for("admin.users"))

    if user.has_role("admin"):
        admin_count = (
            User.query.filter(User.roles.any(Role.name == "admin"))
            .count()
        )
        if admin_count <= 1:
            flash("De laatste administrator kan niet worden verwijderd.", "danger")
            return redirect(url_for("admin.users"))

    db.session.delete(user)
    db.session.commit()
    flash("Gebruiker is verwijderd.", "success")
    return redirect(url_for("admin.users"))


@bp.post("/users/<int:user_id>/roles")
@login_required
def assign_user_role(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    form = UserRoleAssignForm()
    available_roles = Role.query.order_by(Role.name.asc()).all()
    role_choices = [
        (role.name, role.description or role.name.title()) for role in available_roles
    ]
    form.role.choices = [("", "Selecteer een rol...")] + role_choices if role_choices else []

    if not available_roles:
        flash("Er zijn momenteel geen rollen geconfigureerd.", "warning")
        return redirect(url_for("admin.users"))

    if form.validate_on_submit():
        role_name = form.role.data
        role_obj = next((role for role in available_roles if role.name == role_name), None)
        if role_obj is None:
            flash("Onbekende rol geselecteerd.", "danger")
        elif role_obj in user.roles:
            flash("Gebruiker beschikt al over deze rol.", "info")
        else:
            user.roles.append(role_obj)
            db.session.commit()
            flash("Rol is toegevoegd aan de gebruiker.", "success")
            return redirect(url_for("admin.users"))
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.users"))


@bp.post("/users/<int:user_id>/roles/remove")
@login_required
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
            flash("Onbekende rol geselecteerd.", "danger")
        elif role_obj not in user.roles:
            flash("Gebruiker heeft deze rol niet.", "info")
        else:
            if role_obj.name == "admin":
                admin_count = (
                    User.query.join(User.roles)
                    .filter(Role.name == "admin")
                    .count()
                )
                if admin_count <= 1:
                    flash("Er moet altijd minstens één administrator zijn.", "danger")
                    return redirect(url_for("admin.users"))
            user.roles.remove(role_obj)
            db.session.commit()
            flash("Rol is verwijderd van de gebruiker.", "success")
            return redirect(url_for("admin.users"))
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/mfa", methods=["GET", "POST"])
@login_required
def manage_user_mfa(user_id: int):
    _require_admin()

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    issuer = current_app.config.get("MFA_ISSUER_NAME", "Control Self Assessment")
    provisioning = None

    if request.method == "POST":
        action = request.form.get("action") or ""
        if action == "enable":
            provisioning = build_provisioning(user.email, issuer)
            if user.mfa_setting is None:
                user.mfa_setting = MFASetting(secret=provisioning.secret, enabled=True)
                db.session.add(user.mfa_setting)
            else:
                user.mfa_setting.secret = provisioning.secret
                user.mfa_setting.enabled = True
                user.mfa_setting.enrolled_at = None
            db.session.commit()
            flash("MFA is ingeschakeld voor deze gebruiker. Deel het secret veilig.", "success")
        elif action == "disable":
            if user.mfa_setting:
                user.mfa_setting.enabled = False
                user.mfa_setting.enrolled_at = None
                db.session.commit()
                flash("MFA is uitgeschakeld voor deze gebruiker.", "info")
        elif action == "regenerate" and user.mfa_setting:
            provisioning = build_provisioning(user.email, issuer)
            user.mfa_setting.secret = provisioning.secret
            user.mfa_setting.enrolled_at = None
            user.mfa_setting.enabled = True
            db.session.commit()
            flash("MFA-secret is vernieuwd. Deel het nieuwe secret veilig.", "warning")
        return redirect(url_for("admin.manage_user_mfa", user_id=user.id))

    if user.mfa_setting:
        provisioning = build_provisioning(user.email, issuer, secret=user.mfa_setting.secret)

    return render_template(
        "admin/manage_user_mfa.html",
        target_user=user,
        provisioning=provisioning,
    )


@bp.route("/controls/import", methods=["GET", "POST"])
@login_required
def import_controls():
    _require_admin()

    form = ControlImportForm()
    stats = None

    if request.method == "POST" and request.form.get("action") == "import_builtin":
        builtin_path = Path(current_app.root_path).parent / "iso_27002_controls.json"
        if not builtin_path.exists():
            flash("Standaardbestand niet gevonden op de server.", "danger")
        else:
            stats = import_controls_from_file(builtin_path)
            flash(
                f"Import voltooid. Nieuw: {stats.created}, bijgewerkt: {stats.updated}.",
                "success" if not stats.errors else "warning",
            )
            for error in stats.errors:
                flash(error, "warning")
        return redirect(url_for("admin.import_controls"))

    if form.validate_on_submit():
        file_storage = form.data_file.data
        try:
            payload = json.load(file_storage)
        except json.JSONDecodeError as exc:
            flash(f"Kon JSON niet inlezen: {exc}", "danger")
            file_storage.close()
            return redirect(url_for("admin.import_controls"))

        stats = import_controls_from_mapping(payload)
        flash(
            f"Import voltooid. Nieuw: {stats.created}, bijgewerkt: {stats.updated}.",
            "success" if not stats.errors else "warning",
        )
        for error in stats.errors:
            flash(error, "warning")
        return redirect(url_for("admin.import_controls"))

    return render_template("admin/import_controls.html", form=form)
