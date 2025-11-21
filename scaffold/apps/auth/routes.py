"""Unified authentication routes."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping, cast

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user
from onelogin.saml2.errors import OneLogin_Saml2_Error

from ...extensions import db
from ..identity.models import User, UserStatus
from ...core.i18n import get_locale, session_storage_key, set_locale, gettext as _
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
from .role_sync import RoleSyncService
from .saml import (
    attribute_first,
    build_settings as build_saml_settings,
    init_saml_auth,
    log_saml_error,
    metadata_response,
    prepare_request,
    SamlSettings,
)

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


def _get_saml_settings() -> SamlSettings | None:
    settings = build_saml_settings(current_app.config)
    if not settings.is_configured():
        return None
    return settings


def _normalized_groups(values: Iterable[str]) -> set[str]:
    return {value.strip().lower() for value in values if isinstance(value, str) and value.strip()}


def _extract_groups(attributes: Mapping[str, Iterable[str]], settings: SamlSettings) -> list[str]:
    values = attributes.get(settings.group_attribute)
    if not values:
        return []
    return [str(value).strip() for value in values if value]


def _check_allowed_groups(group_ids: Iterable[str], allowed_ids: list[str]) -> tuple[bool, str | None]:
    if not allowed_ids:
        return True, None

    normalized = _normalized_groups(group_ids)
    permitted = {group.lower() for group in allowed_ids}
    if normalized & permitted:
        return True, None

    if normalized:
        return False, "Your account is not a member of an authorised group."

    return False, "Group membership information is missing from the assertion."


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

    allow_password = bool(current_app.config.get("PASSWORD_LOGIN_ENABLED"))
    form = LoginForm() if allow_password else None

    settings = _get_saml_settings()
    saml_enabled = settings is not None

    if request.method == "POST":
        if not allow_password or form is None:
            flash(_("auth.login.errors.password_disabled"), "danger")
            return redirect(url_for("auth.login"))

        if form.validate_on_submit():
            email = (form.email.data or "").strip()
            password = form.password.data or ""
            user: User | None = User.find_by_email(email) if email else None

            if user is None or not user.check_password(password):
                flash(_("auth.login.errors.invalid_credentials"), "danger")
                cast(list[str], form.password.errors).append(_("auth.login.errors.invalid_credentials"))
            elif user.status == UserStatus.DISABLED:
                flash(_("auth.login.errors.account_disabled"), "warning")
                cast(list[str], form.email.errors).append(_("auth.login.errors.account_disabled"))
            elif user.status == UserStatus.PENDING:
                flash(_("auth.login.errors.account_pending"), "warning")
                cast(list[str], form.email.errors).append(_("auth.login.errors.account_pending"))
            else:
                remember = bool(form.remember_me.data)
                if user.mfa_is_enrolled:
                    queue_mfa_verification(user, remember)
                    flash(_("auth.login.notices.mfa_required"), "info")
                    return redirect(url_for("auth.mfa_verify"))
                if user.mfa_is_enabled and not user.mfa_is_enrolled:
                    queue_mfa_enrolment(user, remember)
                    flash(_("auth.login.notices.mfa_enrol"), "info")
                    return redirect(url_for("auth.mfa_enroll"))
                finalise_login(user, remember, method="password")
                _flash_login_result(user)
                return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))
        else:
            flash(_("auth.login.errors.invalid_submission"), "danger")

    return render_template(
        "auth/login.html",
        form=form,
        saml_login_enabled=saml_enabled,
        password_login_enabled=allow_password,
    )


@bp.get("/login/saml")
def login_saml():
    if current_user.is_authenticated:
        return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))

    settings = _get_saml_settings()
    if settings is None:
        flash("SAML login is not configured.", "danger")
        return redirect(url_for("auth.login", saml_error=1))

    auth = init_saml_auth(prepare_request(request), settings)
    redirect_url = auth.login()
    session["saml_request_id"] = auth.get_last_request_id()
    return redirect(redirect_url)


@bp.route("/login/saml/acs", methods=["POST"])
def login_saml_acs():
    settings = _get_saml_settings()
    if settings is None:
        flash("SAML login is not configured.", "danger")
        return redirect(url_for("auth.login"))

    auth = init_saml_auth(prepare_request(request), settings)
    request_id = session.pop("saml_request_id", None)
    try:
        auth.process_response(request_id=request_id)
    except OneLogin_Saml2_Error as exc:
        log_saml_error("SAML ACS processing error", [exc.__class__.__name__], str(exc))
        flash("Unable to process SAML response.", "danger")
        return redirect(url_for("auth.login", saml_error=1))
    errors = auth.get_errors()
    if errors:
        log_saml_error("SAML ACS errors", errors, auth.get_last_error_reason())
        flash("Unable to process SAML response.", "danger")
        return redirect(url_for("auth.login", saml_error=1))

    if not auth.is_authenticated():
        flash("Authentication was not successful.", "danger")
        return redirect(url_for("auth.login", saml_error=1))

    attributes = auth.get_attributes()
    name_id = auth.get_nameid() or ""
    session_index = auth.get_session_index()
    session["saml_name_id"] = name_id
    if session_index:
        session["saml_session_index"] = session_index

    object_id = attribute_first(attributes, settings.object_id_attribute)
    upn_claim = attribute_first(attributes, settings.upn_attribute) or name_id
    email = attribute_first(attributes, settings.email_attribute) or name_id
    if not email:
        flash("Email address missing from SAML assertion.", "danger")
        return redirect(url_for("auth.login", saml_error=1))

    given_name = attribute_first(attributes, settings.first_name_attribute)
    family_name = attribute_first(attributes, settings.last_name_attribute)
    display_name = attribute_first(attributes, settings.display_name_attribute)

    group_ids = _extract_groups(attributes, settings)
    allowed, message = _check_allowed_groups(group_ids, settings.allowed_group_ids)
    if not allowed:
        current_app.logger.warning("SAML login denied for %s due to group policy", object_id or email)
        flash(message or "Access denied.", "danger")
        return redirect(url_for("auth.login", saml_error=1))

    user: User | None = None
    if object_id:
        user = User.find_by_azure_oid(object_id)
    if user is None and upn_claim:
        user = User.find_by_aad_upn(upn_claim)
    if user is None:
        user = User.find_by_email(email)

    if user is None:
        user = User()
        user.email = email
        user.username = upn_claim or email
        user.first_name = given_name or None
        user.last_name = family_name or None
        user.status = UserStatus.ACTIVE
        user.activated_at = datetime.now(UTC)
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        current_app.logger.info("Provisioned user %s via SAML", email)
    else:
        if user.status == UserStatus.DISABLED:
            flash("Your account is disabled. Contact an administrator.", "warning")
            return redirect(url_for("auth.login", saml_error=1))
        if user.status == UserStatus.PENDING:
            user.status = UserStatus.ACTIVE
            user.activated_at = user.activated_at or datetime.now(UTC)
            current_app.logger.info("Activated pending user %s via SAML", email)
        if email and email.lower() != (user.email or "").lower():
            conflicting = User.find_by_email(email)
            if conflicting and conflicting.id != user.id:
                current_app.logger.warning(
                    "Skipping email update for user %s due to conflicting account with email %s",
                    user.id,
                    email,
                )
            else:
                user.email = email
        if given_name and given_name != (user.first_name or ""):
            user.first_name = given_name
        if family_name and family_name != (user.last_name or ""):
            user.last_name = family_name
        if upn_claim and upn_claim != (user.username or ""):
            user.username = upn_claim

    if display_name:
        first_segment, _, remainder = display_name.partition(" ")
        if not user.first_name and first_segment:
            user.first_name = first_segment
        if not user.last_name and remainder:
            user.last_name = remainder
    if not user.username:
        user.username = upn_claim or email

    user.set_entra_identity(object_id or None, upn_claim or email)

    role_sync = RoleSyncService.from_app(current_app)
    role_sync.apply(user, group_ids)

    db.session.commit()

    saml_metadata: dict[str, Any] = {"provider": "saml"}
    if session_index:
        saml_metadata["saml_session_index"] = session_index
    if name_id:
        saml_metadata["saml_name_id"] = name_id

    finalise_login(user, remember=False, method="saml", metadata=saml_metadata)
    flash("Signed in with SAML.", "success")
    return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))


@bp.get("/login/saml/metadata")
def login_saml_metadata():
    settings = _get_saml_settings()
    if settings is None:
        return "SAML metadata is unavailable", 404

    metadata, mime_type = metadata_response(settings)
    response = make_response(metadata)
    response.headers["Content-Type"] = mime_type
    return response


@bp.route("/login/saml/sls", methods=["GET", "POST"])
def login_saml_sls():
    settings = _get_saml_settings()
    if settings is None:
        flash("SAML logout is not configured.", "danger")
        return redirect(url_for("auth.login"))

    auth = init_saml_auth(prepare_request(request), settings)
    request_id = session.pop("saml_logout_request_id", None)
    url = auth.process_slo(request_id=request_id)
    errors = auth.get_errors()
    if errors:
        log_saml_error("SAML SLS errors", errors, auth.get_last_error_reason())
        flash("Unable to complete SAML logout.", "danger")
        return redirect(url_for("auth.login", saml_error=1))

    relay_state = request.values.get("RelayState")
    target = relay_state or url or current_app.config.get("SAML_LOGOUT_RETURN_URL") or url_for("auth.login")
    if not relay_state:
        flash("You have been signed out.", "info")
    return redirect(target)


@bp.get("/logout")
@login_required
def logout():
    settings = _get_saml_settings()
    name_id = session.get("saml_name_id")
    session_index = session.get("saml_session_index")

    clear_mfa_state()
    logout_user()

    slo_url = None
    logout_request_id = None
    return_to = current_app.config.get("SAML_LOGOUT_RETURN_URL") or url_for("auth.login", _external=True)
    if settings:
        idp_slo = settings.config.get("idp", {}).get("singleLogoutService", {}).get("url")
        sp_slo = settings.config.get("sp", {}).get("singleLogoutService", {}).get("url")
        if idp_slo and sp_slo:
            auth = init_saml_auth(prepare_request(request), settings)
            slo_url = auth.logout(
                name_id=name_id or None,
                session_index=session_index or None,
                return_to=return_to,
            )
            logout_request_id = auth.get_last_request_id()

    session.clear()

    if logout_request_id and slo_url:
        session["saml_logout_request_id"] = logout_request_id
        return redirect(slo_url)

    flash("You have been signed out.", "info")
    return redirect(return_to)


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
            finalise_login(user, current_remember_me(), method="mfa_enroll")
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
            finalise_login(user, remember, method="mfa_verify")
            _flash_login_result(user)
            flash("MFA verification successful.", "success")
            return redirect(url_for(LOGIN_REDIRECT_ENDPOINT))
        flash("Invalid code. Try again.", "danger")

    return render_template("auth/mfa_verify.html", form=form, user=user)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    manager = current_app.extensions.get("i18n")
    available_locales = manager.available_locales() if manager else ["en"]
    if not available_locales:
        available_locales = ["en"]

    def _label(locale_code: str) -> str:
        if manager:
            return manager.translate(f"app.language.option.{locale_code}", locale=get_locale())
        return locale_code.upper()

    form.locale.choices = [(code, _label(code)) for code in available_locales]
    if not form.is_submitted():
        form.theme.data = current_user.theme_preference or "dark"
        form.locale.data = current_user.locale_preference or available_locales[0]
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
        if form.locale.data and form.locale.data != current_user.locale_preference:
            current_user.locale_preference = form.locale.data
            session[session_storage_key()] = current_user.locale_preference
            set_locale(current_user.locale_preference)
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
