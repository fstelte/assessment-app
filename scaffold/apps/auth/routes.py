"""Unified authentication routes."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user

from ...extensions import db
from ..identity.models import User, UserStatus
from .flow import (
    clear_mfa_state,
    current_remember_me,
    ensure_mfa_provisioning,
    finalise_login,
    get_enrolment_user,
    get_pending_user,
    queue_mfa_enrolment,
    queue_mfa_verification,
)
from .forms import LoginForm, MFAEnrollForm, MFAVerifyForm, ProfileForm, RegistrationForm
from .mfa import validate_token

bp = Blueprint("auth", __name__, template_folder="templates", url_prefix="/auth")

LOGIN_REDIRECT_ENDPOINT = "bia.dashboard"


def _flash_login_result(user: User) -> None:
    if not user.mfa_is_enrolled:
        flash(
            "Multi-factor authentication is not enabled yet. Configure MFA to protect your account.",
            "warning",
        )
    else:
        flash("Welcome back!", "success")


@bp.route("/register", methods=["GET", "POST"])
def register_user():
    if current_user.is_authenticated:
        return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.email = (form.email.data or "").strip()
        user.username = (form.username.data or "").strip() or None
        user.first_name = (form.first_name.data or "").strip() or None
        user.last_name = (form.last_name.data or "").strip() or None
        user.status = UserStatus.PENDING
        user.set_password(form.password.data or "")
        db.session.add(user)
        db.session.commit()
        flash("Registration received. An administrator must activate your account before you can log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data or "")
        if user is None or not user.check_password(form.password.data or ""):
            flash("Invalid credentials.", "danger")
        elif user.status != UserStatus.ACTIVE:
            flash("Your account is not active. Contact an administrator.", "warning")
        else:
            remember = bool(form.remember_me.data)
            if user.mfa_setting and user.mfa_setting.enabled:
                if not user.mfa_setting.enrolled_at:
                    queue_mfa_enrolment(user, remember)
                    flash("Complete MFA enrolment to finish signing in.", "info")
                    return redirect(url_for("auth.mfa_enroll"))
                queue_mfa_verification(user, remember)
                return redirect(url_for("auth.mfa_verify"))

            finalise_login(user, remember)
            _flash_login_result(user)
            return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))

    return render_template("auth/login.html", form=form)


@bp.get("/logout")
@login_required
def logout():
    clear_mfa_state()
    logout_user()
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/mfa/enroll", methods=["GET", "POST"])
def mfa_enroll():
    user = get_enrolment_user()
    if user is None:
        clear_mfa_state()
        flash("MFA enrolment is not available.", "warning")
        return redirect(url_for("auth.login"))

    issuer = current_app.config.get("MFA_ISSUER_NAME", "Scaffold Platform")
    provisioning = ensure_mfa_provisioning(user, issuer)

    form = MFAEnrollForm()
    if form.validate_on_submit():
        if validate_token(provisioning.secret, form.otp_token.data or ""):
            user.mfa_setting.secret = provisioning.secret
            user.mfa_setting.mark_enrolled()
            db.session.commit()
            finalise_login(user, current_remember_me())
            _flash_login_result(user)
            flash("Multi-factor authentication enabled.", "success")
            return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))
        flash("Invalid code. Try again.", "danger")

    return render_template("auth/mfa_enroll.html", form=form, provisioning=provisioning)


@bp.route("/mfa/verify", methods=["GET", "POST"])
def mfa_verify():
    user = get_pending_user()
    if user is None or not user.mfa_is_enrolled or user.mfa_setting is None:
        clear_mfa_state()
        flash("MFA verification is unavailable.", "warning")
        return redirect(url_for("auth.login"))

    form = MFAVerifyForm()
    if form.validate_on_submit():
        if validate_token(user.mfa_setting.secret, form.otp_token.data or ""):
            user.mfa_setting.mark_verified()
            db.session.commit()
            remember = bool(current_remember_me() or form.remember_device.data)
            finalise_login(user, remember)
            _flash_login_result(user)
            flash("MFA verification successful.", "success")
            return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))
        flash("Invalid code. Try again.", "danger")

    return render_template("auth/mfa_verify.html", form=form, user=user)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        updated = False

        if form.first_name.data != current_user.first_name:
            current_user.first_name = form.first_name.data
            updated = True
        if form.last_name.data != current_user.last_name:
            current_user.last_name = form.last_name.data
            updated = True
        if form.theme.data and form.theme.data != current_user.theme_preference:
            current_user.theme_preference = form.theme.data
            updated = True

        if form.new_password.data:
            if not current_user.check_password(form.current_password.data or ""):
                flash("Current password is incorrect.", "danger")
                return render_template("auth/profile.html", form=form)
            current_user.set_password(form.new_password.data)
            updated = True

        if updated:
            db.session.commit()
            flash("Profile updated.", "success")
        else:
            flash("No changes detected.", "info")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form)


@bp.get("/mfa/manage")
@login_required
def mfa_manage():
    queue_mfa_enrolment(current_user, remember=False)
    return redirect(url_for("auth.mfa_enroll"))


def register(app):
    app.register_blueprint(bp)
    app.logger.info("Authentication module registered.")
