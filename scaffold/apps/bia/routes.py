"""Routes implementing the complete Business Impact Analysis workflow."""

from __future__ import annotations

import csv
import io
import logging
from collections import defaultdict
from datetime import date, datetime

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload
from urllib.parse import urlparse

from ...core.audit import log_change_event
from ...core.security import require_fresh_login
from ...core.i18n import gettext as _, get_locale
from ...extensions import db
from ..identity.models import ROLE_ADMIN, ROLE_ASSESSMENT_MANAGER, User, UserStatus
from .forms import (
    AvailabilityForm,
    ChangePasswordForm,
    ComponentForm,
    ConsequenceForm,
    ContextScopeForm,
    ImportCSVForm,
    ImportSQLForm,
    SummaryForm,
)
from .models import (
    AIIdentificatie,
    AvailabilityRequirements,
    Component,
    ComponentEnvironment,
    Consequences,
    ContextScope,
    ENVIRONMENT_TYPES,
    Summary,
)
from .services.authentication import (
    list_authentication_options,
    lookup_by_id as lookup_authentication_option,
)
from .utils import (
    ensure_export_folder,
    export_to_csv,
    export_to_sql,
    get_cia_impact,
    get_impact_color,
    get_impact_level,
    get_max_cia_impact,
    import_from_csv,
    import_sql_file,
)
def get_impact_color(impact):
    impact_colors = {
        'catastrophic': 'badge bg-danger',
        'major': 'badge bg-warning text-dark',
        'moderate': 'badge bg-info text-dark',
        'minor': 'badge bg-primary',
        'insignificant': 'badge bg-success'
    }
    return impact_colors.get(impact.lower(), 'badge bg-secondary')

bp = Blueprint(
    "bia",
    __name__,
    url_prefix="/bia",
    template_folder="templates",
    static_folder="static",
)


# Environment selection order and ranking for fallback authentication resolution.
# Priority: production (0) > acceptance (1) > test (2) > development (3)
_ENVIRONMENT_SELECTION_ORDER = tuple(reversed(ENVIRONMENT_TYPES))
_ENVIRONMENT_SELECTION_RANK = {name: index for index, name in enumerate(_ENVIRONMENT_SELECTION_ORDER)}


@bp.app_context_processor
def inject_helpers():
    return {
        "bia_get_cia_impact": get_cia_impact,
        "bia_get_impact_color": get_impact_color,
        "bia_get_max_cia_impact": get_max_cia_impact,
        "bia_ai_badge_tokens": _ai_badge_tokens,
        "bia_component_authentication": _describe_authentication,
        "bia_environment_label": _environment_label,
        "bia_environment_types": ENVIRONMENT_TYPES,
        "bia_component_environment": _get_component_environment,
        "bia_environment_authentication": _describe_environment_authentication,
    }


def _ai_badge_tokens(category: str | None) -> dict[str, str]:
    normalized = (category or "").strip().lower()
    if normalized == "unacceptable risk":
        return {"class": "bg-danger text-white"}
    if normalized == "high risk":
        return {"class": "badge-ai-high-risk"}
    if normalized == "limited risk":
        return {"class": "bg-warning text-dark"}
    if normalized == "minimal risk":
        return {"class": "bg-success"}
    if normalized == "no ai":
        return {"class": "bg-success"}
    return {"class": "bg-secondary"}


def _environment_label(environment_type: str) -> str:
    return _("bia.components.environments.types." + environment_type)


def _configure_component_form(
    form: ComponentForm,
    *,
    component: Component | None = None,
) -> None:
    locale = get_locale()
    choices: list[tuple[str, str]] = [("", _("bia.components.authentication.placeholder"))]
    assigned_auth_ids: set[int] = set()
    if component is not None:
        if component.authentication_method_id is not None:
            assigned_auth_ids.add(component.authentication_method_id)
        for environment in component.environments:
            if environment.authentication_method_id is not None:
                assigned_auth_ids.add(environment.authentication_method_id)
    for option in list_authentication_options(active_only=False):
        if not option.is_active and option.id not in assigned_auth_ids:
            continue
        choices.append((str(option.id), option.label(locale)))
    form.environment_authentication_choices = choices
    _configure_environment_subforms(form, choices, component)


def _configure_environment_subforms(
    form: ComponentForm,
    auth_choices: list[tuple[str, str]],
    component: Component | None,
) -> None:
    while len(form.environments) < len(ENVIRONMENT_TYPES):
        form.environments.append_entry()
    while len(form.environments) > len(ENVIRONMENT_TYPES):
        form.environments.pop_entry()

    existing: dict[str, ComponentEnvironment] = {}
    if component is not None:
        existing = {env.environment_type: env for env in component.environments}

    for index, environment_type in enumerate(ENVIRONMENT_TYPES):
        subform = form.environments[index].form
        subform.environment_type.data = environment_type
        subform.authentication_method.choices = auth_choices
        subform.environment_label = _environment_label(environment_type)
        if request.method != "POST":
            matched = existing.get(environment_type)
            if matched is not None:
                subform.is_enabled.data = bool(matched.is_enabled)
                subform.authentication_method.data = matched.authentication_method_id
            else:
                subform.is_enabled.data = False
                subform.authentication_method.data = None


def _select_primary_environment_assignment(component: Component) -> ComponentEnvironment | None:
    best_assignment: ComponentEnvironment | None = None
    best_rank: int | None = None
    for environment in component.environments:
        if not getattr(environment, "is_enabled", True):
            continue
        if environment.authentication_method_id is None:
            continue
        rank = _ENVIRONMENT_SELECTION_RANK.get(environment.environment_type, len(_ENVIRONMENT_SELECTION_RANK))
        if best_assignment is None or rank < best_rank:
            best_assignment = environment
            best_rank = rank
    return best_assignment


def _resolve_component_authentication_method_id(component: Component) -> int | None:
    """Resolve authentication method ID for a component.

    Returns the component's direct authentication_method_id if set,
    otherwise falls back to the authentication method from the highest
    priority enabled environment (production > acceptance > test > development).

    Returns None if no authentication method is assigned.
    """
    if component.authentication_method_id is not None:
        return component.authentication_method_id
    assignment = _select_primary_environment_assignment(component)
    if assignment is not None:
        return assignment.authentication_method_id
    return None


def _describe_authentication(component: Component) -> str | None:
    method_id = _resolve_component_authentication_method_id(component)
    if method_id is None:
        return None
    snapshot = lookup_authentication_option(method_id)
    if snapshot is None:
        return None
    return snapshot.label(get_locale())


def _describe_environment_authentication(environment: ComponentEnvironment | None) -> str | None:
    if environment is None:
        return None
    method = environment.authentication_method
    if method is not None:
        return method.get_label(get_locale())
    if environment.authentication_method_id is None:
        return None
    snapshot = lookup_authentication_option(environment.authentication_method_id)
    if snapshot is None:
        return None
    return snapshot.label(get_locale())


def _get_component_environment(component: Component, environment_type: str) -> ComponentEnvironment | None:
    for environment in component.environments:
        if environment.environment_type == environment_type:
            return environment
    return None


def _serialize_environments(component: Component) -> list[dict[str, object]]:
    ordering = {environment: index for index, environment in enumerate(ENVIRONMENT_TYPES)}
    serialized: list[dict[str, object]] = []
    for environment in sorted(
        component.environments,
        key=lambda item: ordering.get(item.environment_type, len(ordering)),
    ):
        serialized.append(
            {
                "environment_type": environment.environment_type,
                "is_enabled": environment.is_enabled,
                "authentication_method_id": environment.authentication_method_id,
                "authentication_method_label": _describe_environment_authentication(environment),
            }
        )
    return serialized


def _sync_component_environments(component: Component, form: ComponentForm) -> None:
    existing = {environment.environment_type: environment for environment in component.environments}
    seen: set[str] = set()

    for entry in form.environments:
        subform = entry.form
        environment_type = (subform.environment_type.data or "").strip()
        if not environment_type:
            continue
        seen.add(environment_type)
        is_enabled = bool(subform.is_enabled.data)
        authentication_method_id = subform.authentication_method.data
        environment = existing.get(environment_type)
        if is_enabled:
            if environment is None:
                environment = ComponentEnvironment(component=component, environment_type=environment_type)
                db.session.add(environment)
                existing[environment_type] = environment
            environment.is_enabled = is_enabled
            environment.authentication_method_id = authentication_method_id
        elif environment is not None:
            db.session.delete(environment)
            existing.pop(environment_type, None)

    for environment_type, environment in list(existing.items()):
        if environment_type not in seen:
            db.session.delete(environment)

def _can_manage_bia_owner() -> bool:
    return current_user.has_role(ROLE_ADMIN) or current_user.has_role(ROLE_ASSESSMENT_MANAGER)


def _can_edit_context(context: ContextScope) -> bool:
    if context.author:
        return context.author == current_user
    return current_user.has_role(ROLE_ADMIN)


def _safe_return_target(target: str | None) -> str | None:
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    path = parsed.path or ""
    if not path.startswith("/"):
        return None
    sanitized = path
    if parsed.query:
        sanitized = f"{sanitized}?{parsed.query}"
    if parsed.fragment:
        sanitized = f"{sanitized}#{parsed.fragment}"
    return sanitized


@bp.route("/")
@bp.route("/index")
@login_required
def dashboard():
    contexts = ContextScope.query.order_by(ContextScope.last_update.desc()).all()
    can_manage_owner = _can_manage_bia_owner()
    owner_choices: list[User] = []
    if can_manage_owner:
        owner_choices = (
            User.query.filter(User.status == UserStatus.ACTIVE)
            .order_by(User.last_name.asc(), User.first_name.asc(), User.email.asc())
            .all()
        )
    editable_context_ids = {context.id for context in contexts if _can_edit_context(context)}
    owner_choice_ids = {user.id for user in owner_choices}
    return render_template(
        "bia/dashboard.html",
        contexts=contexts,
        can_manage_owner=can_manage_owner,
        owner_choices=owner_choices,
        owner_choice_ids=owner_choice_ids,
        editable_context_ids=editable_context_ids,
    )


@bp.route("/item/new", methods=["GET", "POST"])
@login_required
def new_item():
    form = ContextScopeForm()
    component_form = ComponentForm()
    _configure_component_form(component_form)
    can_assign_owner = _can_manage_bia_owner()
    if form.validate_on_submit():
        context = ContextScope(author=_resolve_user())
        if context.author:
            context.responsible = context.author.full_name
            context.risk_owner = context.author.full_name
        _apply_context_form(form, context, allow_owner_assignment=can_assign_owner)
        context.last_update = date.today()
        db.session.add(context)
        db.session.commit()
        flash(_("bia.flash.created"), "success")
        return redirect(url_for("bia.view_item", item_id=context.id))
    return render_template(
        "bia/context_form.html",
        form=form,
        component_form=component_form,
        item=None,
        can_assign_owner=can_assign_owner,
    )


@bp.route("/item/<int:item_id>")
@login_required
def view_item(item_id: int):
    item = (
        ContextScope.query.options(
            joinedload(ContextScope.components)
            .joinedload(Component.environments)
            .joinedload(ComponentEnvironment.authentication_method),
            joinedload(ContextScope.components).joinedload(Component.consequences),
            joinedload(ContextScope.components).joinedload(Component.ai_identificaties),
            joinedload(ContextScope.components).joinedload(Component.availability_requirement),
        )
        .filter(ContextScope.id == item_id)
        .one_or_none()
    )
    if item is None:
        abort(404)
    consequences = [consequence for component in item.components for consequence in component.consequences]
    max_cia_impact = get_max_cia_impact(consequences)
    ai_identifications = _collect_ai_identifications(item)

    return render_template(
        "bia/context_detail.html",
        item=item,
        consequences=consequences,
        max_cia_impact=max_cia_impact,
        ai_identifications=ai_identifications,
        can_edit_context=_can_edit_context(item),
    )


@bp.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if not _can_edit_context(item):
        flash(_("bia.flash.owner_forbidden"), "danger")
        return redirect(url_for("bia.view_item", item_id=item.id))

    form = ContextScopeForm(obj=item)
    component_form = ComponentForm()
    _configure_component_form(component_form)
    can_assign_owner = _can_manage_bia_owner()
    if form.validate_on_submit():
        _apply_context_form(form, item, allow_owner_assignment=can_assign_owner)
        item.last_update = date.today()
        db.session.commit()
        flash(_("bia.flash.updated"), "success")
        return redirect(url_for("bia.view_item", item_id=item.id))

    return render_template(
        "bia/context_form.html",
        form=form,
        component_form=component_form,
        item=item,
        can_assign_owner=can_assign_owner,
    )


@bp.route("/item/<int:item_id>/delete", methods=["POST"])
@login_required
@require_fresh_login(max_age_minutes=30)
def delete_item(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if not _can_edit_context(item):
        flash(_("bia.flash.owner_delete_forbidden"), "danger")
        return redirect(url_for("bia.view_item", item_id=item.id))

    db.session.delete(item)
    db.session.commit()
    flash(_("bia.flash.deleted"), "success")
    return redirect(url_for("bia.dashboard"))


@bp.route("/item/<int:item_id>/owner", methods=["POST"])
@login_required
def update_owner(item_id: int):
    context = ContextScope.query.get_or_404(item_id)
    if not _can_manage_bia_owner():
        flash(_("bia.flash.owner_permission_denied"), "danger")
        return redirect(url_for("bia.dashboard"))

    previous_state = {
        "author_id": context.author_id,
        "author_name": getattr(context.author, "full_name", None) if context.author else None,
        "responsible": context.responsible,
        "security_manager": context.security_manager,
    }

    owner_raw = (request.form.get("owner_id") or "").strip()
    message: str
    if not owner_raw:
        context.author = None
        context.responsible = None
        message = _("bia.flash.owner_cleared")
        assigned_owner = None
    else:
        try:
            owner_id = int(owner_raw)
        except ValueError:
            flash(_("bia.flash.invalid_owner"), "danger")
            return redirect(url_for("bia.dashboard"))
        owner = User.query.filter(User.id == owner_id, User.status == UserStatus.ACTIVE).first()
        if not owner:
            flash(_("bia.flash.unavailable_owner"), "danger")
            return redirect(url_for("bia.dashboard"))
        context.author = owner
        context.responsible = owner.full_name
        message = _("bia.flash.owner_set", name=owner.full_name)
        assigned_owner = owner
    context._suppress_last_update = True

    current_state = {
        "author_id": context.author_id,
        "author_name": getattr(context.author, "full_name", None) if context.author else None,
        "responsible": context.responsible,
        "security_manager": context.security_manager,
    }

    changes: dict[str, dict[str, str | int | None]] = {}

    for field, previous in previous_state.items():
        current = current_state.get(field)
        if previous != current:
            changes[field] = {"old": previous, "new": current}

    if changes:
        metadata = {
            "source": "bia.dashboard",
            "bia_name": context.name,
        }
        if assigned_owner is not None:
            metadata["assigned_owner_id"] = assigned_owner.id
            metadata["assigned_owner_email"] = assigned_owner.email
        log_change_event(
            action="owner_updated",
            entity_type="bia.context_scope",
            entity_id=context.id,
            changes=changes,
            metadata=metadata,
        )

    db.session.commit()
    flash(message, "success")
    return redirect(url_for("bia.dashboard"))


@bp.route("/add_component", methods=["POST"])
@login_required
def add_component():
    form = ComponentForm()
    _configure_component_form(form)
    if form.validate_on_submit():
        context_id = request.form.get("bia_id")
        context = ContextScope.query.get(context_id) if context_id else None
        if not context:
            return jsonify({"success": False, "errors": {"bia_id": ["Unknown BIA"]}}), 400
        if not _can_edit_context(context):
            return (
                jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
                403,
            )
        component = Component(
            name=form.name.data,
            info_type=form.info_type.data,
            info_owner=form.info_owner.data,
            user_type=form.user_type.data,
            process_dependencies=form.process_dependencies.data,
            description=form.description.data,
            context_scope=context,
        )
        component.authentication_method_id = None
        db.session.add(component)
        _sync_component_environments(component, form)
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "id": component.id,
                "name": component.name,
                "authentication_method_id": component.authentication_method_id,
                "authentication_method_label": _describe_authentication(component),
                "authentication_method_slug": component.authentication_method.slug if component.authentication_method else None,
                "environments": _serialize_environments(component),
            }
        )
    return jsonify({"success": False, "errors": form.errors}), 400


@bp.route("/update_component/<int:component_id>", methods=["POST"])
@login_required
def update_component(component_id: int):
    component = Component.query.get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    form = ComponentForm()
    _configure_component_form(form, component=component)
    if form.validate_on_submit():
        component.name = form.name.data
        component.info_type = form.info_type.data
        component.info_owner = form.info_owner.data
        component.user_type = form.user_type.data
        component.process_dependencies = form.process_dependencies.data
        component.description = form.description.data
        component.authentication_method_id = None
        _sync_component_environments(component, form)
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "name": component.name,
                "authentication_method_id": component.authentication_method_id,
                "authentication_method_label": _describe_authentication(component),
                "authentication_method_slug": component.authentication_method.slug if component.authentication_method else None,
                "environments": _serialize_environments(component),
            }
        )
    return jsonify({"success": False, "errors": form.errors}), 400


@bp.route("/component/<int:component_id>/edit", methods=["GET", "POST"])
@login_required
def edit_component_form(component_id: int):
    component = (
        Component.query.options(
            joinedload(Component.context_scope),
            joinedload(Component.environments).joinedload(ComponentEnvironment.authentication_method),
        )
        .filter(Component.id == component_id)
        .one_or_none()
    )
    if component is None:
        abort(404)
    if not _can_edit_context(component.context_scope):
        flash(_("bia.flash.owner_forbidden"), "danger")
        return redirect(url_for("bia.view_components"))

    form = ComponentForm(obj=component)
    _configure_component_form(form, component=component)
    contexts = ContextScope.query.order_by(ContextScope.name.asc()).all()

    if form.validate_on_submit():
        context_id = request.form.get("bia_id") or (component.context_scope.id if component.context_scope else None)
        context = ContextScope.query.get(context_id) if context_id else None
        if context is None:
            flash(_("Select a valid BIA context before saving."), "danger")
        elif not _can_edit_context(context):
            flash(_("bia.flash.owner_forbidden"), "danger")
            return redirect(url_for("bia.view_components"))
        else:
            component.context_scope = context
            component.name = form.name.data
            component.info_type = form.info_type.data
            component.info_owner = form.info_owner.data
            component.user_type = form.user_type.data
            component.process_dependencies = form.process_dependencies.data
            component.description = form.description.data
            component.authentication_method_id = None
            _sync_component_environments(component, form)
            db.session.commit()
            flash(_("bia.flash.updated"), "success")
            return redirect(url_for("bia.view_components", scope=context.name))

    return render_template(
        "bia/edit_component.html",
        form=form,
        component=component,
        contexts=contexts,
    )


@bp.route("/delete_component/<int:component_id>", methods=["POST"])
@login_required
def delete_component(component_id: int):
    component = Component.query.get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    db.session.delete(component)
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/components")
@login_required
def view_components():
    scope_filter = request.args.get("scope", "all").strip()
    search_term = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    per_page = current_app.config.get("BIA_COMPONENTS_PER_PAGE", 25)
    query = (
        Component.query.options(
            joinedload(Component.context_scope),
            joinedload(Component.environments).joinedload(ComponentEnvironment.authentication_method),
            joinedload(Component.availability_requirement),
            joinedload(Component.ai_identificaties),
            joinedload(Component.dpia_assessments),
        )
        .join(ContextScope)
    )
    if scope_filter and scope_filter.lower() != "all":
        query = query.filter(ContextScope.name.ilike(f"%{scope_filter}%"))
    if search_term:
        query = query.filter(Component.name.ilike(f"%{search_term}%"))
    pagination = query.order_by(Component.name.asc()).paginate(page=page, per_page=per_page, error_out=False)
    if pagination.total and page > pagination.pages:
        return redirect(url_for("bia.view_components", page=pagination.pages, scope=scope_filter, q=search_term))
    components = pagination.items
    contexts = ContextScope.query.order_by(ContextScope.name.asc()).all()
    component_form = ComponentForm()
    _configure_component_form(component_form)
    view_functions = current_app.view_functions
    dpia_enabled = "dpia.start_from_component" in view_functions and "dpia.dashboard" in view_functions
    if pagination.total:
        page_start = (pagination.page - 1) * pagination.per_page + 1
        page_end = min(pagination.total, pagination.page * pagination.per_page)
    else:
        page_start = 0
        page_end = 0
    full_path = request.full_path or request.path
    if full_path.endswith("?"):
        full_path = full_path[:-1]
    current_view_url = full_path or request.path
    return render_template(
        "bia/components.html",
        components=components,
        contexts=contexts,
        selected_scope=scope_filter,
        pagination=pagination,
        page_start=page_start,
        page_end=page_end,
        component_form=component_form,
        per_page=per_page,
        dpia_enabled=dpia_enabled,
        search_term=search_term,
        current_view_url=current_view_url,
    )


@bp.route("/component/<int:component_id>/availability", methods=["GET", "POST"])
@login_required
def manage_component_availability(component_id: int):
    component = Component.query.options(joinedload(Component.context_scope)).get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        flash(_("bia.flash.owner_forbidden"), "danger")
        return redirect(url_for("bia.view_components"))
    form = AvailabilityForm(obj=component.availability_requirement)
    return_to = _safe_return_target(request.args.get("return_to"))
    if form.validate_on_submit():
        requirement = component.availability_requirement
        if requirement is None:
            requirement = AvailabilityRequirements(component=component)
            db.session.add(requirement)
        requirement.mtd = form.mtd.data
        requirement.rto = form.rto.data
        requirement.rpo = form.rpo.data
        requirement.masl = form.masl.data
        db.session.commit()
        flash(_("Availability requirements updated."), "success")
        return redirect(return_to or url_for("bia.view_components"))
    return render_template(
        "bia/manage_component_availability.html",
        component=component,
        form=form,
        return_to=return_to,
    )


@bp.route("/component/<int:component_id>/consequences/new", methods=["GET", "POST"])
@login_required
def add_component_consequence_view(component_id: int):
    component = Component.query.options(joinedload(Component.context_scope)).get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        flash(_("bia.flash.owner_forbidden"), "danger")
        return redirect(url_for("bia.view_components"))
    form = ConsequenceForm()
    return_to = _safe_return_target(request.args.get("return_to"))
    if form.validate_on_submit():
        categories = form.consequence_category.data or []
        for category in categories:
            consequence = Consequences(
                component=component,
                consequence_category=category,
                security_property=form.security_property.data,
                consequence_worstcase=form.consequence_worstcase.data,
                justification_worstcase=form.justification_worstcase.data,
                consequence_realisticcase=form.consequence_realisticcase.data,
                justification_realisticcase=form.justification_realisticcase.data,
            )
            db.session.add(consequence)
        db.session.commit()
        flash(
            _("Added %(count)d consequence entries.", count=len(categories)),
            "success",
        )
        if return_to:
            return redirect(return_to)
        return redirect(url_for("bia.view_consequences", component_id=component.id))
    return render_template(
        "bia/manage_component_consequence.html",
        component=component,
        form=form,
        return_to=return_to,
    )


@bp.route("/get_component/<int:component_id>")
@login_required
def get_component(component_id: int):
    component = Component.query.get_or_404(component_id)
    return jsonify(
        {
            "id": component.id,
            "name": component.name,
            "info_type": component.info_type,
            "info_owner": component.info_owner,
            "user_type": component.user_type,
            "description": component.description,
            "process_dependencies": component.process_dependencies,
            "bia_name": component.context_scope.name if component.context_scope else None,
            "consequences_count": len(component.consequences),
            "authentication_method_id": component.authentication_method_id,
            "authentication_method_label": _describe_authentication(component),
            "authentication_method_slug": component.authentication_method.slug if component.authentication_method else None,
            "environments": _serialize_environments(component),
        }
    )


@bp.route("/add_consequence/<int:component_id>", methods=["POST"])
@login_required
def add_consequence(component_id: int):
    component = Component.query.get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    data = request.get_json() or {}
    form = ConsequenceForm(data=data)
    if form.validate():
        categories = data.get("consequence_category") or []
        if not isinstance(categories, list):
            categories = [categories]
        for category in categories:
            consequence = Consequences(
                component=component,
                consequence_category=category,
                security_property=form.security_property.data,
                consequence_worstcase=form.consequence_worstcase.data,
                justification_worstcase=form.justification_worstcase.data,
                consequence_realisticcase=form.consequence_realisticcase.data,
                justification_realisticcase=form.justification_realisticcase.data,
            )
            db.session.add(consequence)
        db.session.commit()
        return jsonify({"success": True, "message": f"{len(categories)} consequences added."})
    return jsonify({"success": False, "errors": form.errors}), 400


@bp.route("/get_consequence/<int:consequence_id>")
@login_required
def get_consequence(consequence_id: int):
    consequence = Consequences.query.get_or_404(consequence_id)
    return jsonify(
        {
            "id": consequence.id,
            "consequence_category": consequence.consequence_category,
            "security_property": consequence.security_property,
            "consequence_worstcase": consequence.consequence_worstcase,
            "justification_worstcase": consequence.justification_worstcase,
            "consequence_realisticcase": consequence.consequence_realisticcase,
            "justification_realisticcase": consequence.justification_realisticcase,
        }
    )


@bp.route("/edit_consequence/<int:consequence_id>", methods=["POST"])
@login_required
def edit_consequence(consequence_id: int):
    consequence = Consequences.query.get_or_404(consequence_id)
    if not _can_edit_context(consequence.component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    data = request.get_json() or {}
    required = [
        "consequence_category",
        "security_property",
        "consequence_worstcase",
        "consequence_realisticcase",
    ]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({"success": False, "errors": {field: ["This field is required."] for field in missing}}), 400
    consequence.consequence_category = data.get("consequence_category")
    consequence.security_property = data.get("security_property")
    consequence.consequence_worstcase = data.get("consequence_worstcase")
    consequence.justification_worstcase = data.get("justification_worstcase")
    consequence.consequence_realisticcase = data.get("consequence_realisticcase")
    consequence.justification_realisticcase = data.get("justification_realisticcase")
    db.session.commit()
    return jsonify({"success": True, "message": "Consequence updated."})


@bp.route("/delete_consequence/<int:consequence_id>", methods=["POST"])
@login_required
def delete_consequence(consequence_id: int):
    consequence = Consequences.query.get_or_404(consequence_id)
    if not _can_edit_context(consequence.component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    db.session.delete(consequence)
    db.session.commit()
    return jsonify({"success": True, "message": "Consequence deleted."})


@bp.route("/consequences/<int:component_id>")
@login_required
def view_consequences(component_id: int):
    component = Component.query.get_or_404(component_id)
    consequences = Consequences.query.filter_by(component_id=component.id).all()
    consequence_form = ConsequenceForm()
    return render_template(
        "bia/view_consequences.html",
        component=component,
        consequences=consequences,
        consequence_form=consequence_form,
    )


@bp.route("/get_availability/<int:component_id>")
@login_required
def get_availability(component_id: int):
    availability = AvailabilityRequirements.query.filter_by(component_id=component_id).first()
    if not availability:
        return jsonify({})
    return jsonify(
        {
            "mtd": availability.mtd,
            "rto": availability.rto,
            "rpo": availability.rpo,
            "masl": availability.masl,
        }
    )


@bp.route("/update_availability/<int:component_id>", methods=["POST"])
@login_required
def update_availability(component_id: int):
    component = Component.query.get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    form = AvailabilityForm()
    if not form.validate_on_submit():
        return jsonify({"success": False, "errors": form.errors}), 400
    availability = AvailabilityRequirements.query.filter_by(component_id=component_id).first()
    if availability is None:
        availability = AvailabilityRequirements(component=component)
        db.session.add(availability)
    else:
        availability.component = component
    availability.mtd = form.mtd.data
    availability.rto = form.rto.data
    availability.rpo = form.rpo.data
    availability.masl = form.masl.data
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/add_ai_identification/<int:component_id>", methods=["POST"])
@login_required
def add_ai_identification(component_id: int):
    component = Component.query.get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    existing = AIIdentificatie.query.filter_by(component_id=component.id).first()
    if existing:
        existing.category = request.form.get("category") or existing.category
        existing.motivatie = request.form.get("motivatie")
    else:
        ai_record = AIIdentificatie(
            component=component,
            category=request.form.get("category") or "No AI",
            motivatie=request.form.get("motivatie"),
        )
        db.session.add(ai_record)
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/update_ai_identification/<int:component_id>", methods=["POST"])
@login_required
def update_ai_identification(component_id: int):
    component = Component.query.get_or_404(component_id)
    if not _can_edit_context(component.context_scope):
        return (
            jsonify({"success": False, "errors": {"permission": ["You are not allowed to modify this BIA."]}}),
            403,
        )
    ai_record = AIIdentificatie.query.filter_by(component_id=component.id).first()
    if ai_record is None:
        ai_record = AIIdentificatie(component=component)
        db.session.add(ai_record)
    ai_record.category = request.form.get("category") or ai_record.category
    ai_record.motivatie = request.form.get("motivatie")
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/get_ai_identification/<int:component_id>")
@login_required
def get_ai_identification(component_id: int):
    ai_record = AIIdentificatie.query.filter_by(component_id=component_id).first()
    if not ai_record:
        return jsonify({"exists": False, "category": "No AI", "motivatie": ""}), 404
    return jsonify(
        {
            "exists": True,
            "category": ai_record.category,
            "motivatie": ai_record.motivatie,
        }
    )


@bp.route("/item/<int:item_id>/summary", methods=["GET", "POST"])
@login_required
def manage_summary(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if not _can_edit_context(item):
        abort(403)
    form = SummaryForm(obj=item.summary)
    if form.validate_on_submit():
        if item.summary:
            item.summary.content = form.content.data
        else:
            db.session.add(Summary(content=form.content.data, context_scope=item))
        db.session.commit()
        flash(_("bia.flash.summary_updated"), "success")
        return redirect(url_for("bia.view_item", item_id=item.id))
    return render_template("bia/manage_summary.html", form=form, item=item)


@bp.route("/item/<int:item_id>/summary/delete", methods=["POST"])
@login_required
def delete_summary(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if not _can_edit_context(item):
        abort(403)
    if item.summary:
        db.session.delete(item.summary)
        db.session.commit()
        flash(_("bia.flash.summary_deleted"), "success")
    return redirect(url_for("bia.view_item", item_id=item.id))


@bp.route("/item/<int:item_id>/export")
@login_required
def export_item(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    consequences = [consequence for component in item.components for consequence in component.consequences]
    max_cia_impact = get_max_cia_impact(consequences)
    ai_identifications = _collect_ai_identifications(item)
    css_path = Path(current_app.root_path) / "static" / "css" / "app.css"
    export_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    html_content = render_template(
        "bia/context_detail.html",
        item=item,
        consequences=consequences,
        max_cia_impact=max_cia_impact,
        ai_identifications=ai_identifications,
        can_edit_context=_can_edit_context(item),
        export_mode=True,
        export_css=export_css,
    )

    safe_name = _safe_filename(item.name)
    filename = f"BIA_{safe_name}.html"
    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(html_content, encoding="utf-8")
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/export_csv/<int:item_id>")
@login_required
def export_csv(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if item.author and item.author != current_user:
        abort(403)
    export_folder = ensure_export_folder() / _safe_filename(item.name)
    export_folder.mkdir(parents=True, exist_ok=True)
    csv_files = export_to_csv(item)
    exported_files = []
    for filename, content in csv_files.items():
        path = export_folder / filename
        path.write_text(content, encoding="utf-8")
        exported_files.append(
            {
                "filename": filename,
                "path": export_folder.name,
                "size": len(content.encode("utf-8")),
            }
        )
    flash(_("bia.flash.csv_export_created"), "success")
    return render_template(
        "bia/csv_export_overview.html",
        item=item,
        exported_files=exported_files,
        export_folder=export_folder.name,
    )


@bp.route("/download_csv/<path:folder>/<path:filename>")
@login_required
def download_csv_file(folder: str, filename: str):
    export_folder = ensure_export_folder() / folder
    file_path = export_folder / filename
    if not file_path.exists():
        flash(_("bia.flash.file_not_found"), "danger")
        return redirect(url_for("bia.dashboard"))
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/import_csv", methods=["GET", "POST"])
@login_required
def import_csv_view():
    form = ImportCSVForm()
    if request.method == "POST":
        csv_files: dict[str, str] = {}
        file_mapping = {
            "bia": form.bia,
            "components": form.components,
            "consequences": form.consequences,
            "availability_requirements": form.availability_requirements,
            "ai_identification": form.ai_identification,
            "summary": form.summary,
        }
        try:
            for key, field in file_mapping.items():
                uploaded = request.files.get(field.name) if field.name in request.files else None
                if uploaded and uploaded.filename:
                    csv_files[key] = uploaded.read().decode("utf-8")
            if "bia" not in csv_files:
                flash(_("bia.flash.csv_required"), "danger")
                return redirect(request.url)
            import_from_csv(csv_files)
            flash(_("bia.flash.csv_import_success"), "success")
            return redirect(url_for("bia.dashboard"))
        except Exception as exc:  # pragma: no cover - surface errors to UI
            logging.exception("CSV import failed")
            flash(_("bia.flash.csv_import_failed", details=exc), "danger")
    return render_template("bia/import_csv.html", form=form)


@bp.route("/change_password", methods=["GET", "POST"])
@login_required
@require_fresh_login(max_age_minutes=15)
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash(_("bia.flash.password_updated"), "success")
            return redirect(url_for("bia.dashboard"))
        flash(_("bia.flash.current_password_invalid"), "danger")
    return render_template("bia/change_password.html", form=form)


@bp.route("/export_data_inventory")
@login_required
def export_data_inventory():
    """Export an inventory of all components and their BIA context as CSV.

    This mirrors the legacy behaviour: build a small CSV with BIA, component,
    information type, owner and administrator and return the generated file.
    """

    components = (
        Component.query.options(
            joinedload(Component.context_scope),
            joinedload(Component.authentication_method),
            joinedload(Component.environments).joinedload(ComponentEnvironment.authentication_method),
        )
        .join(ContextScope)
        .all()
    )
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    # Use friendly headers similar to the legacy exporter
    writer.writerow(["BIA", "Systeem", "Informatie", "Eigenaar", "Authenticatie", "Beheer"])
    for component in components:
        authentication_label = _describe_authentication(component) or "N/A"
        writer.writerow(
            [
                component.context_scope.name if component.context_scope else "",
                component.name,
                component.info_type or "N/A",
                component.info_owner or "N/A",
                authentication_label,
                component.context_scope.technical_administrator if component.context_scope else "N/A",
            ]
        )
    filename = f"Data_Inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(csv_buffer.getvalue(), encoding="utf-8")
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/export_authentication_overview")
@login_required
def export_authentication_overview():
    components = (
        Component.query.options(
            joinedload(Component.context_scope),
            joinedload(Component.authentication_method),
            joinedload(Component.environments).joinedload(ComponentEnvironment.authentication_method),
        )
        .order_by(Component.name.asc())
        .all()
    )

    options = list_authentication_options(active_only=False)
    option_map = {option.id: option for option in options}
    grouped: defaultdict[int, list[Component]] = defaultdict(list)
    unassigned: list[Component] = []

    for component in components:
        method_id = _resolve_component_authentication_method_id(component)
        option = option_map.get(method_id or 0)
        if option is None:
            unassigned.append(component)
            continue
        grouped[option.id].append(component)

    def _sort_key(component: Component) -> tuple[str, str]:
        context_name = component.context_scope.name if component.context_scope else ""
        return (context_name.lower(), component.name.lower())

    groups = [
        {
            "option": option_map[method_id],
            "components": sorted(components_list, key=_sort_key),
        }
        for method_id, components_list in grouped.items()
        if components_list
    ]

    groups.sort(key=lambda entry: entry["option"].label(get_locale()).lower())
    unassigned.sort(key=_sort_key)

    html_content = render_template(
        "bia/export_authentication.html",
        groups=groups,
        unassigned=unassigned,
        generated_at=datetime.now(),
    )

    filename = f"Authentication_Overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(html_content, encoding="utf-8")
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/export_all_consequences")
@login_required
def export_all_consequences():
    export_type = request.args.get("type", "detailed")
    bias = ContextScope.query.all()
    # Summary export: produce a compact per-BIA summary of counts and max impacts
    if export_type == "summary":
        summaries = []
        for bia in bias:
            consequences = [consequence for component in bia.components for consequence in component.consequences]
            if not consequences:
                continue
            # Only include BIAs that actually have components and consequences
            if len(bia.components) == 0 or len(consequences) == 0:
                continue
            summaries.append(
                {
                    "bia": bia,
                    "component_count": len(bia.components),
                    "consequence_count": len(consequences),
                    "max_impacts": _summary_impacts(consequences),
                }
            )
        html_content = render_template(
            "bia/export_consequences_summary.html",
            bia_summaries=summaries,
            generated_at=datetime.now(),
        )
        filename = f"CIA_Consequences_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    else:
        # Detailed export: list every consequence with its parent BIA and component
        all_consequences = []
        for bia in bias:
            for component in bia.components:
                for consequence in component.consequences:
                    all_consequences.append(
                        {
                            "bia": bia,
                            "component": component,
                            "consequence": consequence,
                        }
                    )
        html_content = render_template(
            "bia/export_all_consequences.html",
            consequences=all_consequences,
            generated_at=datetime.now(),
        )
        filename = f"All_CIA_Consequences_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(html_content, encoding="utf-8")
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/debug/consequences")
@login_required
def debug_consequences():
    payload = []
    for bia in ContextScope.query.all():
        entry = {
            "bia_name": bia.name,
            "bia_id": bia.id,
            "components": [],
        }
        for component in bia.components:
            comp_data = {
                "component_name": component.name,
                "component_id": component.id,
                "consequences": [],
            }
            for consequence in component.consequences:
                comp_data["consequences"].append(
                    {
                        "security_property": consequence.security_property,
                        "worstcase": consequence.consequence_worstcase,
                        "realistic": consequence.consequence_realisticcase,
                        "category": consequence.consequence_category,
                    }
                )
            entry["components"].append(comp_data)
        payload.append(entry)
    return jsonify(payload)


@bp.route("/bia/<int:item_id>/export/sql")
@login_required
def export_bia_sql(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    try:
        sql_text = export_to_sql(item)
        filename = f"BIA_Export_{_safe_filename(item.name)}_{datetime.now().strftime('%Y%m%d')}.sql"
        export_folder = ensure_export_folder()
        file_path = export_folder / filename
        file_path.write_text(sql_text, encoding="utf-8")
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as exc:  # pragma: no cover - IO failures are surfaced to users
        logging.exception("SQL export failed")
        flash(_("bia.flash.sql_export_failed", details=exc), "danger")
        return redirect(url_for("bia.view_item", item_id=item.id))


@bp.route("/import-sql", methods=["GET", "POST"])
@login_required
def import_sql_form():
    form = ImportSQLForm()
    if form.validate_on_submit():
        try:
            import_sql_file(form.sql_file.data)
            flash(_("bia.flash.sql_import_success"), "success")
            return redirect(url_for("bia.dashboard"))
        except (ValueError, PermissionError) as exc:
            flash(str(exc), "danger")
        except Exception:  # pragma: no cover - defensive logging
            logging.exception("SQL import failed")
            flash(_("bia.flash.sql_import_unexpected"), "danger")
    return render_template("bia/import_sql_form.html", form=form)


def _apply_context_form(
    form: ContextScopeForm,
    context: ContextScope,
    *,
    allow_owner_assignment: bool = True,
) -> None:
    context.name = form.name.data
    if allow_owner_assignment:
        context.responsible = form.responsible.data
    context.coordinator = form.coordinator.data
    context.start_date = form.start_date.data
    context.end_date = form.end_date.data
    context.service_description = form.service_description.data
    context.knowledge = form.knowledge.data
    context.interfaces = form.interfaces.data
    context.mission_critical = form.mission_critical.data
    context.support_contracts = form.support_contracts.data
    context.security_supplier = form.security_supplier.data
    context.user_amount = form.user_amount.data
    context.scope_description = form.scope_description.data
    context.risk_assessment_human = bool(form.risk_assessment_human.data)
    context.risk_assessment_process = bool(form.risk_assessment_process.data)
    context.risk_assessment_technological = bool(form.risk_assessment_technological.data)
    context.ai_model = bool(form.ai_model.data)
    context.project_leader = form.project_leader.data
    context.risk_owner = form.risk_owner.data
    context.product_owner = form.product_owner.data
    context.technical_administrator = form.technical_administrator.data
    context.security_manager = form.security_manager.data
    context.incident_contact = form.incident_contact.data
    if context.author:
        context.responsible = context.author.full_name


def _collect_ai_identifications(context: ContextScope) -> dict[int, AIIdentificatie]:
    ai_map: dict[int, AIIdentificatie] = {}
    for component in context.components:
        ai_record = AIIdentificatie.query.filter_by(component_id=component.id).first()
        if ai_record and ai_record.category != "No AI":
            ai_map[component.id] = ai_record
    return ai_map


def _summary_impacts(consequences: list[Consequences]):
    summary = {
        "confidentiality": {"worstcase": None, "realistic": None},
        "integrity": {"worstcase": None, "realistic": None},
        "availability": {"worstcase": None, "realistic": None},
    }
    for consequence in consequences:
        prop = (consequence.security_property or "").strip().lower()
        if prop not in summary:
            continue
        worst = consequence.consequence_worstcase
        realistic = consequence.consequence_realisticcase
        if worst and (
            summary[prop]["worstcase"] is None
            or get_impact_level(worst) > get_impact_level(summary[prop]["worstcase"])
        ):
            summary[prop]["worstcase"] = worst
        if realistic and (
            summary[prop]["realistic"] is None
            or get_impact_level(realistic) > get_impact_level(summary[prop]["realistic"])
        ):
            summary[prop]["realistic"] = realistic
    return summary


def _resolve_user() -> User | None:
    return current_user if isinstance(current_user, User) else None


def _safe_filename(value: str | None) -> str:
    if not value:
        return "bia"
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-", " "}).strip()
    return cleaned.replace(" ", "_") or "bia"
