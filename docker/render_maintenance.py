from __future__ import annotations

import os
from pathlib import Path
from string import Template


def render() -> None:
    template_path = Path(os.getenv("MAINTENANCE_TEMPLATE_PATH", "/app/docker/templates/maintenance.html.tmpl"))
    if not template_path.exists():
        raise FileNotFoundError(f"maintenance template not found: {template_path}")

    contact_email = os.getenv("MAINTENANCE_CONTACT_EMAIL", "support@example.com")
    contact_label = os.getenv("MAINTENANCE_CONTACT_LABEL", contact_email)
    contact_link = os.getenv("MAINTENANCE_CONTACT_LINK") or f"mailto:{contact_email}"

    payload = Template(template_path.read_text(encoding="utf-8")).safe_substitute(
        CONTACT_EMAIL=contact_email,
        CONTACT_LABEL=contact_label,
        CONTACT_LINK=contact_link,
    )

    flask_output = Path(os.getenv("MAINTENANCE_FLASK_OUTPUT", "/app/scaffold/static/maintenance.html"))
    shared_output = Path(os.getenv("MAINTENANCE_SHARED_OUTPUT", "/maintenance/maintenance.html"))

    for target in {flask_output, shared_output}:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    render()
