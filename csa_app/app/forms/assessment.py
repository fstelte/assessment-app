"""Assessment-related forms."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from ..i18n import gettext as _, lazy_gettext as _l


def _label(key: str) -> str:
    return _l(key)


class AssessmentStartForm(FlaskForm):
    template_id = SelectField(
        _label("assessments.start.fields.template"),
        coerce=int,
        validators=[DataRequired(message=_("assessments.start.errors.template_required"))],
    )
    submit = SubmitField(_label("assessments.start.actions.submit"))


class AssessmentAssignForm(FlaskForm):
    assignee_id = SelectField(
        _label("assessments.assign.fields.assignee"),
        coerce=int,
        validators=[DataRequired(message=_("assessments.assign.errors.assignee_required"))],
    )
    template_id = SelectField(
        _label("assessments.assign.fields.template"),
        coerce=int,
        validators=[DataRequired(message=_("assessments.assign.errors.template_required"))],
    )
    due_date = DateField(_label("assessments.assign.fields.due_date"), validators=[Optional()], format="%Y-%m-%d")
    submit = SubmitField(_label("assessments.assign.actions.submit"))


class AssessmentResponseForm(FlaskForm):
    save = SubmitField(_label("assessments.response.actions.save"))
    submit_for_review = SubmitField(_label("assessments.response.actions.submit_for_review"))


class AssessmentReviewForm(FlaskForm):
    comment = TextAreaField(
        _label("assessments.review.fields.comment"),
        render_kw={
            "rows": 4,
            "placeholder": _("assessments.review.fields.comment_placeholder"),
        },
    )
    approve = SubmitField(_label("assessments.review.actions.approve"))
    return_to_assignee = SubmitField(_label("assessments.review.actions.return_to_assignee"))


def build_assessment_response_form(question_set: Dict[str, Any]) -> Tuple[type[AssessmentResponseForm], List[Dict[str, Any]]]:
    """Generate a dynamic form for an assessment question set.

    Returns a tuple containing the generated form class and a layout description
    so templates can render sections in order.
    """

    class DynamicAssessmentResponseForm(AssessmentResponseForm):
        pass

    layout: List[Dict[str, Any]] = []

    for dimension_key, section in question_set.items():
        questions = section.get("questions", []) or []
        rendered_questions: List[Dict[str, Any]] = []

        for index, question_text in enumerate(questions):
            field_name = f"{dimension_key}_{index}"
            field = TextAreaField(
                question_text,
                render_kw={
                    "rows": 3,
                    "placeholder": _("assessments.response.fields.answer_placeholder"),
                },
            )
            setattr(DynamicAssessmentResponseForm, field_name, field)
            rendered_questions.append(
                {
                    "field_name": field_name,
                    "dimension": dimension_key,
                    "question": question_text,
                }
            )

        layout.append(
            {
                "dimension": dimension_key,
                "label": section.get("label") or dimension_key.replace("_", " ").title(),
                "questions": rendered_questions,
            }
        )

    return DynamicAssessmentResponseForm, layout
