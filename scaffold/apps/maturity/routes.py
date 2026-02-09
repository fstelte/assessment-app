from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from scaffold.core.i18n import gettext as _
from scaffold.extensions import db
from scaffold.models import (
    Control,
    MaturityAnswer,
    MaturityAssessment,
    MaturityLevel,
)

from .constants import CMMI_REQUIREMENTS

maturity_bp = Blueprint("maturity", __name__, url_prefix="/maturity", template_folder="templates")


@maturity_bp.route("/")
@login_required
def index():
    """List all controls with their current maturity status."""
    # Outer join to include controls even if they haven't been assessed yet
    results = (
        db.session.query(Control, MaturityAssessment)
        .outerjoin(MaturityAssessment, MaturityAssessment.control_id == Control.id)
        .order_by(Control.domain, Control.id)
        .all()
    )

    return render_template("maturity/index.html", controls=results)


@maturity_bp.route("/assess/<int:control_id>", methods=["GET", "POST"])
@login_required
def assess(control_id):
    """View and edit assessment for a specific control."""
    control = Control.query.get_or_404(control_id)
    
    # Find existing assessment for this user or create new
    assessment = MaturityAssessment.query.filter_by(
        control_id=control.id, assessor_id=current_user.id
    ).first()

    if not assessment:
        assessment = MaturityAssessment(
            control_id=control.id,
            assessor_id=current_user.id,
            current_level=MaturityLevel.INITIAL,
        )
        db.session.add(assessment)
        db.session.commit()

    if request.method == "POST":
        compliance_map = {}  # Track compliance for calculation

        # Process all requirements across all levels
        for level_num, requirements in CMMI_REQUIREMENTS.items():
            for req in requirements:
                req_key = req["id"]
                
                # Extract form data
                is_compliant = request.form.get(f"compliant_{req_key}") == "on"
                evidence_text = request.form.get(f"evidence_{req_key}", "")
                
                # Find or create answer record
                answer = MaturityAnswer.query.filter_by(
                    assessment_id=assessment.id, requirement_key=req_key
                ).first()
                
                if not answer:
                    answer = MaturityAnswer(
                        assessment_id=assessment.id,
                        requirement_key=req_key,
                        level=MaturityLevel(level_num),
                    )
                    db.session.add(answer)
                
                answer.compliant = is_compliant
                answer.evidence = evidence_text
                
                compliance_map[req_key] = is_compliant

        # Calculate achieved maturity level
        # Logic: A level N is achieved if all requirements for N AND all levels < N are compliant
        calculated_level = MaturityLevel.INITIAL
        sorted_levels = sorted(CMMI_REQUIREMENTS.keys())  # [2, 3, 4, 5]
        
        for level_num in sorted_levels:
            reqs_for_this_level = CMMI_REQUIREMENTS[level_num]
            all_met = all(compliance_map.get(r["id"], False) for r in reqs_for_this_level)
            
            if all_met:
                calculated_level = MaturityLevel(level_num)
            else:
                # If a lower level is not met, cannot achieve higher levels
                break
        
        assessment.current_level = calculated_level
        assessment.notes = request.form.get("assessment_notes", "")
        db.session.commit()
        
        flash(_("maturity.assessment_saved"), "success")
        return redirect(url_for("maturity.index"))

    # GET: Prepare data for template
    existing_answers = {
        a.requirement_key: a for a in assessment.answers
    }

    return render_template(
        "maturity/assessment.html",
        control=control,
        assessment=assessment,
        levels=CMMI_REQUIREMENTS,
        answers=existing_answers,
        MaturityLevel=MaturityLevel,
    )


@maturity_bp.route("/reset/<int:control_id>", methods=["POST"])
@login_required
def reset_assessment(control_id):
    """Reset the maturity assessment for a specific control."""
    control = Control.query.get_or_404(control_id)
    
    assessment = MaturityAssessment.query.filter_by(
        control_id=control.id, assessor_id=current_user.id
    ).first()

    if assessment:
        db.session.delete(assessment)
        db.session.commit()
        flash(_("maturity.assessment_reset"), "success")
    else:
        flash(_("maturity.assessment_not_found"), "warning")
        
    return redirect(url_for("maturity.index"))
