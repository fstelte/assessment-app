"""PDF export utility using Playwright (headless Chromium).

Usage::

    from scaffold.core.pdf_export import html_to_pdf_bytes

    pdf_bytes = html_to_pdf_bytes(html_content)
    response = current_app.response_class(pdf_bytes, mimetype="application/pdf")
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def html_to_pdf_bytes(html_content: str) -> bytes:
    """Convert an HTML string to a PDF byte string using Playwright.

    The function uses the Playwright sync API with a headless Chromium browser.
    CSS is inlined via ``page.set_content()`` so no external files are needed.

    Parameters
    ----------
    html_content:
        Fully rendered HTML document (including any inlined CSS).

    Returns
    -------
    bytes
        Raw PDF file contents.

    Raises
    ------
    RuntimeError
        If Playwright or the Chromium browser is not available.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright is required for PDF export. "
            "Install it with: poetry add playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            page.set_content(html_content, wait_until="networkidle")

            # Remove overflow scroll containers so no content is clipped in the PDF.
            # Tables with overflow-x-auto create scroll boxes that Playwright would
            # otherwise cut off at the container edge.
            # Also disable backdrop-filter: Chromium's PDF/print pipeline does NOT
            # support backdrop-filter — elements that use it become invisible in the
            # rendered PDF (known Chromium limitation). We replace with solid backgrounds.
            page.add_style_tag(content="""
                @page { margin: 0 !important; size: auto; }
                * {
                    backdrop-filter: none !important;
                    -webkit-backdrop-filter: none !important;
                }
                .bia-hero-metric {
                    background: rgba(255, 255, 255, 0.18) !important;
                    border: 1px solid rgba(255, 255, 255, 0.25) !important;
                }
                .bia-item-hero {
                    overflow: visible !important;
                }
                .overflow-x-auto,
                .overflow-x-scroll {
                    overflow-x: visible !important;
                }
                table {
                    width: 100% !important;
                    table-layout: auto !important;
                }
            """)

            # Measure the full rendered dimensions so the PDF has no page breaks
            # and no horizontal clipping regardless of content size.
            # Add a small buffer to prevent pixel-rounding from spilling onto a
            # second page when Chromium switches to print layout.
            dims = page.evaluate("""
                () => ({
                    width: Math.max(
                        document.documentElement.scrollWidth,
                        document.body ? document.body.scrollWidth : 0
                    ),
                    height: Math.max(
                        document.documentElement.scrollHeight,
                        document.body ? document.body.scrollHeight : 0
                    ) + 10
                })
            """)

            pdf_bytes = page.pdf(
                width=f"{dims['width']}px",
                height=f"{dims['height']}px",
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
            )
        finally:
            browser.close()

    logger.debug("PDF generated successfully (%d bytes)", len(pdf_bytes))
    return pdf_bytes
