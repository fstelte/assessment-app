"""Routes for the security and assessment tools module."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, request

from ...core.pdf_export import html_to_pdf_bytes

bp = Blueprint(
    "tools",
    __name__,
    url_prefix="/tools",
    template_folder="templates",
)

TOOLS_MENU = [
    {
        "endpoint": "tools.cvss_calculator",
        "label": "CVSS Risk Calculator",
        "description": "Calculate an adjusted risk score from CVSSv3, business impact, and exposure.",
        "icon": "🔢",
    },
    {
        "endpoint": "tools.risk_tool",
        "label": "Risk Description Generator",
        "description": "Build a structured risk description sentence in Dutch.",
        "icon": "📝",
    },
    {
        "endpoint": "tools.ai_act_checker",
        "label": "EU AI Act Compliance Checker",
        "description": "Step-by-step compliance screening against the EU AI Act.",
        "icon": "🤖",
    },
    {
        "endpoint": "tools.cloud_sovereignty",
        "label": "Cloud Sovereignty Framework",
        "description": "Assess your cloud provider against the EU sovereignty requirements.",
        "icon": "☁️",
    },
    {
        "endpoint": "tools.security_roadmap",
        "label": "Cybersecurity Roadmap",
        "description": "Map maturity levels and generate a growth plan per security domain.",
        "icon": "🗺️",
    },
]


@bp.get("/")
def index():
    return render_template("tools/index.html", tools=TOOLS_MENU)


@bp.get("/cvss-calculator")
def cvss_calculator():
    return render_template("tools/cvss_calculator.html")


@bp.get("/risk-tool")
def risk_tool():
    return render_template("tools/risk_tool.html")


@bp.get("/ai-act-checker")
def ai_act_checker():
    return render_template("tools/ai_act_checker.html")


@bp.get("/cloud-sovereignty")
def cloud_sovereignty():
    return render_template("tools/cloud_sovereignty.html")


@bp.get("/security-roadmap")
def security_roadmap():
    return render_template("tools/security_roadmap.html")


@bp.post("/export-pdf")
def export_pdf():
    """Accept an HTML payload and return it as a PDF via Playwright."""
    html_content = request.form.get("html", "")
    if not html_content:
        abort(400)

    filename = request.form.get("filename", "export.pdf")
    # Sanitize filename to alphanumerics, dashes, underscores, and dots only
    safe_filename = "".join(
        ch for ch in filename if ch.isalnum() or ch in {"-", "_", ".", " "}
    ).strip() or "export.pdf"
    if not safe_filename.endswith(".pdf"):
        safe_filename += ".pdf"

    try:
        pdf_bytes = html_to_pdf_bytes(html_content)
    except RuntimeError as exc:
        current_app.logger.error("PDF export failed: %s", exc)
        abort(500)

    response = current_app.response_class(pdf_bytes, mimetype="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    return response
