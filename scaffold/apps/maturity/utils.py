from __future__ import annotations

import collections
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from scaffold.apps.maturity.models import (
    MaturityAnswer,
    MaturityAssessment,
    MaturityAssessmentVersion,
)
from scaffold.apps.risk.models import (
    Risk,
    RiskImpactAreaLink,
    RiskSeverityThreshold,
    risk_component_links,
    risk_control_links,
)
from scaffold.extensions import db


def _sql_value(value: Any) -> str:
    """Format a Python value as a SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return f"'{value.isoformat()}'"
    
    # Escape single quotes for SQL text
    # Standard SQL escape is two single quotes
    text_val = str(value)
    escaped = text_val.replace("'", "''")
    return f"'{escaped}'"


def export_to_sql() -> str:
    """Generate SQL INSERT statements for Maturity and Risk tables."""
    statements: list[str] = []

    def insert_statement(table_name: str, data: dict[str, Any]) -> str:
        columns: list[str] = []
        values: list[str] = []
        for key, value in data.items():
            if value is None:
                 # Skip None values to let default handling or explicit NULL if needed. 
                 # However, usually explicit NULL is safer for export.
                 # Based on BIA util, it skips. I'll stick to that but _sql_value handles None.
                 # Let's check logic: if value is None continue. 
                 # This means columns with defaults use defaults. 
                 # But for restore, we probably want exact state.
                 # I'll follow BIA util pattern: "if value is None: continue"
                 continue
            columns.append(key)
            values.append(_sql_value(value))
        
        if not columns:
            return ""

        column_sql = ", ".join(columns)
        value_sql = ", ".join(values)
        return f"INSERT INTO {table_name} ({column_sql}) VALUES ({value_sql});"

    # --- Maturity Tables ---
    
    # MaturityAssessment
    table = MaturityAssessment.__table__.name
    for item in MaturityAssessment.query.all():
        statements.append(insert_statement(table, {
            "id": item.id,
            "control_id": item.control_id,
            "status": item.status.name if item.status else None,
            "last_updated_by_id": item.last_updated_by_id,
            "submitted_by_id": item.submitted_by_id,
            "current_level": item.current_level.name if item.current_level else None,
            "target_level": item.target_level.name if item.target_level else None,
            "notes": item.notes,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }))

    # MaturityAnswer
    table = MaturityAnswer.__table__.name
    for item in MaturityAnswer.query.all():
        statements.append(insert_statement(table, {
            "id": item.id,
            "assessment_id": item.assessment_id,
            "level": item.level.name if item.level else None,
            "requirement_key": item.requirement_key,
            "compliant": item.compliant,
            "evidence": item.evidence,
        }))

    # MaturityAssessmentVersion
    table = MaturityAssessmentVersion.__table__.name
    for item in MaturityAssessmentVersion.query.all():
        # JSON config requires special handling if DB specific, but here it's likely just string
        # SQLAlchemy handles Python -> JSON conversion usually, 
        # but for raw SQL we might need json dump.
        # _sql_value stringifies dicts, but Postgres needs valid JSON string.
        # I'll rely on str() of dict being vaguely acceptable or use json.dumps?
        # BIA _sql_value uses str(value). str({'a':1}) -> "{'a': 1}". This is NOT valid JSON (needs double quotes).
        import json
        data_json = json.dumps(item.data) if item.data else None
        
        statements.append(insert_statement(table, {
            "id": item.id,
            "control_id": item.control_id,
            "approved_at": item.approved_at,
            "approved_by_id": item.approved_by_id,
            "maturity_level": item.maturity_level.name if item.maturity_level else None,
            "data": data_json,
            "notes": item.notes,
        }))

    # --- Risk Tables ---

    # Risk (Items)
    table = Risk.__table__.name
    for item in Risk.query.all():
        statements.append(insert_statement(table, {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "discovered_on": item.discovered_on,
            "impact": item.impact.value if item.impact else None,
            "chance": item.chance.value if item.chance else None,
            "treatment": item.treatment.value if item.treatment else None,
            "treatment_plan": item.treatment_plan,
            "treatment_due_date": item.treatment_due_date,
            "treatment_owner_id": item.treatment_owner_id,
            "ticket_url": item.ticket_url,
            "closed_at": item.closed_at,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }))

    # RiskImpactAreaLink
    table = RiskImpactAreaLink.__table__.name
    for item in RiskImpactAreaLink.query.all():
        statements.append(insert_statement(table, {
            "id": item.id,
            "risk_id": item.risk_id,
            "area": item.area.value if item.area else None,
        }))

    # RiskSeverityThreshold
    table = RiskSeverityThreshold.__table__.name
    for item in RiskSeverityThreshold.query.all():
        statements.append(insert_statement(table, {
            "id": item.id,
            "severity": item.severity.value if item.severity else None,
            "min_score": item.min_score,
            "max_score": item.max_score,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }))

    # Many-to-Many Links
    # Use db.session.execute to get raw rows for association tables
    
    # risk_component_links
    table = risk_component_links.name
    results = db.session.query(risk_component_links).all()
    for row in results:
        # row is a keyed tuple
        statements.append(insert_statement(table, {
            "risk_id": row.risk_id,
            "component_id": row.component_id,
        }))
        
    # risk_control_links
    table = risk_control_links.name
    results = db.session.query(risk_control_links).all()
    for row in results:
        statements.append(insert_statement(table, {
            "risk_id": row.risk_id,
            "control_id": row.control_id,
        }))

    return "\n".join(statements)
