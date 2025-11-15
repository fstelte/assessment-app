"""Utilities supporting Business Impact Analysis data import/export."""

from __future__ import annotations

import csv
import io
import re
import shutil
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

from flask import current_app
from flask_login import current_user
from sqlalchemy import text

from ...extensions import db
from .models import (
    AIIdentificatie,
    AvailabilityRequirements,
    Component,
    Consequences,
    ContextScope,
    Summary,
)
from .services.authentication import AuthenticationOption, list_authentication_options, lookup_by_slug


MAX_SQL_FILE_SIZE = 2 * 1024 * 1024  # 2 MB guardrail matches legacy exporter

_IMPACT_LEVELS = {
    "very low": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "very high": 5,
    "insignificant": 1,
    "minor": 2,
    "moderate": 3,
    "major": 4,
    "catastrophic": 5,
}

_SQL_TABLE_ALIASES = {
    "context_scope": ContextScope.__table__.name,
    "component": Component.__table__.name,
    "consequences": Consequences.__table__.name,
    "availability_requirements": AvailabilityRequirements.__table__.name,
    "ai_identificatie": AIIdentificatie.__table__.name,
    "summary": Summary.__table__.name,
}

_SQL_ALLOWED_TABLES = set(_SQL_TABLE_ALIASES.values())

_SQL_COLUMN_WHITELIST = {
    ContextScope.__table__.name: {column.key for column in ContextScope.__table__.columns},
    Component.__table__.name: {column.key for column in Component.__table__.columns},
    Consequences.__table__.name: {column.key for column in Consequences.__table__.columns},
    AvailabilityRequirements.__table__.name: {column.key for column in AvailabilityRequirements.__table__.columns},
    AIIdentificatie.__table__.name: {column.key for column in AIIdentificatie.__table__.columns},
    Summary.__table__.name: {column.key for column in Summary.__table__.columns},
}

_SQL_COLUMN_ALIASES = {
    ContextScope.__table__.name: {
        "user_id": "author_id",
    }
}


def _filter_columns(table: str, row: dict[str, object | None]) -> dict[str, object | None]:
    """Drop legacy columns that no longer exist and normalise aliases."""

    allowed = _SQL_COLUMN_WHITELIST.get(table, set())
    aliases = _SQL_COLUMN_ALIASES.get(table, {})
    filtered: dict[str, object | None] = {}
    for key, value in row.items():
        target = aliases.get(key, key)
        if target in allowed:
            filtered[target] = value
    return filtered


def get_impact_level(impact: object | None) -> int:
    """Normalise impact labels or numeric strings into comparable integers."""

    if impact is None:
        return 0
    if isinstance(impact, (int, float)):
        return int(impact)
    text = str(impact).strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    return _IMPACT_LEVELS.get(text.lower(), 0)


def get_impact_color(impact: object | None) -> str:
    """Return the CSS class that corresponds with an impact label."""

    color_map = {
        1: "bg-green",
        2: "bg-yellow",
        3: "bg-orange",
        4: "bg-red",
        5: "bg-dark-red",
    }
    level = get_impact_level(impact)
    return color_map.get(level, "impact-unknown")


def get_cia_impact(
    consequences: Iterable[Consequences] | Consequences,
    security_property: str,
    case_type: str = "worstcase",
) -> str:
    """Return the highest impact registered for a CIA property."""

    if isinstance(consequences, Consequences):
        iterable: Iterable[Consequences] = [consequences]
    else:
        iterable = consequences

    target = security_property.strip().lower()
    case_key = "consequence_worstcase" if case_type == "worstcase" else "consequence_realisticcase"
    highest_level = 0
    highest_label = "Very Low"
    for consequence in iterable:
        if (consequence.security_property or "").strip().lower() != target:
            continue
        value = getattr(consequence, case_key)
        level = get_impact_level(value)
        if level > highest_level:
            highest_level = level
            highest_label = value or highest_label
    return highest_label


def get_max_cia_impact(consequences: Iterable[Consequences]) -> dict[str, str]:
    """Summarise the maximum realistic-case CIA impact across all consequences."""

    result: dict[str, str] = {
        "confidentiality": "Very Low",
        "integrity": "Very Low",
        "availability": "Very Low",
    }

    for consequence in consequences:
        prop = (consequence.security_property or "").strip().lower()
        if prop not in result:
            continue
        candidate = consequence.consequence_realisticcase or consequence.consequence_worstcase or "Very Low"
        if get_impact_level(candidate) > get_impact_level(result[prop]):
            result[prop] = candidate

    return result


def export_to_csv(context: ContextScope) -> dict[str, str]:
    """Return CSV payloads keyed by filename for a context scope."""

    prefix = _safe_slug(context.name) or "bia"
    exports: dict[str, str] = {}

    def stringify(value: object | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    # Context export
    context_buffer = io.StringIO()
    context_writer = csv.writer(context_buffer)
    context_writer.writerow(
        [
            "BIA Name",
            "BIA Responsible",
            "BIA Coordinator",
            "BIA Start Date",
            "BIA End Date",
            "BIA Last Update",
            "Service Description",
            "Knowledge",
            "Interfaces",
            "Mission Critical",
            "Support Contracts",
            "Security Supplier",
            "User Amount",
            "Scope Description",
            "Risk Assessment Human",
            "Risk Assessment Process",
            "Risk Assessment Technological",
            "AI Model",
            "Project Leader",
            "Risk Owner",
            "Product Owner",
            "Technical Administrator",
            "Security Manager",
            "Incident Contact",
        ]
    )
    context_writer.writerow(
        [
            stringify(context.name),
            stringify(context.responsible),
            stringify(context.coordinator),
            stringify(context.start_date),
            stringify(context.end_date),
            stringify(context.last_update),
            stringify(context.service_description),
            stringify(context.knowledge),
            stringify(context.interfaces),
            stringify(context.mission_critical),
            stringify(context.support_contracts),
            stringify(context.security_supplier),
            stringify(context.user_amount),
            stringify(context.scope_description),
            stringify(context.risk_assessment_human),
            stringify(context.risk_assessment_process),
            stringify(context.risk_assessment_technological),
            stringify(context.ai_model),
            stringify(context.project_leader),
            stringify(context.risk_owner),
            stringify(context.product_owner),
            stringify(context.technical_administrator),
            stringify(context.security_manager),
            stringify(context.incident_contact),
        ]
    )
    exports[f"{prefix}_bia.csv"] = context_buffer.getvalue()

    # Components
    components_buffer = io.StringIO()
    components_writer = csv.writer(components_buffer)
    authentication_options = {option.id: option for option in list_authentication_options(active_only=False)}

    components_writer.writerow(
        [
            "Component Name",
            "Type of Information",
            "Process Dependencies",
            "Information Owner",
            "Types of Users",
            "Authentication Slug",
            "Authentication Label (EN)",
            "Authentication Label (NL)",
            "Description of the Component",
            "Gerelateerd aan BIA",
        ]
    )
    for component in context.components:
        option = authentication_options.get(component.authentication_method_id)
        auth_slug = option.slug if option else ""
        auth_label_en = option.label_for_locale("en") if option else ""
        auth_label_nl = option.label_for_locale("nl") if option else ""
        components_writer.writerow(
            [
                stringify(component.name),
                stringify(component.info_type),
                stringify(component.process_dependencies),
                stringify(component.info_owner),
                stringify(component.user_type),
                stringify(auth_slug),
                stringify(auth_label_en),
                stringify(auth_label_nl),
                stringify(component.description),
                stringify(context.name),
            ]
        )
    exports[f"{prefix}_components.csv"] = components_buffer.getvalue()

    # Consequences
    consequences_buffer = io.StringIO()
    consequences_writer = csv.writer(consequences_buffer)
    consequences_writer.writerow(
        [
            "Gerelateerd aan BIA",
            "Gerelateerd aan Component",
            "Category of Consequence",
            "Property of Security",
            "Worstcase Consequence",
            "Justification for Worst Consequence",
            "Realistic Consequence",
            "Justification for Realistic Consequence",
        ]
    )
    for component in context.components:
        for consequence in component.consequences:
            consequences_writer.writerow(
                [
                    stringify(context.name),
                    stringify(component.name),
                    stringify(consequence.consequence_category),
                    stringify(consequence.security_property),
                    stringify(consequence.consequence_worstcase),
                    stringify(consequence.justification_worstcase),
                    stringify(consequence.consequence_realisticcase),
                    stringify(consequence.justification_realisticcase),
                ]
            )
    exports[f"{prefix}_consequences.csv"] = consequences_buffer.getvalue()

    # Availability requirements
    availability_buffer = io.StringIO()
    availability_writer = csv.writer(availability_buffer)
    availability_writer.writerow(
        [
            "Gerelateerd aan BIA",
            "Gerelateerd aan Component",
            "Maximum Tolerable Downtime",
            "Recovery Time Objective",
            "Recovery Point Objective",
            "Minimum Acceptable Service Level",
        ]
    )
    for component in context.components:
        availability = component.availability_requirement
        if not availability:
            continue
        availability_writer.writerow(
            [
                stringify(context.name),
                stringify(component.name),
                stringify(availability.mtd),
                stringify(availability.rto),
                stringify(availability.rpo),
                stringify(availability.masl),
            ]
        )
    exports[f"{prefix}_availability_requirements.csv"] = availability_buffer.getvalue()

    # AI identifications
    ai_buffer = io.StringIO()
    ai_writer = csv.writer(ai_buffer)
    ai_writer.writerow(["Gerelateerd aan BIA", "Gerelateerd aan Component", "AI Category", "AI Justification"])
    for component in context.components:
        for ai_record in component.ai_identificaties:
            ai_writer.writerow(
                [
                    stringify(context.name),
                    stringify(component.name),
                    stringify(ai_record.category),
                    stringify(ai_record.motivatie),
                ]
            )
    exports[f"{prefix}_ai_identification.csv"] = ai_buffer.getvalue()

    # Summary (optional)
    summary_buffer = io.StringIO()
    summary_writer = csv.writer(summary_buffer)
    summary_writer.writerow(["Gerelateerd aan BIA", "Summary Text"])
    if context.summary:
        summary_writer.writerow([stringify(context.name), stringify(context.summary.content)])
    exports[f"{prefix}_summary.csv"] = summary_buffer.getvalue()

    return exports


def import_from_csv(csv_files: dict[str, str]) -> None:
    """Import a BIA context from exported CSV artefacts."""

    if not current_user.is_authenticated:
        raise PermissionError("Authentication is required for CSV import.")

    bia_csv = csv_files.get("bia")
    if not bia_csv:
        raise ValueError("ContextScope CSV file (BIA) is required.")

    context_reader = list(csv.DictReader(io.StringIO(bia_csv)))
    if not context_reader:
        raise ValueError("BIA CSV did not contain any rows.")

    context_names = {
        (row.get("BIA Name") or "").strip()
        for row in context_reader
        if (row.get("BIA Name") or "").strip()
    }

    if not context_names:
        raise ValueError("BIA CSV must include at least one name.")

    component_csv = csv_files.get("components")
    consequences_csv = csv_files.get("consequences")
    availability_csv = csv_files.get("availability_requirements")
    ai_csv = csv_files.get("ai_identification")
    summary_csv = csv_files.get("summary")

    def _normalise(name: str | None) -> str:
        return (name or "").strip().lower()

    with db.session.begin_nested():
        for name in context_names:
            for existing in ContextScope.query.filter_by(name=name).all():
                db.session.delete(existing)
        db.session.flush()

        context_map: dict[str, ContextScope] = {}
        component_map: dict[tuple[str, str], Component] = {}
        authentication_options = list_authentication_options(active_only=False)
        option_by_slug = {option.slug.lower(): option for option in authentication_options}
        option_by_label: dict[str, AuthenticationOption] = {}
        for option in authentication_options:
            label_en = option.label_for_locale("en").strip()
            label_nl = option.label_for_locale("nl").strip()
            if label_en:
                option_by_label[label_en.lower()] = option
            if label_nl:
                option_by_label[label_nl.lower()] = option

        for row in context_reader:
            name = (row.get("BIA Name") or "").strip()
            if not name:
                continue
            payload = {
                "name": name,
                "responsible": row.get("BIA Responsible") or None,
                "coordinator": row.get("BIA Coordinator") or None,
                "start_date": _parse_date(row.get("BIA Start Date")),
                "end_date": _parse_date(row.get("BIA End Date")),
                "last_update": _parse_date(row.get("BIA Last Update")),
                "service_description": row.get("Service Description") or None,
                "knowledge": row.get("Knowledge") or None,
                "interfaces": row.get("Interfaces") or None,
                "mission_critical": row.get("Mission Critical") or None,
                "support_contracts": row.get("Support Contracts") or None,
                "security_supplier": row.get("Security Supplier") or None,
                "user_amount": _parse_int(row.get("User Amount")),
                "scope_description": row.get("Scope Description") or None,
                "risk_assessment_human": _parse_bool(row.get("Risk Assessment Human")),
                "risk_assessment_process": _parse_bool(row.get("Risk Assessment Process")),
                "risk_assessment_technological": _parse_bool(row.get("Risk Assessment Technological")),
                "ai_model": _parse_bool(row.get("AI Model")),
                "project_leader": row.get("Project Leader") or None,
                "risk_owner": row.get("Risk Owner") or None,
                "product_owner": row.get("Product Owner") or None,
                "technical_administrator": row.get("Technical Administrator") or None,
                "security_manager": row.get("Security Manager") or None,
                "incident_contact": row.get("Incident Contact") or None,
                "author_id": getattr(current_user, "id", None),
            }
            context = ContextScope(**payload)
            db.session.add(context)
            db.session.flush()
            context_map[_normalise(name)] = context

        if component_csv:
            for row in csv.DictReader(io.StringIO(component_csv)):
                component_name = (row.get("Component Name") or "").strip()
                if not component_name:
                    continue
                context_name = (row.get("Gerelateerd aan BIA") or "").strip()
                context = context_map.get(_normalise(context_name))
                if not context:
                    continue
                raw_slug = (row.get("Authentication Slug") or row.get("Authentication Method Slug") or "").strip().lower()
                auth_option = option_by_slug.get(raw_slug)
                if auth_option is None:
                    raw_label = (row.get("Authentication Label (EN)") or row.get("Authentication Label (NL)") or "").strip().lower()
                    if raw_label:
                        auth_option = option_by_label.get(raw_label)
                component = Component(
                    name=component_name,
                    info_type=row.get("Type of Information") or None,
                    process_dependencies=row.get("Process Dependencies") or None,
                    info_owner=row.get("Information Owner") or None,
                    user_type=row.get("Types of Users") or None,
                    description=row.get("Description of the Component") or None,
                    authentication_method_id=auth_option.id if auth_option else None,
                    context_scope_id=context.id,
                )
                db.session.add(component)
                db.session.flush()
                component_map[(context.id, _normalise(component_name))] = component

        def resolve_component(component_name: str, context_name: str) -> Component | None:
            context = context_map.get(_normalise(context_name))
            if not context:
                return None
            return component_map.get((context.id, _normalise(component_name)))

        if consequences_csv:
            for row in csv.DictReader(io.StringIO(consequences_csv)):
                component_name = (row.get("Gerelateerd aan Component") or "").strip()
                if not component_name:
                    continue
                context_name = row.get("Gerelateerd aan BIA") or row.get("Gerelateerd aan Context")
                component = None
                if context_name:
                    component = resolve_component(component_name, context_name)
                if component is None:
                    # Fall back to the first context when legacy files omit the parent reference
                    component = next(
                        (comp for key, comp in component_map.items() if key[1] == _normalise(component_name)),
                        None,
                    )
                if not component:
                    continue
                consequence = Consequences(
                    component_id=component.id,
                    consequence_category=row.get("Category of Consequence") or None,
                    security_property=row.get("Property of Security") or None,
                    consequence_worstcase=row.get("Worstcase Consequence") or None,
                    justification_worstcase=row.get("Justification for Worst Consequence") or None,
                    consequence_realisticcase=row.get("Realistic Consequence") or None,
                    justification_realisticcase=row.get("Justification for Realistic Consequence") or None,
                )
                db.session.add(consequence)

        if availability_csv:
            for row in csv.DictReader(io.StringIO(availability_csv)):
                component_name = (row.get("Gerelateerd aan Component") or "").strip()
                if not component_name:
                    continue
                context_name = (row.get("Gerelateerd aan BIA") or "").strip()
                component = resolve_component(component_name, context_name) if context_name else None
                if component is None:
                    component = next(
                        (comp for key, comp in component_map.items() if key[1] == _normalise(component_name)),
                        None,
                    )
                if not component:
                    continue
                availability = AvailabilityRequirements(
                    component_id=component.id,
                    mtd=row.get("Maximum Tolerable Downtime") or None,
                    rto=row.get("Recovery Time Objective") or None,
                    rpo=row.get("Recovery Point Objective") or None,
                    masl=row.get("Minimum Acceptable Service Level") or None,
                )
                db.session.add(availability)

        if ai_csv:
            for row in csv.DictReader(io.StringIO(ai_csv)):
                component_name = (row.get("Gerelateerd aan Component") or "").strip()
                if not component_name:
                    continue
                context_name = (row.get("Gerelateerd aan BIA") or "").strip()
                component = resolve_component(component_name, context_name) if context_name else None
                if component is None:
                    component = next(
                        (comp for key, comp in component_map.items() if key[1] == _normalise(component_name)),
                        None,
                    )
                if not component:
                    continue
                ai_record = AIIdentificatie(
                    component_id=component.id,
                    category=row.get("AI Category") or "No AI",
                    motivatie=row.get("AI Justification") or None,
                )
                db.session.add(ai_record)

        if summary_csv:
            for row in csv.DictReader(io.StringIO(summary_csv)):
                context_name = (row.get("Gerelateerd aan BIA") or "").strip()
                if not context_name:
                    continue
                context = context_map.get(_normalise(context_name))
                if not context:
                    continue
                content = row.get("Summary Text") or ""
                if context.summary:
                    context.summary.content = content
                else:
                    db.session.add(Summary(context_scope_id=context.id, content=content))

    _sync_identity_sequences()
    db.session.commit()


def export_to_sql(context: ContextScope) -> str:
    """Serialize a context scope and related records to INSERT statements."""

    statements: list[str] = []

    def insert_statement(table_name: str, data: dict[str, object | None]) -> str:
        columns: list[str] = []
        values: list[str] = []
        for key, value in data.items():
            if value is None:
                continue
            columns.append(key)
            values.append(_sql_value(value))
        column_sql = ", ".join(columns)
        value_sql = ", ".join(values)
        return f"INSERT INTO {table_name} ({column_sql}) VALUES ({value_sql});"

    context_table = ContextScope.__table__.name
    statements.append(
        insert_statement(
            context_table,
            {
                "id": context.id,
                "name": context.name,
                "responsible": context.responsible,
                "coordinator": context.coordinator,
                "start_date": context.start_date,
                "end_date": context.end_date,
                "last_update": context.last_update,
                "service_description": context.service_description,
                "knowledge": context.knowledge,
                "interfaces": context.interfaces,
                "mission_critical": context.mission_critical,
                "support_contracts": context.support_contracts,
                "security_supplier": context.security_supplier,
                "user_amount": context.user_amount,
                "scope_description": context.scope_description,
                "risk_assessment_human": int(bool(context.risk_assessment_human)),
                "risk_assessment_process": int(bool(context.risk_assessment_process)),
                "risk_assessment_technological": int(bool(context.risk_assessment_technological)),
                "ai_model": int(bool(context.ai_model)),
                "project_leader": context.project_leader,
                "risk_owner": context.risk_owner,
                "product_owner": context.product_owner,
                "technical_administrator": context.technical_administrator,
                "security_manager": context.security_manager,
                "incident_contact": context.incident_contact,
                "author_id": context.author_id,
            },
        )
    )

    component_table = Component.__table__.name
    consequence_table = Consequences.__table__.name
    availability_table = AvailabilityRequirements.__table__.name
    ai_table = AIIdentificatie.__table__.name
    summary_table = Summary.__table__.name

    for component in context.components:
        statements.append(
            insert_statement(
                component_table,
                {
                    "id": component.id,
                    "name": component.name,
                    "info_type": component.info_type,
                    "info_owner": component.info_owner,
                    "user_type": component.user_type,
                    "process_dependencies": component.process_dependencies,
                    "description": component.description,
                    "authentication_method_id": component.authentication_method_id,
                    "context_scope_id": component.context_scope_id,
                },
            )
        )
        for consequence in component.consequences:
            statements.append(
                insert_statement(
                    consequence_table,
                    {
                        "id": consequence.id,
                        "component_id": consequence.component_id,
                        "consequence_category": consequence.consequence_category,
                        "security_property": consequence.security_property,
                        "consequence_worstcase": consequence.consequence_worstcase,
                        "justification_worstcase": consequence.justification_worstcase,
                        "consequence_realisticcase": consequence.consequence_realisticcase,
                        "justification_realisticcase": consequence.justification_realisticcase,
                    },
                )
            )
        if component.availability_requirement:
            availability = component.availability_requirement
            statements.append(
                insert_statement(
                    availability_table,
                    {
                        "id": availability.id,
                        "component_id": availability.component_id,
                        "mtd": availability.mtd,
                        "rto": availability.rto,
                        "rpo": availability.rpo,
                        "masl": availability.masl,
                    },
                )
            )
        for ai_record in component.ai_identificaties:
            statements.append(
                insert_statement(
                    ai_table,
                    {
                        "id": ai_record.id,
                        "component_id": ai_record.component_id,
                        "category": ai_record.category,
                        "motivatie": ai_record.motivatie,
                    },
                )
            )

    if context.summary:
        statements.append(
            insert_statement(
                summary_table,
                {
                    "id": context.summary.id,
                    "context_scope_id": context.summary.context_scope_id,
                    "content": context.summary.content,
                },
            )
        )

    def sequence_reset_statement(table_name: str, column: str = "id") -> str:
        sequence_name = f"{table_name}_{column}_seq"
        value_sql = f"COALESCE((SELECT MAX({column}) FROM {table_name}), 1)"
        called_sql = f"CASE WHEN EXISTS (SELECT 1 FROM {table_name}) THEN true ELSE false END"
        return f"SELECT setval('{sequence_name}', {value_sql}, {called_sql});"

    statements.extend(
        [
            sequence_reset_statement(context_table),
            sequence_reset_statement(component_table),
            sequence_reset_statement(consequence_table),
            sequence_reset_statement(availability_table),
            sequence_reset_statement(ai_table),
            sequence_reset_statement(summary_table),
        ]
    )

    return "\n".join(statements)


def import_from_sql(sql_content: str) -> None:
    """Import SQL export statements from the BIA module."""

    if not current_user.is_authenticated:
        raise PermissionError("Authentication is required for SQL import.")

    statements = _split_sql_statements(sql_content)
    if not statements:
        raise ValueError("No SQL statements found in the provided file.")

    parsed: defaultdict[str, list[dict[str, object | None]]] = defaultdict(list)
    for statement in statements:
        stripped = statement.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("select setval"):
            continue
        table, columns, values = _parse_insert_statement(stripped)
        row = dict(zip(columns, values))
        parsed[table].append(_filter_columns(table, row))

    context_table = ContextScope.__table__.name
    component_table = Component.__table__.name
    consequence_table = Consequences.__table__.name
    availability_table = AvailabilityRequirements.__table__.name
    ai_table = AIIdentificatie.__table__.name
    summary_table = Summary.__table__.name

    if not parsed.get(context_table):
        raise ValueError("No context records found in the SQL import.")

    context_id_map: dict[int, int] = {}
    component_id_map: dict[int, int] = {}
    user_id = getattr(current_user, "id", None)

    with db.session.begin_nested():
        imported_names = {
            row.get("name")
            for row in parsed[context_table]
            if isinstance(row.get("name"), str)
        }
        if imported_names:
            for name in imported_names:
                for existing in ContextScope.query.filter_by(name=name).all():
                    db.session.delete(existing)
            db.session.flush()

        for row in parsed[context_table]:
            original_id = row.pop("id", None)
            row.pop("author_id", None)
            context = ContextScope(
                **{
                    **row,
                    "start_date": _parse_date(row.get("start_date")),
                    "end_date": _parse_date(row.get("end_date")),
                    "last_update": _parse_date(row.get("last_update")),
                    "risk_assessment_human": _parse_bool(row.get("risk_assessment_human")),
                    "risk_assessment_process": _parse_bool(row.get("risk_assessment_process")),
                    "risk_assessment_technological": _parse_bool(row.get("risk_assessment_technological")),
                    "ai_model": _parse_bool(row.get("ai_model")),
                    "user_amount": _parse_int(row.get("user_amount")),
                    "author_id": user_id,
                }
            )
            db.session.add(context)
            db.session.flush()
            if isinstance(original_id, int):
                context_id_map[original_id] = context.id

        for row in parsed[component_table]:
            original_id = row.pop("id", None)
            context_fk = row.get("context_scope_id")
            if isinstance(context_fk, int) and context_fk in context_id_map:
                row["context_scope_id"] = context_id_map[context_fk]
            component = Component(**row)
            db.session.add(component)
            db.session.flush()
            if isinstance(original_id, int):
                component_id_map[original_id] = component.id

        for row in parsed[consequence_table]:
            row.pop("id", None)
            component_fk = row.get("component_id")
            if isinstance(component_fk, int) and component_fk in component_id_map:
                row["component_id"] = component_id_map[component_fk]
            db.session.add(Consequences(**row))

        for row in parsed[availability_table]:
            row.pop("id", None)
            component_fk = row.get("component_id")
            if isinstance(component_fk, int) and component_fk in component_id_map:
                row["component_id"] = component_id_map[component_fk]
            db.session.add(AvailabilityRequirements(**row))

        for row in parsed[ai_table]:
            row.pop("id", None)
            component_fk = row.get("component_id")
            if isinstance(component_fk, int) and component_fk in component_id_map:
                row["component_id"] = component_id_map[component_fk]
            if not row.get("category"):
                row["category"] = "No AI"
            db.session.add(AIIdentificatie(**row))

        for row in parsed[summary_table]:
            row.pop("id", None)
            context_fk = row.get("context_scope_id")
            if isinstance(context_fk, int) and context_fk in context_id_map:
                row["context_scope_id"] = context_id_map[context_fk]
            db.session.add(Summary(**row))

    _sync_identity_sequences()
    db.session.commit()


def import_sql_file(file_storage) -> None:
    """Read, validate and import a SQL export file."""

    if not file_storage or not file_storage.filename:
        raise ValueError("No SQL file provided.")

    filename = Path(file_storage.filename)
    if filename.suffix.lower() != ".sql":
        raise ValueError("Only .sql files are supported.")

    stream = file_storage.stream
    stream.seek(0, io.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    if size > MAX_SQL_FILE_SIZE:
        raise ValueError("SQL file exceeds the maximum allowed size.")

    content = stream.read()
    try:
        sql_text = content.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError("SQL file must be UTF-8 encoded.") from exc

    import_from_sql(sql_text)


def ensure_export_folder() -> Path:
    """Ensure the export directory exists and return its path."""

    export_root = Path(current_app.root_path) / "exports"
    export_root.mkdir(parents=True, exist_ok=True)
    return export_root


def cleanup_export_folder(max_age_days: int) -> tuple[int, int]:
    """Remove export artefacts older than the configured age.

    Returns a tuple with (removed_count, failed_count).
    """

    max_age_days = max(1, int(max_age_days))
    export_root = ensure_export_folder()
    try:
        entries = list(export_root.iterdir())
    except FileNotFoundError:  # pragma: no cover - directory was removed externally
        return (0, 0)

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    removed = 0
    failed = 0

    for node in entries:
        if node.name.startswith("."):
            continue
        try:
            metadata = node.stat()
        except FileNotFoundError:  # pragma: no cover - race condition with concurrent deletion
            continue
        modified = datetime.fromtimestamp(metadata.st_mtime, timezone.utc)
        if modified >= cutoff:
            continue
        try:
            if node.is_dir():
                shutil.rmtree(node)
            else:
                node.unlink(missing_ok=True)
            removed += 1
        except Exception:  # pragma: no cover - defensive logging for filesystem issues
            failed += 1
            current_app.logger.warning("Failed to remove export artefact %s", node, exc_info=current_app.debug)

    return removed, failed


def _safe_slug(value: str | None) -> str:
    if not value:
        return "bia"
    return "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-", " "}).strip().replace(" ", "_")


def _parse_bool(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _parse_int(value: object | None) -> int | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text or text.lower() == "none":
            return None
        return int(text)
    except (TypeError, ValueError):
        return None


def _parse_date(value: object | None):
    if not value or str(value).strip().lower() in {"none", "null", ""}:
        return None
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _reset_identity_sequence(table_name: str, column: str = "id") -> None:
    sequence_name = f"{table_name}_{column}_seq"
    value_sql = f"COALESCE((SELECT MAX({column}) FROM {table_name}), 1)"
    called_sql = f"CASE WHEN EXISTS (SELECT 1 FROM {table_name}) THEN true ELSE false END"
    db.session.execute(text(f"SELECT setval('{sequence_name}', {value_sql}, {called_sql})"))


def _sync_identity_sequences() -> None:
    for table_name in (
        ContextScope.__table__.name,
        Component.__table__.name,
        Consequences.__table__.name,
        AvailabilityRequirements.__table__.name,
        AIIdentificatie.__table__.name,
        Summary.__table__.name,
    ):
        _reset_identity_sequence(table_name)


def _sql_value(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime):
        return f"'{value.isoformat()}'"
    return "'" + str(value).replace("'", "''") + "'"


def _split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_string = False
    i = 0
    while i < len(sql_text):
        char = sql_text[i]
        buffer.append(char)
        if char == "'":
            if i + 1 < len(sql_text) and sql_text[i + 1] == "'":
                buffer.append("'")
                i += 1
            else:
                in_string = not in_string
        elif char == ";" and not in_string:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        i += 1
    if buffer and "".join(buffer).strip():  # pragma: no cover - defensive
        raise ValueError("SQL file contained an incomplete statement.")
    return statements


_INSERT_REGEX = re.compile(
    r"^INSERT\s+INTO\s+(?P<table>[a-z0-9_]+)\s*\((?P<columns>[^)]+)\)\s+VALUES\s*\((?P<values>.*)\)\s*;$",
    re.IGNORECASE | re.DOTALL,
)


def _parse_insert_statement(statement: str) -> tuple[str, Sequence[str], Sequence[object]]:
    match = _INSERT_REGEX.match(statement)
    if not match:
        raise ValueError("Unexpected SQL statement encountered during import.")

    table = match.group("table").lower()
    table = _SQL_TABLE_ALIASES.get(table, table)
    if table not in _SQL_ALLOWED_TABLES:
        raise ValueError("SQL import references an unsupported table.")

    columns = [col.strip() for col in match.group("columns").split(",")]
    values = _split_values(match.group("values"))
    if len(columns) != len(values):
        raise ValueError("Column count did not match value count in SQL import.")

    converted = [_convert_sql_token(token) for token in values]
    return table, columns, converted


def _split_values(values_str: str) -> list[str]:
    values: list[str] = []
    buffer: list[str] = []
    in_string = False
    i = 0
    while i < len(values_str):
        char = values_str[i]
        if char == "'":
            buffer.append(char)
            if i + 1 < len(values_str) and values_str[i + 1] == "'":
                buffer.append("'")
                i += 1
            else:
                in_string = not in_string
        elif char == "," and not in_string:
            values.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)
        i += 1
    if buffer:
        values.append("".join(buffer).strip())
    return values


def _convert_sql_token(token: str) -> object | None:
    cleaned = token.strip()
    if cleaned.upper() == "NULL":
        return None
    if cleaned.startswith("'") and cleaned.endswith("'"):
        return cleaned[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        return float(cleaned)
    return cleaned
