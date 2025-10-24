"""Forms supporting CSA self-assessment workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class AssessmentStartForm(FlaskForm):
    """Start a self-assessment from an active template."""

    template_id = SelectField(
        "Template",
        coerce=int,
        validators=[DataRequired(message="Select a template."),],
    )
    submit = SubmitField("Start self-assessment")


class AssessmentAssignForm(FlaskForm):
    """Assign an assessment template to another user."""

    assignee_id = SelectField(
        "Assign to",
        coerce=int,
        validators=[DataRequired(message="Select a user."),],
    )
    template_id = SelectField(
        "Template",
        coerce=int,
        validators=[DataRequired(message="Select a template."),],
    )
    due_date = DateField("Due date", validators=[Optional()], format="%Y-%m-%d")
    submit = SubmitField("Assign")


class AssessmentResponseForm(FlaskForm):
    """Shared actions for responding to an assessment."""

    save = SubmitField("Save responses")
    submit_for_review = SubmitField("Submit for review")


class AssessmentReviewForm(FlaskForm):
    """Form used by reviewers to approve or return assessments."""

    comment = TextAreaField(
        "Review comment",
        render_kw={
            "rows": 4,
            "placeholder": "Add context when approving or reasons when returning.",
        },
    )
    approve = SubmitField("Approve")
    return_to_assignee = SubmitField("Return to assignee")


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
                    "placeholder": "Enter your answer here.",
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
