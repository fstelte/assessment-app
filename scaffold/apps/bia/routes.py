"""Routes implementing the complete Business Impact Analysis workflow."""

from __future__ import annotations

import csv
import io
import logging
from collections import defaultdict
from datetime import date, datetime

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from ...core.security import require_fresh_login
from ...extensions import db
from ..identity.models import User
from .forms import (
    ChangePasswordForm,
    ComponentForm,
    ConsequenceForm,
    ContextScopeForm,
    ImportCSVForm,
    ImportSQLForm,
    SummaryForm,
)
from .models import (
    AIIdentificatie,
    AvailabilityRequirements,
    Component,
    Consequences,
    ContextScope,
    Summary,
)
from .utils import (
    ensure_export_folder,
    export_to_csv,
    export_to_sql,
    get_cia_impact,
    get_impact_color,
    get_impact_level,
    get_max_cia_impact,
    import_from_csv,
    import_sql_file,
)
def get_impact_color(impact):
    impact_colors = {
        'catastrophic': 'badge bg-danger',
        'major': 'badge bg-warning text-dark',
        'moderate': 'badge bg-info text-dark',
        'minor': 'badge bg-primary',
        'insignificant': 'badge bg-success'
    }
    return impact_colors.get(impact.lower(), 'badge bg-secondary')

bp = Blueprint(
    "bia",
    __name__,
    url_prefix="/bia",
    template_folder="templates",
    static_folder="static",
)


@bp.app_context_processor
def inject_helpers():
    return {
        "bia_get_cia_impact": get_cia_impact,
        "bia_get_impact_color": get_impact_color,
        "bia_get_max_cia_impact": get_max_cia_impact,
    }


@bp.route("/")
@bp.route("/index")
@login_required
def dashboard():
    contexts = ContextScope.query.order_by(ContextScope.last_update.desc()).all()
    return render_template("bia/dashboard.html", contexts=contexts)


@bp.route("/item/new", methods=["GET", "POST"])
@login_required
def new_item():
    form = ContextScopeForm()
    component_form = ComponentForm()
    if form.validate_on_submit():
        context = ContextScope(author=_resolve_user())
        _apply_context_form(form, context)
        context.last_update = date.today()
        db.session.add(context)
        db.session.commit()
        flash("BIA created successfully.", "success")
        return redirect(url_for("bia.view_item", item_id=context.id))
    return render_template(
        "bia/context_form.html",
        form=form,
        component_form=component_form,
        item=None,
    )


@bp.route("/item/<int:item_id>")
@login_required
def view_item(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    consequences = [consequence for component in item.components for consequence in component.consequences]
    max_cia_impact = get_max_cia_impact(consequences)
    ai_identifications = _collect_ai_identifications(item)

    return render_template(
        "bia/context_detail.html",
        item=item,
        consequences=consequences,
        max_cia_impact=max_cia_impact,
        ai_identifications=ai_identifications,
    )


@bp.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if item.author and item.author != current_user:
        flash("You do not have permission to edit this BIA.", "danger")
        return redirect(url_for("bia.view_item", item_id=item.id))

    form = ContextScopeForm(obj=item)
    component_form = ComponentForm()
    if form.validate_on_submit():
        _apply_context_form(form, item)
        item.last_update = date.today()
        db.session.commit()
        flash("BIA updated successfully.", "success")
        return redirect(url_for("bia.view_item", item_id=item.id))

    return render_template(
        "bia/context_form.html",
        form=form,
        component_form=component_form,
        item=item,
    )


@bp.route("/item/<int:item_id>/delete", methods=["POST"])
@login_required
@require_fresh_login(max_age_minutes=30)
def delete_item(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if item.author and item.author != current_user:
        flash("You do not have permission to delete this BIA.", "danger")
        return redirect(url_for("bia.view_item", item_id=item.id))

    db.session.delete(item)
    db.session.commit()
    flash("BIA deleted.", "success")
    return redirect(url_for("bia.dashboard"))


@bp.route("/add_component", methods=["POST"])
@login_required
def add_component():
    form = ComponentForm()
    if form.validate_on_submit():
        context_id = request.form.get("bia_id")
        context = ContextScope.query.get(context_id) if context_id else None
        if not context:
            return jsonify({"success": False, "errors": {"bia_id": ["Unknown BIA"]}}), 400
        component = Component(
            name=form.name.data,
            info_type=form.info_type.data,
            info_owner=form.info_owner.data,
            user_type=form.user_type.data,
            process_dependencies=form.process_dependencies.data,
            description=form.description.data,
            context_scope=context,
        )
        db.session.add(component)
        db.session.commit()
        return jsonify({"success": True, "id": component.id, "name": component.name})
    return jsonify({"success": False, "errors": form.errors}), 400


@bp.route("/update_component/<int:component_id>", methods=["POST"])
@login_required
def update_component(component_id: int):
    component = Component.query.get_or_404(component_id)
    form = ComponentForm()
    if form.validate_on_submit():
        component.name = form.name.data
        component.info_type = form.info_type.data
        component.info_owner = form.info_owner.data
        component.user_type = form.user_type.data
        component.process_dependencies = form.process_dependencies.data
        component.description = form.description.data
        db.session.commit()
        return jsonify({"success": True, "name": component.name})
    return jsonify({"success": False, "errors": form.errors}), 400


@bp.route("/delete_component/<int:component_id>", methods=["POST"])
@login_required
def delete_component(component_id: int):
    component = Component.query.get_or_404(component_id)
    db.session.delete(component)
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/components")
@login_required
def view_components():
    scope_filter = request.args.get("scope", "all").strip()
    query = Component.query.join(ContextScope)
    if scope_filter and scope_filter.lower() != "all":
        query = query.filter(ContextScope.name.ilike(f"%{scope_filter}%"))
    components = query.order_by(Component.name.asc()).all()
    contexts = ContextScope.query.order_by(ContextScope.name.asc()).all()
    component_form = ComponentForm()
    consequence_form = ConsequenceForm()
    return render_template(
        "bia/components.html",
        components=components,
        contexts=contexts,
        selected_scope=scope_filter,
        component_form=component_form,
        consequence_form=consequence_form,
    )


@bp.route("/get_component/<int:component_id>")
@login_required
def get_component(component_id: int):
    component = Component.query.get_or_404(component_id)
    return jsonify(
        {
            "id": component.id,
            "name": component.name,
            "info_type": component.info_type,
            "info_owner": component.info_owner,
            "user_type": component.user_type,
            "description": component.description,
            "process_dependencies": component.process_dependencies,
            "bia_name": component.context_scope.name if component.context_scope else None,
            "consequences_count": len(component.consequences),
        }
    )


@bp.route("/add_consequence/<int:component_id>", methods=["POST"])
@login_required
def add_consequence(component_id: int):
    component = Component.query.get_or_404(component_id)
    data = request.get_json() or {}
    form = ConsequenceForm(data=data)
    if form.validate():
        categories = data.get("consequence_category") or []
        if not isinstance(categories, list):
            categories = [categories]
        for category in categories:
            consequence = Consequences(
                component=component,
                consequence_category=category,
                security_property=form.security_property.data,
                consequence_worstcase=form.consequence_worstcase.data,
                justification_worstcase=form.justification_worstcase.data,
                consequence_realisticcase=form.consequence_realisticcase.data,
                justification_realisticcase=form.justification_realisticcase.data,
            )
            db.session.add(consequence)
        db.session.commit()
        return jsonify({"success": True, "message": f"{len(categories)} consequences added."})
    return jsonify({"success": False, "errors": form.errors}), 400


@bp.route("/get_consequence/<int:consequence_id>")
@login_required
def get_consequence(consequence_id: int):
    consequence = Consequences.query.get_or_404(consequence_id)
    return jsonify(
        {
            "id": consequence.id,
            "consequence_category": consequence.consequence_category,
            "security_property": consequence.security_property,
            "consequence_worstcase": consequence.consequence_worstcase,
            "justification_worstcase": consequence.justification_worstcase,
            "consequence_realisticcase": consequence.consequence_realisticcase,
            "justification_realisticcase": consequence.justification_realisticcase,
        }
    )


@bp.route("/edit_consequence/<int:consequence_id>", methods=["POST"])
@login_required
def edit_consequence(consequence_id: int):
    consequence = Consequences.query.get_or_404(consequence_id)
    data = request.get_json() or {}
    required = [
        "consequence_category",
        "security_property",
        "consequence_worstcase",
        "consequence_realisticcase",
    ]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({"success": False, "errors": {field: ["This field is required."] for field in missing}}), 400
    consequence.consequence_category = data.get("consequence_category")
    consequence.security_property = data.get("security_property")
    consequence.consequence_worstcase = data.get("consequence_worstcase")
    consequence.justification_worstcase = data.get("justification_worstcase")
    consequence.consequence_realisticcase = data.get("consequence_realisticcase")
    consequence.justification_realisticcase = data.get("justification_realisticcase")
    db.session.commit()
    return jsonify({"success": True, "message": "Consequence updated."})


@bp.route("/delete_consequence/<int:consequence_id>", methods=["POST"])
@login_required
def delete_consequence(consequence_id: int):
    consequence = Consequences.query.get_or_404(consequence_id)
    db.session.delete(consequence)
    db.session.commit()
    return jsonify({"success": True, "message": "Consequence deleted."})


@bp.route("/consequences/<int:component_id>")
@login_required
def view_consequences(component_id: int):
    component = Component.query.get_or_404(component_id)
    consequences = Consequences.query.filter_by(component_id=component.id).all()
    consequence_form = ConsequenceForm()
    return render_template(
        "bia/view_consequences.html",
        component=component,
        consequences=consequences,
        consequence_form=consequence_form,
    )


@bp.route("/get_availability/<int:component_id>")
@login_required
def get_availability(component_id: int):
    availability = AvailabilityRequirements.query.filter_by(component_id=component_id).first()
    if not availability:
        return jsonify({})
    return jsonify(
        {
            "mtd": availability.mtd,
            "rto": availability.rto,
            "rpo": availability.rpo,
            "masl": availability.masl,
        }
    )


@bp.route("/update_availability/<int:component_id>", methods=["POST"])
@login_required
def update_availability(component_id: int):
    availability = AvailabilityRequirements.query.filter_by(component_id=component_id).first()
    if availability is None:
        availability = AvailabilityRequirements(component_id=component_id)
        db.session.add(availability)
    availability.mtd = request.form.get("mtd")
    availability.rto = request.form.get("rto")
    availability.rpo = request.form.get("rpo")
    availability.masl = request.form.get("masl")
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/add_ai_identification/<int:component_id>", methods=["POST"])
@login_required
def add_ai_identification(component_id: int):
    component = Component.query.get_or_404(component_id)
    existing = AIIdentificatie.query.filter_by(component_id=component.id).first()
    if existing:
        existing.category = request.form.get("category") or existing.category
        existing.motivatie = request.form.get("motivatie")
    else:
        ai_record = AIIdentificatie(
            component=component,
            category=request.form.get("category") or "No AI",
            motivatie=request.form.get("motivatie"),
        )
        db.session.add(ai_record)
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/update_ai_identification/<int:component_id>", methods=["POST"])
@login_required
def update_ai_identification(component_id: int):
    component = Component.query.get_or_404(component_id)
    ai_record = AIIdentificatie.query.filter_by(component_id=component.id).first()
    if ai_record is None:
        ai_record = AIIdentificatie(component=component)
        db.session.add(ai_record)
    ai_record.category = request.form.get("category") or ai_record.category
    ai_record.motivatie = request.form.get("motivatie")
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/get_ai_identification/<int:component_id>")
@login_required
def get_ai_identification(component_id: int):
    ai_record = AIIdentificatie.query.filter_by(component_id=component_id).first()
    if not ai_record:
        return jsonify({"exists": False, "category": "No AI", "motivatie": ""}), 404
    return jsonify(
        {
            "exists": True,
            "category": ai_record.category,
            "motivatie": ai_record.motivatie,
        }
    )


@bp.route("/item/<int:item_id>/summary", methods=["GET", "POST"])
@login_required
def manage_summary(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if item.author and item.author != current_user:
        abort(403)
    form = SummaryForm(obj=item.summary)
    if form.validate_on_submit():
        if item.summary:
            item.summary.content = form.content.data
        else:
            db.session.add(Summary(content=form.content.data, context_scope=item))
        db.session.commit()
        flash("Summary updated.", "success")
        return redirect(url_for("bia.view_item", item_id=item.id))
    return render_template("bia/manage_summary.html", form=form, item=item)


@bp.route("/item/<int:item_id>/summary/delete", methods=["POST"])
@login_required
def delete_summary(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if item.author and item.author != current_user:
        abort(403)
    if item.summary:
        db.session.delete(item.summary)
        db.session.commit()
        flash("Summary deleted.", "success")
    return redirect(url_for("bia.view_item", item_id=item.id))


@bp.route("/item/<int:item_id>/export")
@login_required
def export_item(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    consequences = [consequence for component in item.components for consequence in component.consequences]
    max_cia_impact = get_max_cia_impact(consequences)
    ai_identifications = _collect_ai_identifications(item)
    html_content = render_template(
        "bia/export_item.html",
        item=item,
        consequences=consequences,
        max_cia_impact=max_cia_impact,
        ai_identifications=ai_identifications,
    )

    safe_name = _safe_filename(item.name)
    filename = f"BIA_{safe_name}.html"
    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(html_content, encoding="utf-8")
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/export_csv/<int:item_id>")
@login_required
def export_csv(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    if item.author and item.author != current_user:
        abort(403)
    export_folder = ensure_export_folder() / _safe_filename(item.name)
    export_folder.mkdir(parents=True, exist_ok=True)
    csv_files = export_to_csv(item)
    exported_files = []
    for filename, content in csv_files.items():
        path = export_folder / filename
        path.write_text(content, encoding="utf-8")
        exported_files.append(
            {
                "filename": filename,
                "path": export_folder.name,
                "size": len(content.encode("utf-8")),
            }
        )
    flash("CSV export created.", "success")
    return render_template(
        "bia/csv_export_overview.html",
        item=item,
        exported_files=exported_files,
        export_folder=export_folder.name,
    )


@bp.route("/download_csv/<path:folder>/<path:filename>")
@login_required
def download_csv_file(folder: str, filename: str):
    export_folder = ensure_export_folder() / folder
    file_path = export_folder / filename
    if not file_path.exists():
        flash("Requested file was not found.", "danger")
        return redirect(url_for("bia.dashboard"))
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/import_csv", methods=["GET", "POST"])
@login_required
def import_csv_view():
    form = ImportCSVForm()
    if request.method == "POST":
        csv_files: dict[str, str] = {}
        file_mapping = {
            "bia": form.bia,
            "components": form.components,
            "consequences": form.consequences,
            "availability_requirements": form.availability_requirements,
            "ai_identification": form.ai_identification,
            "summary": form.summary,
        }
        try:
            for key, field in file_mapping.items():
                uploaded = request.files.get(field.name) if field.name in request.files else None
                if uploaded and uploaded.filename:
                    csv_files[key] = uploaded.read().decode("utf-8")
            if "bia" not in csv_files:
                flash("The BIA CSV file is required.", "danger")
                return redirect(request.url)
            import_from_csv(csv_files)
            flash("CSV files imported successfully.", "success")
            return redirect(url_for("bia.dashboard"))
        except Exception as exc:  # pragma: no cover - surface errors to UI
            logging.exception("CSV import failed")
            flash(f"CSV import failed: {exc}", "danger")
    return render_template("bia/import_csv.html", form=form)


@bp.route("/change_password", methods=["GET", "POST"])
@login_required
@require_fresh_login(max_age_minutes=15)
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("bia.dashboard"))
        flash("Current password was invalid.", "danger")
    return render_template("bia/change_password.html", form=form)


@bp.route("/export_data_inventory")
@login_required
def export_data_inventory():
    components = Component.query.join(ContextScope).all()
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["BIA", "Component", "Information", "Owner", "Administrator"])
    for component in components:
        writer.writerow(
            [
                component.context_scope.name if component.context_scope else "",
                component.name,
                component.info_type or "N/A",
                component.info_owner or "N/A",
                component.context_scope.technical_administrator if component.context_scope else "N/A",
            ]
        )
    filename = f"Data_Inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(csv_buffer.getvalue(), encoding="utf-8")
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/export_all_consequences")
@login_required
def export_all_consequences():
    export_type = request.args.get("type", "detailed")
    bias = ContextScope.query.all()
    if export_type == "summary":
        summaries = []
        for bia in bias:
            consequences = [consequence for component in bia.components for consequence in component.consequences]
            if not consequences:
                continue
            summaries.append(
                {
                    "bia": bia,
                    "component_count": len(bia.components),
                    "consequence_count": len(consequences),
                    "max_impacts": _summary_impacts(consequences),
                }
            )
        html_content = render_template(
            "bia/export_consequences_summary.html",
            bia_summaries=summaries,
            generated_at=datetime.now(),
        )
        filename = f"CIA_Consequences_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    else:
        all_consequences = []
        for bia in bias:
            for component in bia.components:
                for consequence in component.consequences:
                    all_consequences.append(
                        {
                            "bia": bia,
                            "component": component,
                            "consequence": consequence,
                        }
                    )
        html_content = render_template(
            "bia/export_all_consequences.html",
            consequences=all_consequences,
            generated_at=datetime.now(),
        )
        filename = f"All_CIA_Consequences_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    export_folder = ensure_export_folder()
    file_path = export_folder / filename
    file_path.write_text(html_content, encoding="utf-8")
    return send_file(file_path, as_attachment=True, download_name=filename)


@bp.route("/debug/consequences")
@login_required
def debug_consequences():
    payload = []
    for bia in ContextScope.query.all():
        entry = {
            "bia_name": bia.name,
            "bia_id": bia.id,
            "components": [],
        }
        for component in bia.components:
            comp_data = {
                "component_name": component.name,
                "component_id": component.id,
                "consequences": [],
            }
            for consequence in component.consequences:
                comp_data["consequences"].append(
                    {
                        "security_property": consequence.security_property,
                        "worstcase": consequence.consequence_worstcase,
                        "realistic": consequence.consequence_realisticcase,
                        "category": consequence.consequence_category,
                    }
                )
            entry["components"].append(comp_data)
        payload.append(entry)
    return jsonify(payload)


@bp.route("/bia/<int:item_id>/export/sql")
@login_required
def export_bia_sql(item_id: int):
    item = ContextScope.query.get_or_404(item_id)
    try:
        sql_text = export_to_sql(item)
        filename = f"BIA_Export_{_safe_filename(item.name)}_{datetime.now().strftime('%Y%m%d')}.sql"
        export_folder = ensure_export_folder()
        file_path = export_folder / filename
        file_path.write_text(sql_text, encoding="utf-8")
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as exc:  # pragma: no cover - IO failures are surfaced to users
        logging.exception("SQL export failed")
        flash(f"Failed to export SQL: {exc}", "danger")
        return redirect(url_for("bia.view_item", item_id=item.id))


@bp.route("/import-sql", methods=["GET", "POST"])
@login_required
def import_sql_form():
    form = ImportSQLForm()
    if form.validate_on_submit():
        try:
            import_sql_file(form.sql_file.data)
            flash("SQL file imported successfully.", "success")
            return redirect(url_for("bia.dashboard"))
        except (ValueError, PermissionError) as exc:
            flash(str(exc), "danger")
        except Exception:  # pragma: no cover - defensive logging
            logging.exception("SQL import failed")
            flash("Unexpected error while importing SQL.", "danger")
    return render_template("bia/import_sql_form.html", form=form)


def _apply_context_form(form: ContextScopeForm, context: ContextScope) -> None:
    context.name = form.name.data
    context.responsible = form.responsible.data
    context.coordinator = form.coordinator.data
    context.start_date = form.start_date.data
    context.end_date = form.end_date.data
    context.service_description = form.service_description.data
    context.knowledge = form.knowledge.data
    context.interfaces = form.interfaces.data
    context.mission_critical = form.mission_critical.data
    context.support_contracts = form.support_contracts.data
    context.security_supplier = form.security_supplier.data
    context.user_amount = form.user_amount.data
    context.scope_description = form.scope_description.data
    context.risk_assessment_human = bool(form.risk_assessment_human.data)
    context.risk_assessment_process = bool(form.risk_assessment_process.data)
    context.risk_assessment_technological = bool(form.risk_assessment_technological.data)
    context.ai_model = bool(form.ai_model.data)
    context.project_leader = form.project_leader.data
    context.risk_owner = form.risk_owner.data
    context.product_owner = form.product_owner.data
    context.technical_administrator = form.technical_administrator.data
    context.security_manager = form.security_manager.data
    context.incident_contact = form.incident_contact.data


def _collect_ai_identifications(context: ContextScope) -> dict[int, AIIdentificatie]:
    ai_map: dict[int, AIIdentificatie] = {}
    for component in context.components:
        ai_record = AIIdentificatie.query.filter_by(component_id=component.id).first()
        if ai_record and ai_record.category != "No AI":
            ai_map[component.id] = ai_record
    return ai_map


def _summary_impacts(consequences: list[Consequences]):
    summary = {
        "confidentiality": {"worstcase": None, "realistic": None},
        "integrity": {"worstcase": None, "realistic": None},
        "availability": {"worstcase": None, "realistic": None},
    }
    for consequence in consequences:
        prop = (consequence.security_property or "").strip().lower()
        if prop not in summary:
            continue
        worst = consequence.consequence_worstcase
        realistic = consequence.consequence_realisticcase
        if worst and (
            summary[prop]["worstcase"] is None
            or get_impact_level(worst) > get_impact_level(summary[prop]["worstcase"])
        ):
            summary[prop]["worstcase"] = worst
        if realistic and (
            summary[prop]["realistic"] is None
            or get_impact_level(realistic) > get_impact_level(summary[prop]["realistic"])
        ):
            summary[prop]["realistic"] = realistic
    return summary


def _resolve_user() -> User | None:
    return current_user if isinstance(current_user, User) else None


def _safe_filename(value: str | None) -> str:
    if not value:
        return "bia"
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-", " "}).strip()
    return cleaned.replace(" ", "_") or "bia"
