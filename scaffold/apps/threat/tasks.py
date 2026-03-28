"""Background tasks for threat modeling — executed by the RQ worker."""
from __future__ import annotations


def generate_pdf_task(model_id: int, html_content: str) -> str:
    """Generate a PDF from pre-rendered HTML and return the saved file path.

    Parameters
    ----------
    model_id:
        Threat model identifier (used to name the output file).
    html_content:
        Fully rendered HTML string (including inlined CSS) ready for Playwright.

    Returns
    -------
    str
        Absolute path to the generated PDF file.
    """
    from scaffold import create_app
    from scaffold.core.pdf_export import html_to_pdf_bytes

    app = create_app()
    with app.app_context():
        from scaffold.apps.bia.utils import ensure_export_folder

        pdf_bytes = html_to_pdf_bytes(html_content)
        export_folder = ensure_export_folder()
        out_path = export_folder / f"threat_model_{model_id}.pdf"
        out_path.write_bytes(pdf_bytes)
        return str(out_path)
