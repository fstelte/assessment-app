"""Routes for the Incident Response Plan app."""

from pathlib import Path
import re
import unicodedata
from flask import render_template, redirect, url_for, flash, request, abort, current_app, send_file
from flask_login import login_required
from flask_wtf import FlaskForm

from ...extensions import db
from ...apps.bia.models import Component, ContextScope
from . import bp
from .models import IncidentScenario, IncidentStep
from .forms import ScenarioForm, IncidentStepForm
from .services import get_bia_requirements


def _safe_filename(name: str) -> str:
    """Sanitize a string to be safe for filenames."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "_", name)


def ensure_export_folder() -> Path:
    folder = Path(current_app.instance_path) / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@bp.route("/")
@login_required
def dashboard():
    """List components to select for incident planning."""
    
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)

    try:
        per_page = int(request.args.get("per_page", 20))
    except (TypeError, ValueError):
        per_page = 20
    per_page = min(max(1, per_page), 100)

    search_query = (request.args.get("q") or "").strip()
    selected_scope = (request.args.get("scope") or "all").strip()

    query = Component.query.join(ContextScope)

    if search_query:
        like = f"%{search_query}%"
        query = query.filter(Component.name.ilike(like))
    
    if selected_scope and selected_scope.lower() != "all":
        query = query.filter(ContextScope.name == selected_scope)

    pagination = query.order_by(ContextScope.name, Component.name).paginate(page=page, per_page=per_page, error_out=False)
    contexts = ContextScope.query.order_by(ContextScope.name.asc()).all()

    return render_template(
        "incident/dashboard.html",
        components=pagination.items,
        pagination=pagination,
        contexts=contexts,
        search_query=search_query,
        selected_scope=selected_scope
    )

@bp.route("/component/<int:component_id>")
@login_required
def component_scenarios(component_id):
    """List scenarios for a specific component."""
    component = Component.query.get_or_404(component_id)
    scenarios = IncidentScenario.query.filter_by(component_id=component_id).all()
    delete_form = FlaskForm()
    return render_template("incident/component_scenarios.html", component=component, scenarios=scenarios, delete_form=delete_form)

@bp.route("/component/<int:component_id>/scenario/new", methods=["GET", "POST"])
@login_required
def create_scenario(component_id):
    """Create a new scenario (The If)."""
    component = Component.query.get_or_404(component_id)
    form = ScenarioForm()
    
    if form.validate_on_submit():
        scenario = IncidentScenario(
            component_id=component.id,
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(scenario)
        db.session.commit()
        flash("Scenario created successfully.", "success")
        return redirect(url_for("incident.manage_steps", scenario_id=scenario.id))
        
    return render_template("incident/edit_scenario.html", form=form, component=component, title="Create Scenario")

@bp.route("/scenario/<int:scenario_id>/edit", methods=["GET", "POST"])
@login_required
def edit_scenario(scenario_id):
    """Edit an existing scenario (The If)."""
    scenario = IncidentScenario.query.get_or_404(scenario_id)
    form = ScenarioForm(obj=scenario)
    
    if form.validate_on_submit():
        form.populate_obj(scenario)
        db.session.commit()
        flash("Scenario updated.", "success")
        return redirect(url_for("incident.component_scenarios", component_id=scenario.component_id))
        
    return render_template("incident/edit_scenario.html", form=form, component=scenario.component, title="Edit Scenario")

@bp.route("/scenario/<int:scenario_id>/steps", methods=["GET", "POST"])
@login_required
def manage_steps(scenario_id):
    """Manage the steps for a scenario (The Then)."""
    scenario = IncidentScenario.query.get_or_404(scenario_id)
    component = scenario.component
    
    # Check if steps exist
    steps = IncidentStep.query.filter_by(scenario_id=scenario.id).first()
    
    # Pre-fill RTO/RPO from BIA Service
    bia_reqs = get_bia_requirements(component.id)
    
    if not steps:
        steps = IncidentStep(scenario_id=scenario.id)
        steps.rto = bia_reqs["rto"]
        steps.rpo = bia_reqs["rpo"]
    else:
        # Also pre-fill if existing record has empty fields
        if not steps.rto:
            steps.rto = bia_reqs["rto"]
        if not steps.rpo:
            steps.rpo = bia_reqs["rpo"]
    
    form = IncidentStepForm(obj=steps)
    
    if form.validate_on_submit():
        form.populate_obj(steps)
        db.session.add(steps)
        db.session.commit()
        flash("Incident plan updated.", "success")
        return redirect(url_for("incident.manage_steps", scenario_id=scenario.id))
        
    return render_template("incident/manage_steps.html", form=form, scenario=scenario, component=component)

@bp.route("/scenario/<int:scenario_id>/export/html")
@login_required
def export_scenario_html(scenario_id):
    """Export the scenario and plans as HTML for printing."""
    scenario = IncidentScenario.query.get_or_404(scenario_id)
    steps = IncidentStep.query.filter_by(scenario_id=scenario.id).first()
    
    from datetime import date
    
    css_path = Path(current_app.root_path) / "static" / "css" / "app.css"
    export_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    
    html_content = render_template(
        "incident/export_scenario.html",
        scenario=scenario,
        component=scenario.component,
        steps=steps,
        current_date=date.today().strftime("%Y-%m-%d"),
        export_mode=True,
        export_css=export_css
    )
    
    safe_name = _safe_filename(f"{scenario.component.name}_{scenario.name}")
    filename = f"IncidentPlan_{safe_name}.html"
    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(html_content, encoding="utf-8")
    
    return send_file(file_path, as_attachment=True, download_name=filename)
    return render_template(
        "incident/export_scenario.html",
        scenario=scenario,
        component=scenario.component,
        steps=steps,
        current_date=date.today().strftime("%Y-%m-%d")
    )

@bp.route("/scenario/<int:scenario_id>/delete", methods=["POST"])
@login_required
def delete_scenario(scenario_id):
    """Delete a scenario and its associated plans."""
    scenario = IncidentScenario.query.get_or_404(scenario_id)
    component_id = scenario.component_id
    db.session.delete(scenario)
    db.session.commit()
    flash("Scenario deleted.", "success")
    return redirect(url_for("incident.component_scenarios", component_id=component_id))
