"""Routes for authentication and MFA flows."""

from __future__ import annotations

from datetime import UTC, datetime

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ...auth.mfa import build_provisioning, validate_token
from ...extensions import db
from ...forms import LoginForm, MFAEnrollForm, MFAVerifyForm, ProfileForm, RegistrationForm
from ...models import MFASetting, User, UserStatus
from . import bp

LOGIN_REDIRECT_ENDPOINT = "public.index"


def _login_and_update(user: User, remember: bool) -> None:
    login_user(user, remember=remember)
    user.last_login_at = datetime.now(UTC)
    db.session.commit()


def _clear_mfa_sessions() -> None:
    session.pop("mfa_pending_user_id", None)
    session.pop("mfa_enroll_user_id", None)
    session.pop("mfa_remember_me", None)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))

    form = RegistrationForm()
    if form.validate_on_submit():
        existing = User.find_by_email(form.email.data)
        if existing:
            flash("Dit e-mailadres is al geregistreerd.", "warning")
        else:
            user = User(
                email=form.email.data.strip(),
                first_name=form.first_name.data.strip() if form.first_name.data else None,
                last_name=form.last_name.data.strip() if form.last_name.data else None,
                status=UserStatus.PENDING,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(
                "Registratie ontvangen. Een administrator moet uw account activeren voordat u kunt inloggen.",
                "success",
            )
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data)
        if user is None or not user.check_password(form.password.data):
            flash("Ongeldige inloggegevens.", "danger")
        elif user.status != UserStatus.ACTIVE:
            flash("Uw account is nog niet geactiveerd door een administrator.", "warning")
        else:
            remember = bool(form.remember_me.data)
            session["mfa_remember_me"] = remember
            if user.mfa_setting and user.mfa_setting.enabled:
                if not user.mfa_setting.enrolled_at:
                    session["mfa_enroll_user_id"] = user.id
                    return redirect(url_for("auth.mfa_enroll"))
                session["mfa_pending_user_id"] = user.id
                return redirect(url_for("auth.mfa_verify"))

            _clear_mfa_sessions()
            _login_and_update(user, remember)
            flash("U bent succesvol ingelogd.", "success")
            return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))

    return render_template("auth/login.html", form=form)


@bp.get("/logout")
@login_required
def logout():
    _clear_mfa_sessions()
    logout_user()
    flash("U bent afgemeld.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/mfa/enroll", methods=["GET", "POST"])
def mfa_enroll():
    user_id = session.get("mfa_enroll_user_id")
    if not user_id:
        flash("MFA-enrolment is niet beschikbaar.", "warning")
        return redirect(url_for("auth.login"))

    try:
        lookup_id = int(user_id)
    except (TypeError, ValueError):
        lookup_id = None

    user = db.session.get(User, lookup_id) if lookup_id is not None else None
    if user is None:
        _clear_mfa_sessions()
        flash("Gebruiker niet gevonden.", "danger")
        return redirect(url_for("auth.login"))

    issuer = current_app.config.get("MFA_ISSUER_NAME", "Control Self Assessment")
    if user.mfa_setting is None or not user.mfa_setting.enabled:
        provisioning = build_provisioning(user.email, issuer)
        if user.mfa_setting is None:
            user.mfa_setting = MFASetting(secret=provisioning.secret, enabled=True)
            db.session.add(user.mfa_setting)
        else:
            user.mfa_setting.secret = provisioning.secret
            user.mfa_setting.enabled = True
            user.mfa_setting.enrolled_at = None
        db.session.commit()
    else:
        provisioning = build_provisioning(user.email, issuer, secret=user.mfa_setting.secret)

    form = MFAEnrollForm()
    if form.validate_on_submit():
        if validate_token(provisioning.secret, form.otp_token.data):
            user.mfa_setting.secret = provisioning.secret
            user.mfa_setting.mark_enrolled()
            db.session.commit()
            _clear_mfa_sessions()
            _login_and_update(user, remember=session.get("mfa_remember_me", False))
            flash("Multi-factor authenticatie is geactiveerd.", "success")
            return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))
        flash("Ongeldige code. Probeer het opnieuw.", "danger")

    return render_template(
        "auth/mfa_enroll.html",
        form=form,
        provisioning=provisioning,
    )


@bp.route("/mfa/verify", methods=["GET", "POST"])
def mfa_verify():
    user_id = session.get("mfa_pending_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    try:
        lookup_id = int(user_id)
    except (TypeError, ValueError):
        lookup_id = None

    user = db.session.get(User, lookup_id) if lookup_id is not None else None
    if user is None or not user.mfa_is_enrolled:
        _clear_mfa_sessions()
        flash("MFA verificatie is niet beschikbaar.", "warning")
        return redirect(url_for("auth.login"))

    form = MFAVerifyForm()
    if form.validate_on_submit():
        if validate_token(user.mfa_setting.secret, form.otp_token.data):
            user.mfa_setting.mark_verified()
            db.session.commit()
            remember = bool(session.get("mfa_remember_me") or form.remember_device.data)
            _clear_mfa_sessions()
            _login_and_update(user, remember)
            flash("MFA verificatie geslaagd.", "success")
            return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))
        flash("Ongeldige code. Probeer het opnieuw.", "danger")

    return render_template("auth/mfa_verify.html", form=form, user=user)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(theme=current_user.theme_preference)
    if form.validate_on_submit():
        desired_theme = form.theme.data or current_user.theme_preference
        theme_changed = desired_theme != current_user.theme_preference
        password_changed = False

        if form.new_password.data:
            if not form.current_password.data:
                form.current_password.errors.append("Voer uw huidige wachtwoord in.")
            elif not current_user.check_password(form.current_password.data):
                form.current_password.errors.append("Huidig wachtwoord is onjuist.")
            else:
                current_user.set_password(form.new_password.data)
                password_changed = True

        if form.current_password.errors:
            return render_template("auth/profile.html", form=form), 400

        if theme_changed or password_changed:
            if theme_changed:
                current_user.theme_preference = desired_theme
            db.session.commit()
            parts = []
            if theme_changed:
                parts.append("thema")
            if password_changed:
                parts.append("wachtwoord")
            flash(f"Wijzigingen opgeslagen ({' en '.join(parts)}).", "success")
        else:
            flash("Geen wijzigingen opgeslagen.", "info")
        return redirect(url_for("auth.profile"))

    if request.method == "GET":
        form.theme.data = current_user.theme_preference

    return render_template("auth/profile.html", form=form)


@bp.get("/mfa/manage")
@login_required
def mfa_manage():
    """Allow the logged-in user to (re)start the MFA enrollment flow."""

    session["mfa_enroll_user_id"] = current_user.id
    session["mfa_remember_me"] = False
    return redirect(url_for("auth.mfa_enroll"))
