from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for, send_file
from flask_login import current_user, login_required

from scaffold.apps.identity.models import (
    ROLE_ADMIN,
    ROLE_ASSESSMENT_MANAGER,
    ROLE_CONTROL_OWNER,
)
from scaffold.core.i18n import gettext as _
from scaffold.extensions import db
from scaffold.models import (
    Control,
    MaturityAnswer,
    MaturityAssessment,
    MaturityLevel,
    MaturityScore,
)
from .models import AssessmentStatus, MaturityAssessmentVersion
from .utils import export_to_sql

from .constants import CMMI_REQUIREMENTS

maturity_bp = Blueprint("maturity", __name__, url_prefix="/maturity", template_folder="templates")


@maturity_bp.app_template_filter("datetime")
def format_datetime(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format a datetime object for display."""
    if value is None:
        return ""
    return value.strftime(fmt)


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

    # Calculate statistics
    assessments_started = 0
    assessments_finished = 0
    total_maturity = 0

    for _, assessment in results:
        if assessment:
            if assessment.status == AssessmentStatus.BEING_ASSESSED:
                assessments_started += 1
            elif assessment.status in (AssessmentStatus.ASSESSED, AssessmentStatus.SUBMITTED, AssessmentStatus.APPROVED):
                assessments_finished += 1
                total_maturity += assessment.current_level.value

    average_maturity = 0
    if assessments_finished > 0:
        average_maturity = round(total_maturity / assessments_finished, 1)

    return render_template(
        "maturity/index.html",
        controls=results,
        assessments_started=assessments_started,
        assessments_finished=assessments_finished,
        average_maturity=average_maturity,
    )


@maturity_bp.route("/assess/<int:control_id>", methods=["GET", "POST"])
@login_required
def assess(control_id):
    """View and edit assessment for a specific control."""
    control = Control.query.get_or_404(control_id)
    
    # Find existing assessment for this control (shared/singleton)
    assessment = MaturityAssessment.query.filter_by(control_id=control.id).first()

    if not assessment:
        assessment = MaturityAssessment(
            control_id=control.id,
            current_level=MaturityLevel.INITIAL,
            status=AssessmentStatus.UNASSESSED,
        )
        db.session.add(assessment)
        db.session.commit()

    if request.method == "POST":
        action = request.form.get("action")
        
        is_admin = current_user.has_role(ROLE_ADMIN)
        is_owner = (control.owner_id == current_user.id) or current_user.has_role(ROLE_CONTROL_OWNER)
        is_assessor = current_user.has_role(ROLE_ASSESSMENT_MANAGER) or is_owner or is_admin

        if action == "submit":
            if not is_assessor:
                flash(_("maturity.assessment_permission_denied"), "danger")
                return redirect(url_for("maturity.assess", control_id=control.id))
            
            assessment.status = AssessmentStatus.SUBMITTED
            assessment.submitted_by_id = current_user.id
            db.session.commit()
            flash(_("maturity.assessment_submitted"), "success")
            return redirect(url_for("maturity.index"))
        
        elif action == "approve":
            if not (is_owner or is_admin):
                flash(_("maturity.assessment_permission_denied"), "danger")
                return redirect(url_for("maturity.assess", control_id=control.id))
            
            # Create snapshot version
            snapshot_data = {
                a.requirement_key: {
                    "level": a.level.name,
                    "compliant": a.compliant,
                    "evidence": a.evidence
                }
                for a in assessment.answers
            }
            
            version = MaturityAssessmentVersion(
                control_id=control.id,
                approved_by_id=current_user.id,
                maturity_level=assessment.current_level,
                data=snapshot_data,
                notes=assessment.notes
            )
            db.session.add(version)
            
            assessment.status = AssessmentStatus.APPROVED
            db.session.commit()
            
            flash(_("maturity.assessment_approved"), "success")
            return redirect(url_for("maturity.index"))

        elif action == "decline":
            if not is_owner:
                flash(_("maturity.assessment_permission_denied"), "danger")
                return redirect(url_for("maturity.assess", control_id=control.id))
            
            assessment.status = AssessmentStatus.UNASSESSED
            db.session.commit()
            flash(_("maturity.assessment_declined"), "success")
            return redirect(url_for("maturity.index"))

        elif action == "set_target":
            target_level_val = request.form.get("target_level")
            target_level = int(target_level_val) if target_level_val and target_level_val.isdigit() else None
            assessment.target_level = MaturityLevel(target_level) if target_level else None
            db.session.commit()
            flash(_("maturity.target_level_updated"), "success")
            return redirect(url_for("maturity.assess", control_id=control.id))

        # Default save action
        target_level_val = request.form.get("target_level")
        target_level = int(target_level_val) if target_level_val and target_level_val.isdigit() else None
        assessment.target_level = MaturityLevel(target_level) if target_level else None

        compliance_map = {}  # Track compliance for calculation

        # Process all requirements across all levels
        for level_num, requirements in CMMI_REQUIREMENTS.items():
            # If a strict target is set, we can ignore/reset levels above it
            ignore_level = target_level and level_num > target_level

            for req in requirements:
                req_key = req["id"]
                
                if ignore_level:
                    score_val = 0
                    jira_ticket = ""
                    description = ""
                    evidence_url = ""
                    is_compliant = False
                else:
                    # Extract structured form data
                    score_val = int(request.form.get(f"score_{req_key}", 0))
                    jira_ticket = request.form.get(f"jira_{req_key}", "").strip()
                    description = request.form.get(f"desc_{req_key}", "").strip()
                    evidence_url = request.form.get(f"url_{req_key}", "").strip()
                    
                    # Logic: Score 3 (Implemented) and 4 (Best Practice) count as compliant
                    is_compliant = score_val >= 3
                
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
                
                # Update fields
                try:
                    answer.score = MaturityScore(score_val)
                except ValueError:
                    answer.score = MaturityScore.NOT_APPLICABLE

                answer.jira_ticket = jira_ticket
                answer.description = description
                answer.evidence_url = evidence_url
                answer.compliant = is_compliant
                
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
        
        # Update workflow status on save
        assessment.status = AssessmentStatus.BEING_ASSESSED
        assessment.last_updated_by_id = current_user.id
        
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
        MaturityScore=MaturityScore,
        AssessmentStatus=AssessmentStatus,
    )


@maturity_bp.route("/reset/<int:control_id>", methods=["POST"])
@login_required
def reset_assessment(control_id):
    """Reset the maturity assessment for a specific control."""
    control = Control.query.get_or_404(control_id)
    
    assessment = MaturityAssessment.query.filter_by(control_id=control.id).first()

    if assessment:
        db.session.delete(assessment)
        db.session.commit()
        flash(_("maturity.assessment_reset"), "success")
    else:
        flash(_("maturity.assessment_not_found"), "warning")
        
    return redirect(url_for("maturity.index"))


@maturity_bp.route("/history/<int:control_id>")
@login_required
def history(control_id):
    """List past assessment versions for a control."""
    control = Control.query.get_or_404(control_id)
    versions = (
        MaturityAssessmentVersion.query
        .filter_by(control_id=control.id)
        .order_by(MaturityAssessmentVersion.approved_at.desc())
        .all()
    )
    
    return render_template(
        "maturity/history.html",
        control=control,
        versions=versions,
        MaturityLevel=MaturityLevel,
    )


@maturity_bp.route("/version/<int:version_id>")
@login_required
def version(version_id):
    """View a read-only snapshot of a past assessment."""
    version = MaturityAssessmentVersion.query.get_or_404(version_id)
    control = Control.query.get_or_404(version.control_id)
    
    return render_template(
        "maturity/version.html",
        control=control,
        version=version,
        levels=CMMI_REQUIREMENTS,
        MaturityLevel=MaturityLevel,
    )


@maturity_bp.route("/history/delete/<int:version_id>", methods=["POST"])
@login_required
def delete_version(version_id):
    """Delete a specific maturity assessment snapshot."""
    version = MaturityAssessmentVersion.query.get_or_404(version_id)
    control = Control.query.get_or_404(version.control_id)

    # Permission check: Only Admin or Control Owner
    is_admin = current_user.has_role(ROLE_ADMIN)
    is_owner = (control.owner_id == current_user.id) or current_user.has_role(ROLE_CONTROL_OWNER)
    
    if not (is_admin or is_owner):
        flash(_("maturity.assessment_permission_denied"), "danger")
        return redirect(url_for("maturity.history", control_id=control.id))

    db.session.delete(version)
    db.session.commit()
    
    flash(_("maturity.version_deleted"), "success")
    return redirect(url_for("maturity.history", control_id=control.id))


@maturity_bp.route("/export/html")
@login_required
def export_html():
    """Generate a full HTML report of the maturity state."""
    results = (
        db.session.query(Control, MaturityAssessment)
        .outerjoin(MaturityAssessment, MaturityAssessment.control_id == Control.id)
        .order_by(Control.domain, Control.id)
        .all()
    )

    # Calculate statistics
    assessments_finished = 0
    total_maturity = 0
    
    for _, assessment in results:
        if assessment and assessment.status in (AssessmentStatus.ASSESSED, AssessmentStatus.SUBMITTED, AssessmentStatus.APPROVED):
            assessments_finished += 1
            total_maturity += assessment.current_level.value

    average_maturity = round(total_maturity / assessments_finished, 1) if assessments_finished else 0

    return render_template(
        "maturity/export_report.html",
        controls=results,
        assessments_finished=assessments_finished,
        average_maturity=average_maturity,
        levels=CMMI_REQUIREMENTS,
        MaturityLevel=MaturityLevel,
        generated_at=datetime.now(),
    )

