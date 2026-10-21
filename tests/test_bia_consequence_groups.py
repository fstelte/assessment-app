from __future__ import annotations

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.apps.bia.utils import category_label, group_consequences
from scaffold.extensions import db


def _consequence(component, prop, category, worst, realistic, just_worst=None, just_real=None):
    return Consequences(
        component=component,
        security_property=prop,
        consequence_category=category,
        consequence_worstcase=worst,
        consequence_realisticcase=realistic,
        justification_worstcase=just_worst,
        justification_realisticcase=just_real,
    )


def _setup(app):
    context = ContextScope(name="Payments")
    beta = Component(name="beta", context_scope=context)
    alpha = Component(name="Alpha", context_scope=context)
    db.session.add_all([context, alpha, beta])
    return alpha, beta


def test_legacy_rows_merge_into_one_group(app):
    with app.test_request_context():
        alpha, _beta = _setup(app)
        rows = [
            _consequence(alpha, "Confidentiality", "privacy", "minor", "minor", "Leaks data", "Unlikely"),
            _consequence(alpha, "confidentiality", "financial", "major", None, "Fines", "Unlikely"),
            _consequence(alpha, "confidentiality ", "Operational", "moderate", "moderate", "Leaks data", ""),
        ]
        db.session.add_all(rows)
        db.session.flush()

        groups = group_consequences(rows)

        assert len(groups) == 1
        group = groups[0]
        assert group.component is alpha
        assert group.security_property == "confidentiality"
        assert [record.id for record in group.records] == sorted(row.id for row in rows)
        assert group.representative_id == rows[0].id
        # Known keys in canonical order; capitalised legacy value is matched case-insensitively.
        assert group.categories == ["financial", "operational", "privacy"]
        assert group.worstcase == "major"
        assert group.realisticcase == "moderate"
        assert group.justification_worstcase == "Leaks data\n\nFines"
        assert group.justification_realisticcase == "Unlikely"


def test_groups_ordered_by_component_then_cia(app):
    with app.test_request_context():
        alpha, beta = _setup(app)
        rows = [
            _consequence(beta, "availability", "operational", "minor", "minor"),
            _consequence(alpha, None, "regulatory", "minor", "minor"),
            _consequence(alpha, "availability", "operational", "minor", "minor"),
            _consequence(alpha, "confidentiality", "privacy", "minor", "minor"),
            _consequence(alpha, "integrity", "financial", "minor", "minor"),
        ]
        db.session.add_all(rows)
        db.session.flush()

        order = [(g.component.name, g.security_property) for g in group_consequences(rows)]

        assert order == [
            ("Alpha", "confidentiality"),
            ("Alpha", "integrity"),
            ("Alpha", "availability"),
            ("Alpha", ""),
            ("beta", "availability"),
        ]


def test_comma_joined_labels_split_and_unknown_values_last(app):
    with app.test_request_context():
        alpha, _beta = _setup(app)
        row = _consequence(alpha, "integrity", "Custom risk, privacy,financial", "minor", "minor")
        db.session.add(row)
        db.session.flush()

        (group,) = group_consequences([row])

        assert group.categories == ["financial", "privacy", "Custom risk"]


def test_category_label_translates_known_keys_and_keeps_unknown(app):
    with app.test_request_context():
        assert category_label("reputation and trust") == "Reputation and trust"
        assert category_label("Human and Safety") == "Human and safety"
        assert category_label("Custom risk") == "Custom risk"
        assert category_label(None) == ""
