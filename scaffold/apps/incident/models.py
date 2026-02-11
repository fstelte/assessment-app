"""Incident Response Plan models."""

from __future__ import annotations

from ...extensions import db
from ...apps.bia.models import Component

class IncidentScenario(db.Model):
    """A scenario that triggers an incident response plan (The 'If')."""

    __tablename__ = "incident_scenarios"

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("bia_components.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    component = db.relationship("Component", backref=db.backref("incident_scenarios", lazy=True))
    steps = db.relationship("IncidentStep", back_populates="scenario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<IncidentScenario {self.name}>"


class IncidentStep(db.Model):
    """The steps to take in an incident scenario (The 'Then')."""

    __tablename__ = "incident_steps"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("incident_scenarios.id"), nullable=False)
    
    # 3a. Actions first hour
    actions_first_hour = db.Column(db.Text, nullable=True)
    
    # 3b. Alternatives / fallback
    alternatives = db.Column(db.Text, nullable=True)
    
    # 3c. RTO / RPO (Snapshot from BIA)
    rto = db.Column(db.String(255), nullable=True)
    rpo = db.Column(db.String(255), nullable=True)
    
    # 3d. Contact list
    contact_list = db.Column(db.Text, nullable=True)
    
    # 3e. Manual procedures / offline possibilities
    manual_procedures = db.Column(db.Text, nullable=True)

    scenario = db.relationship("IncidentScenario", back_populates="steps")

    def __repr__(self):
        return f"<IncidentStep scenario={self.scenario_id}>"
