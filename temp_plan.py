from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from scaffold.extensions import db
from scaffold.apps.bia.models import ContextScope, BiaTier

# Add BiaTier to models
class BiaTier(db.Model):
    __tablename__ = "bia_tiers"
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, unique=True, nullable=False)
    name_en = db.Column(db.String(255), nullable=False)
    name_nl = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<BiaTier {self.level}>"

# Add relationship to ContextScope
ContextScope.tier_id = db.Column(db.Integer, db.ForeignKey("bia_tiers.id"), nullable=True)
ContextScope.tier = db.relationship("BiaTier", backref="context_scopes")
