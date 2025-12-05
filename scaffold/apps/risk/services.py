"""Helper utilities for risk management workflows."""

from __future__ import annotations

import enum
from datetime import date
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlparse

import sqlalchemy as sa

from ...core.i18n import gettext as _
from ...extensions import db
from ..bia.models import Component, ContextScope
from ..csa.models import Control
from ..identity.models import User
from .models import (
    CHANCE_WEIGHTS,
    IMPACT_WEIGHTS,
    Risk,
    RiskImpact,
    RiskImpactArea,
    RiskImpactAreaLink,
    RiskChance,
    RiskSeverity,
    RiskSeverityThreshold,
    RiskTreatmentOption,
)


def eligible_component_query() -> sa.orm.Query:
    """Return the base query for components that allow risk tracking."""

    return Component.query.join(ContextScope).filter(
        sa.or_(
            ContextScope.risk_assessment_human.is_(True),
            ContextScope.risk_assessment_process.is_(True),
            ContextScope.risk_assessment_technological.is_(True),
        )
    )


def list_eligible_components() -> list[Component]:
    """Return eligible components ordered by context and component name."""

    return (
        eligible_component_query()
        .order_by(ContextScope.name.asc(), Component.name.asc())
        .options(sa.orm.joinedload(Component.context_scope))
        .all()
    )


def validate_component_ids(component_ids: Iterable[int]) -> list[Component]:
    """Ensure the provided component ids refer to eligible components."""

    ids = {int(component_id) for component_id in component_ids if component_id is not None}
    if not ids:
        return []

    components = (
        eligible_component_query()
        .filter(Component.id.in_(ids))
        .options(sa.orm.joinedload(Component.context_scope))
        .all()
    )
    found_ids = {component.id for component in components}
    missing = ids - found_ids
    if missing:
        raise ValueError(f"Non-eligible component ids supplied: {sorted(missing)}")
    return components


def validate_control_ids(control_ids: Iterable[int | str]) -> list[Control]:
    """Ensure the provided CSA control ids exist and preserve selection order."""

    ids: list[int] = []
    seen: set[int] = set()
    for raw_value in control_ids:
        if raw_value in (None, ""):
            continue
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Control ids must be integers.") from exc
        if value in seen:
            continue
        seen.add(value)
        ids.append(value)
    if not ids:
        return []

    controls = Control.query.filter(Control.id.in_(ids)).all()
    found_ids = {control.id for control in controls}
    missing = set(ids) - found_ids
    if missing:
        raise ValueError(f"Unknown control ids supplied: {sorted(missing)}")

    control_lookup = {control.id: control for control in controls}
    return [control_lookup[control_id] for control_id in ids]


def component_choice_label(component: Component) -> str:
    """Build a display label combining context and component names."""

    scope_name = component.context_scope.name if component.context_scope else "?"
    return f"{scope_name} - {component.name}"


def component_choices() -> list[tuple[str, str]]:
    """Return WTForms choices for eligible components."""

    return [(str(component.id), component_choice_label(component)) for component in list_eligible_components()]


def control_choices(include_blank: bool = True) -> list[tuple[str, str]]:
    """Return CSA control select options sorted by domain."""

    query = Control.query.order_by(Control.domain.asc())
    choices: list[tuple[str, str]] = []
    if include_blank:
        choices.append(("", "---"))
    choices.extend([(str(control.id), f"{control.domain}") for control in query])
    return choices


def treatment_owner_choices(include_blank: bool = True) -> list[tuple[str, str]]:
    """Return selectable treatment owners."""

    query = User.query.order_by(User.last_name.asc(), User.first_name.asc())
    choices: list[tuple[str, str]] = []
    if include_blank:
        choices.append(("", "---"))
    choices.extend([(str(user.id), f"{user.full_name or user.email}") for user in query])
    return choices


_IMPACT_LABEL_KEYS = {
    RiskImpact.INSIGNIFICANT: "risk.impact.insignificant",
    RiskImpact.MINOR: "risk.impact.minor",
    RiskImpact.MODERATE: "risk.impact.moderate",
    RiskImpact.MAJOR: "risk.impact.major",
    RiskImpact.CATASTROPHIC: "risk.impact.catastrophic",
}


def impact_choices() -> list[tuple[str, str]]:
    """Return impact options aligned with the BIA consequence terminology."""

    return [
        (impact.value, _(_IMPACT_LABEL_KEYS[impact]))
        for impact in RiskImpact
    ]


def chance_choices() -> list[tuple[str, str]]:
    """Return localised likelihood options."""

    label_keys = {
        RiskChance.RARE: "risk.chance.rare",
        RiskChance.UNLIKELY: "risk.chance.unlikely",
        RiskChance.POSSIBLE: "risk.chance.possible",
        RiskChance.LIKELY: "risk.chance.likely",
        RiskChance.ALMOST_CERTAIN: "risk.chance.almost_certain",
    }
    return [(chance.value, _(label_keys[chance])) for chance in RiskChance]


def impact_area_choices() -> list[tuple[str, str]]:
    return [
        (area.value, _(f"risk.impact_area.{area.value}"))
        for area in RiskImpactArea
    ]


def treatment_choices() -> list[tuple[str, str]]:
    return [
        (option.value, _(f"risk.treatment.{option.value}"))
        for option in RiskTreatmentOption
    ]


def load_thresholds() -> list[RiskSeverityThreshold]:
    return RiskSeverityThreshold.query.order_by(RiskSeverityThreshold.min_score.asc()).all()


def determine_severity(score: int, thresholds: Sequence[RiskSeverityThreshold] | None = None) -> RiskSeverity | None:
    """Return the severity entry matching the provided score."""

    resolved = thresholds or load_thresholds()
    for threshold in resolved:
        if threshold.min_score <= score <= threshold.max_score:
            return threshold.severity
    return None


def configure_risk_form(
    form,
    *,
    extra_components: list[Component] | None = None,
    ineligible_suffix: str | None = None,
) -> None:
    form.impact.choices = impact_choices()
    form.chance.choices = chance_choices()
    form.impact_areas.choices = impact_area_choices()
    form.component_ids.choices = component_choices()
    form.treatment.choices = treatment_choices()
    form.treatment_owner_id.choices = treatment_owner_choices()
    if hasattr(form, "csa_control_ids"):
        form.csa_control_ids.choices = control_choices(include_blank=False)

    if extra_components:
        existing_ids = {choice[0] for choice in form.component_ids.choices}
        suffix = ineligible_suffix or _("admin.risks.form.ineligible_suffix")
        for component in extra_components:
            cid = str(component.id)
            if cid in existing_ids:
                continue
            label = f"{component_choice_label(component)} ({suffix})"
            form.component_ids.choices.append((cid, label))


def set_impact_areas(risk: Risk, area_values: list[str]) -> None:
    selected: set[RiskImpactArea] = set()
    for raw_value in area_values:
        if not raw_value:
            continue
        try:
            selected.add(RiskImpactArea(raw_value))
        except ValueError:
            continue

    desired = sorted(selected, key=lambda entry: entry.value)
    desired_set = set(desired)

    # Remove stale links first to avoid unique constraint violations when re-adding
    for link in list(risk.impact_area_links):
        if link.area not in desired_set:
            risk.impact_area_links.remove(link)

    existing_values = {link.area for link in risk.impact_area_links}
    for area in desired:
        if area in existing_values:
            continue
        risk.impact_area_links.append(RiskImpactAreaLink(area=area))


def optional_int(value: str | None) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def thresholds_overlap(thresholds: list[RiskSeverityThreshold]) -> bool:
    ordered = sorted(thresholds, key=lambda entry: entry.min_score)
    previous_max: int | None = None
    for entry in ordered:
        if previous_max is not None and entry.min_score <= previous_max:
            return True
        previous_max = entry.max_score
    return False


_IMPACT_WEIGHT_INDEX = {weight: impact for impact, weight in IMPACT_WEIGHTS.items()}
_CHANCE_WEIGHT_INDEX = {weight: chance for chance, weight in CHANCE_WEIGHTS.items()}


class RiskValidationError(ValueError):
    """Raised when API payloads fail validation."""

    def __init__(self, errors: dict[str, list[str]]) -> None:
        super().__init__("Risk payload validation failed")
        self.errors = errors


def apply_payload_to_risk(risk: Risk, payload: Mapping[str, object] | None) -> None:
    """Validate and transfer API payload data onto a risk instance."""

    if payload is None:
        raise RiskValidationError({"payload": ["JSON body is required."]})

    errors: dict[str, list[str]] = {}

    def add_error(field: str, message: str) -> None:
        errors.setdefault(field, []).append(message)

    title = _coerce_string(payload.get("title"))
    if not title:
        add_error("title", "Title is required.")
    elif len(title) > 255:
        add_error("title", "Title cannot exceed 255 characters.")

    description = _coerce_string(payload.get("description"))
    if not description:
        add_error("description", "Description is required.")

    impact = _coerce_weighted_enum(payload.get("impact"), "impact", RiskImpact, _IMPACT_WEIGHT_INDEX, add_error)
    chance = _coerce_weighted_enum(payload.get("chance"), "chance", RiskChance, _CHANCE_WEIGHT_INDEX, add_error)
    treatment = _coerce_treatment(payload.get("treatment"), add_error)

    component_ids = _coerce_id_list(payload.get("component_ids"), "component_ids", add_error)
    components: list[Component] = []
    if component_ids:
        try:
            components = validate_component_ids(component_ids)
        except ValueError as exc:
            add_error("component_ids", str(exc))
    else:
        add_error("component_ids", "Select at least one component.")

    impact_areas = _coerce_impact_areas(payload.get("impact_areas"), add_error)

    discovered_on = _parse_date(payload.get("discovered_on"), "discovered_on", add_error)
    treatment_due_date = _parse_date(payload.get("treatment_due_date"), "treatment_due_date", add_error)

    owner = _resolve_user(payload.get("treatment_owner_id"), add_error)
    controls = _resolve_controls(
        payload.get("csa_control_ids"),
        legacy_value=payload.get("csa_control_id"),
        add_error=add_error,
    )
    if treatment == RiskTreatmentOption.MITIGATE and not controls:
        add_error("csa_control_ids", "Mitigation treatment requires at least one CSA control.")
    ticket_url = _coerce_url(payload.get("ticket_url"), "ticket_url", add_error)

    if errors:
        raise RiskValidationError(errors)

    risk.title = title or risk.title
    risk.description = description or risk.description
    if discovered_on is not None:
        risk.discovered_on = discovered_on
    elif risk.discovered_on is None:
        risk.discovered_on = date.today()

    risk.impact = impact or risk.impact
    risk.chance = chance or risk.chance
    risk.treatment = treatment or risk.treatment
    plan = _coerce_string(payload.get("treatment_plan"))
    risk.treatment_plan = plan or None
    risk.treatment_due_date = treatment_due_date
    risk.treatment_owner = owner
    risk.controls = controls
    risk.ticket_url = ticket_url
    risk.components = components
    risk.impact_area_links = [
        RiskImpactAreaLink(area=area)
        for area in sorted(impact_areas, key=lambda entry: entry.value)
    ]


def serialize_risk(risk: Risk, thresholds: Sequence[RiskSeverityThreshold] | None = None) -> dict[str, object]:
    """Return a JSON-ready representation of a risk with derived fields."""

    thresholds = thresholds or load_thresholds()
    score = risk.score()
    severity = determine_severity(score, thresholds)
    components = [
        {
            "id": component.id,
            "name": component.name,
            "context": component.context_scope.name if component.context_scope else None,
        }
        for component in sorted(risk.components, key=lambda item: (item.name or "").lower())
    ]
    impact_areas = [
        link.area.value
        for link in sorted(risk.impact_area_links, key=lambda entry: entry.area.value)
    ]
    controls: list[dict[str, object]] = []
    for control in sorted(
        risk.controls,
        key=lambda entry: (
            (entry.domain or ""),
            (entry.section or ""),
        ),
    ):
        serialized_control = _serialize_control(control)
        if serialized_control is None:
            continue
        controls.append(serialized_control)
    return {
        "id": risk.id,
        "title": risk.title,
        "description": risk.description,
        "discovered_on": risk.discovered_on.isoformat() if risk.discovered_on else None,
        "impact": {
            "value": risk.impact.value,
            "weight": IMPACT_WEIGHTS[risk.impact],
        },
        "chance": {
            "value": risk.chance.value,
            "weight": CHANCE_WEIGHTS[risk.chance],
        },
        "score": score,
        "severity": severity.value if severity else None,
        "treatment": risk.treatment.value,
        "treatment_plan": risk.treatment_plan,
        "treatment_due_date": risk.treatment_due_date.isoformat() if risk.treatment_due_date else None,
        "treatment_owner": _serialize_owner(risk.treatment_owner),
        "component_ids": [component["id"] for component in components],
        "components": components,
        "impact_areas": impact_areas,
        "controls": controls,
        "control_ids": [control["id"] for control in controls if control.get("id") is not None],
        "control": controls[0] if controls else None,
        "ticket_url": risk.ticket_url,
        "closed_at": risk.closed_at.isoformat() if getattr(risk, "closed_at", None) else None,
        "created_at": risk.created_at.isoformat() if getattr(risk, "created_at", None) else None,
        "updated_at": risk.updated_at.isoformat() if getattr(risk, "updated_at", None) else None,
    }


def _coerce_string(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_weighted_enum(
    raw_value: object | None,
    field: str,
    enum_cls,
    weight_map: Mapping[int, enum.Enum],
    add_error,
):
    if raw_value is None:
        add_error(field, f"{field.replace('_', ' ').title()} is required.")
        return None
    if isinstance(raw_value, str):
        stripped = raw_value.strip().lower()
        if not stripped:
            add_error(field, f"{field.replace('_', ' ').title()} is required.")
            return None
        if stripped.isdigit():
            raw_value = int(stripped)
        else:
            try:
                return enum_cls(stripped)
            except ValueError:
                add_error(field, f"Unknown {field.replace('_', ' ')} '{raw_value}'.")
                return None
    if isinstance(raw_value, (int, float)):
        candidate = weight_map.get(int(raw_value))
        if candidate is None:
            add_error(field, f"{field.replace('_', ' ').title()} must be between 1 and 5.")
            return None
        return candidate
    add_error(field, f"{field.replace('_', ' ').title()} must be a numeric weight or enum value.")
    return None


def _coerce_url(raw_value: object | None, field: str, add_error):
    value = _coerce_string(raw_value)
    if not value:
        return None
    if len(value) > 500:
        add_error(field, "URL exceeds maximum length of 500 characters.")
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        add_error(field, "Provide a valid HTTP or HTTPS URL.")
        return None
    return value


def _coerce_treatment(raw_value: object | None, add_error):
    if raw_value is None:
        add_error("treatment", "Treatment is required.")
        return None
    if isinstance(raw_value, str):
        stripped = raw_value.strip().lower()
        if not stripped:
            add_error("treatment", "Treatment is required.")
            return None
        try:
            return RiskTreatmentOption(stripped)
        except ValueError:
            add_error("treatment", f"Unknown treatment '{raw_value}'.")
            return None
    add_error("treatment", "Treatment must be provided as a string value.")
    return None


def _coerce_id_list(raw_value: object | None, field: str, add_error) -> list[int]:
    if raw_value is None:
        return []
    if not isinstance(raw_value, (list, tuple, set)):
        add_error(field, "Provide a list of identifiers.")
        return []
    result: list[int] = []
    seen: set[int] = set()
    for entry in raw_value:
        try:
            value = int(entry)
        except (TypeError, ValueError):
            add_error(field, f"'{entry}' is not a valid integer.")
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _coerce_impact_areas(raw_value: object | None, add_error) -> list[RiskImpactArea]:
    if raw_value is None:
        add_error("impact_areas", "Provide at least one impact area.")
        return []
    if not isinstance(raw_value, (list, tuple, set)):
        add_error("impact_areas", "Provide at least one impact area.")
        return []
    resolved: list[RiskImpactArea] = []
    seen: set[RiskImpactArea] = set()
    for entry in raw_value:
        candidate = _coerce_string(entry).lower()
        if not candidate:
            continue
        try:
            area = RiskImpactArea(candidate)
        except ValueError:
            add_error("impact_areas", f"Unknown impact area '{entry}'.")
            continue
        if area in seen:
            continue
        seen.add(area)
        resolved.append(area)
    if not resolved:
        add_error("impact_areas", "Provide at least one impact area.")
    return resolved


def _parse_date(raw_value: object | None, field: str, add_error) -> date | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, date):
        return raw_value
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            return None
        try:
            return date.fromisoformat(stripped)
        except ValueError:
            add_error(field, "Dates must use the YYYY-MM-DD format.")
            return None
    add_error(field, "Dates must use the YYYY-MM-DD format.")
    return None


def _resolve_user(raw_value: object | None, add_error) -> User | None:
    if raw_value in (None, ""):
        return None
    text_value = str(raw_value).strip()
    if not text_value:
        return None
    try:
        user_id = int(text_value)
    except (TypeError, ValueError):
        add_error("treatment_owner_id", "Owner id must be an integer.")
        return None
    owner = db.session.get(User, user_id)
    if owner is None:
        add_error("treatment_owner_id", "Unknown user selected as owner.")
    return owner


def _resolve_controls(raw_value: object | None, *, legacy_value: object | None, add_error) -> list[Control]:
    controls: list[Control] = []
    if isinstance(raw_value, (list, tuple, set)):
        try:
            controls = validate_control_ids(raw_value)
        except ValueError as exc:
            add_error("csa_control_ids", str(exc))
    elif raw_value not in (None, ""):
        add_error("csa_control_ids", "Provide CSA controls as a list of identifiers.")

    if not controls and legacy_value not in (None, ""):
        control = _resolve_control(legacy_value, add_error)
        if control:
            controls = [control]
    return controls


def _resolve_control(raw_value: object | None, add_error) -> Control | None:
    if raw_value in (None, ""):
        return None
    text_value = str(raw_value).strip()
    if not text_value:
        return None
    try:
        control_id = int(text_value)
    except (TypeError, ValueError):
        add_error("csa_control_id", "Control id must be an integer.")
        return None
    control = db.session.get(Control, control_id)
    if control is None:
        add_error("csa_control_id", "Unknown control selected.")
    return control


def _serialize_owner(user: User | None) -> dict[str, object] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
    }


def _serialize_control(control: Control | None) -> dict[str, object] | None:
    if control is None:
        return None
    return {
        "id": control.id,
        "domain": control.domain,
        "section": control.section,
        "description": control.description,
    }
