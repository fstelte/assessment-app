"""Forms supporting CSA self-assessment workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from scaffold.core.i18n import lazy_gettext as _l


def _label(key: str) -> str:
    """Return a lazy translation coerced to str for WTForms labels."""

    return cast(str, _l(key))


def _message(key: str) -> str:
    """Return a lazy translation coerced to str for validation messages."""

    return cast(str, _l(key))


class AssessmentStartForm(FlaskForm):
    """Start a self-assessment from an active template."""

    template_id = SelectField(
        _label("csa.assessments.start.fields.template.label"),
        coerce=int,
        validators=[DataRequired(message=_message("csa.assessments.start.fields.template.required"))],
    )
    submit = SubmitField(_label("csa.assessments.start.submit"))


class AssessmentAssignForm(FlaskForm):
    """Assign an assessment template to another user."""

    assignee_id = SelectField(
        _label("csa.assessments.assign.fields.assignee.label"),
        coerce=int,
        validators=[DataRequired(message=_message("csa.assessments.assign.fields.assignee.required"))],
    )
    template_id = SelectField(
        _label("csa.assessments.assign.fields.template.label"),
        coerce=int,
        validators=[DataRequired(message=_message("csa.assessments.assign.fields.template.required"))],
    )
    due_date = DateField(
        _label("csa.assessments.assign.fields.due_date.label"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    submit = SubmitField(_label("csa.assessments.assign.submit"))


class AssessmentResponseForm(FlaskForm):
    """Shared actions for responding to an assessment."""

    save = SubmitField(_label("csa.assessments.detail.actions.save"))
    submit_for_review = SubmitField(_label("csa.assessments.detail.actions.submit_for_review"))


class AssessmentReviewForm(FlaskForm):
    """Form used by reviewers to approve or return assessments."""

    comment = TextAreaField(
        _label("csa.assessments.detail.review.comment_label"),
        render_kw={
            "rows": 4,
            "placeholder": cast(str, _l("csa.assessments.detail.review.comment_placeholder")),
        },
    )
    approve = SubmitField(_label("csa.assessments.detail.review.approve"))
    return_to_assignee = SubmitField(_label("csa.assessments.detail.review.return_to_assignee"))


def build_assessment_response_form(question_set: Dict[str, Any]) -> Tuple[type[AssessmentResponseForm], List[Dict[str, Any]]]:
    """Generate a dynamic response form for the provided question set."""

    class DynamicAssessmentResponseForm(AssessmentResponseForm):  # type: ignore[misc]
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
                    "placeholder": cast(str, _l("csa.assessments.form.answer_placeholder")),
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
