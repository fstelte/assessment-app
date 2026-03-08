"""Convert standalone tool HTML files to Jinja2 templates extending base.html.

CSP Rules (from security_headers.py):
- script-src: self https://cdn.jsdelivr.net nonce-xxx
- font-src: self https://cdn.jsdelivr.net  (Google Fonts NOT allowed)
"""
import re
from pathlib import Path

TOOLS_DIR = Path("scaffold/tools")
TEMPLATES_DIR = Path("scaffold/apps/tools/templates/tools")

HTML2PDF_CDN = "https://cdn.jsdelivr.net/npm/html2pdf.js@0.10.1/dist/html2pdf.bundle.min.js"

CDN_REWRITES = {
    "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js": HTML2PDF_CDN,
    "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js": "https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js": "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js",
}

TOOLS = {
    "cvss-calculator.html": {"template": "cvss_calculator.html", "title": "CVSS Risk Calculator", "existing_pdf": False, "wide": False},
    "risk-tool.html": {"template": "risk_tool.html", "title": "Risk Description Generator", "existing_pdf": False, "wide": True},
    "ai-act-checker.html": {"template": "ai_act_checker.html", "title": "EU AI Act Compliance Checker", "existing_pdf": True, "wide": False},
    "cloud-sovereignty-framework.html": {"template": "cloud_sovereignty.html", "title": "Cloud Sovereignty Framework", "existing_pdf": True, "wide": False},
    "security-roadmap.html": {"template": "security_roadmap.html", "title": "Cybersecurity Roadmap", "existing_pdf": True, "wide": True},
}

PDF_BUTTON_CVSS = """
  <div id="pdf-export-section" style="display:none; margin-top:1.5rem; text-align:center;">
    <button class="calc-btn" id="exportPdfBtn" onclick="exportPDF()" style="background: var(--accent); max-width:260px;">&#8659; Export as PDF</button>
  </div>"""

PDF_BUTTON_RISK = """
      <div class="card" style="margin-top:16px; text-align:center;">
        <button id="exportPdfBtn" class="btn" onclick="exportPDF()" type="button" style="width:100%;">&#8659; Export als PDF</button>
      </div>"""

PDF_SCRIPT_CVSS = """
  function exportPDF() {
    var btn = document.getElementById("exportPdfBtn");
    var old = btn.textContent;
    btn.textContent = "Generating...";
    btn.disabled = true;
    var el = document.querySelector(".card");
    html2pdf().set({margin:10,filename:"CVSS-"+new Date().toISOString().split("T")[0]+".pdf",image:{type:"jpeg",quality:.95},html2canvas:{scale:2,backgroundColor:"#0f1117"},jsPDF:{unit:"mm",format:"a4"}}).from(el).save().then(function(){btn.textContent=old;btn.disabled=false;});
  }
  document.addEventListener("DOMContentLoaded", function() {
    var calcBtn = document.querySelector(".calc-btn");
    if (calcBtn) {
      calcBtn.addEventListener("click", function() {
        setTimeout(function(){
          var r = document.getElementById("result");
          if (r && r.classList.contains("visible")) document.getElementById("pdf-export-section").style.display="block";
        }, 150);
      });
    }
  });
"""

PDF_SCRIPT_RISK = """
  function exportPDF() {
    var btn = document.getElementById("exportPdfBtn");
    var preview = document.getElementById("preview");
    if (!preview || /Begin met invullen/.test(preview.textContent)) { alert("Vul eerst de velden in."); return; }
    var old = btn.textContent;
    btn.textContent = "Bezig...";
    btn.disabled = true;
    var el = document.querySelector(".wrap");
    html2pdf().set({margin:10,filename:"Risicobeschrijving-"+new Date().toISOString().split("T")[0]+".pdf",image:{type:"jpeg",quality:.95},html2canvas:{scale:2,backgroundColor:"#0f172a"},jsPDF:{unit:"mm",format:"a4"}}).from(el).save().then(function(){btn.textContent=old;btn.disabled=false;});
  }
"""

def rewrite_cdn(tag):
    return re.sub(r"src=['\"]([^'\"]+)['\"]", lambda m: "src=\"" + CDN_REWRITES.get(m.group(1), m.group(1)) + "\"", tag)

def extract_sections(html):
    styles = re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL)
    style = "\n".join(styles)
    head = (re.search(r"<head[^>]*>(.*?)</head>", html, re.DOTALL) or type("",(),{"group":lambda self,x:""})()).group(1) if re.search(r"<head[^>]*>(.*?)</head>", html, re.DOTALL) else ""
    ext_scripts = [rewrite_cdn(s) for s in re.findall(r"<script\s+src=['\"][^'\"]+['\"][^>]*></script>", head) if "tailwindcss.com" not in s]
    ext_links = [lnk for lnk in re.findall(r"<link\b[^>]*/>", head) if "fonts.google" not in lnk and "fonts.gstatic" not in lnk and ("stylesheet" in lnk or "preconnect" in lnk)]
    body_m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL)
    body = body_m.group(1) if body_m else html
    body = re.sub(r"<header\b[^>]*>.*?</header>", "", body, flags=re.DOTALL)
    return style.strip(), ext_scripts, ext_links, body.strip()

def extract_inline_scripts(body):
    found = []
    def capture(m):
        if "src=" in (m.group(1) or ""): return m.group(0)
        found.append(m.group(2)); return ""
    cleaned = re.sub(r"<script(\b[^>]*)>([\s\S]*?)</script>", capture, body)
    return cleaned.strip(), found

def scope_css(style):
    # Replace standalone body selector only — not .foo-body or body-wrap etc.
    r = re.sub(r"(?<![a-zA-Z0-9_-])body(?![a-zA-Z0-9_-])\s*\{", ".tool-body-wrap {", style)
    # html, .tool-body-wrap → just keep html{} to preserve html-level vars
    r = re.sub(r"html\s*,\s*\.tool-body-wrap\s*\{", "html {", r)
    r = re.sub(r"\bheader\b\s*\{[^}]*\}", "/* header suppressed */", r)
    r = re.sub(r"\bheader\b[\s>~+.#\w\[,:]*\{[^}]*\}", "", r)
    return r

def make_tpl(src_name, cfg, style, ext_scripts, ext_links, body):
    title = cfg["title"]
    main_cls = "w-full px-4 sm:px-6 grow" if cfg["wide"] else "container mx-auto max-w-4xl px-4 sm:px-6 grow"
    scoped = scope_css(style)
    if src_name == "cvss-calculator.html":
        body = re.sub(r"(<!-- Result -->[\s\S]*?</div>\s*</div>)", lambda m: m.group(0) + PDF_BUTTON_CVSS, body, count=1)
    elif src_name == "risk-tool.html":
        body = body.rstrip()
        if body.endswith("</div>"): body = body[:-6] + PDF_BUTTON_RISK + "\n  </div>"
    clean, inline = extract_inline_scripts(body)
    css_lines = [f"    {lnk}" for lnk in ext_links] + ["    <style nonce=\"{{ csp_nonce }}\">", scoped, "    </style>"]
    js_lines = [f"    {s}" for s in ext_scripts]
    if not cfg["existing_pdf"]:
        js_lines.append(f"    <script src=\"{HTML2PDF_CDN}\"></script>")
    for sc in inline:
        js_lines.append(f"<script nonce=\"{{{{ csp_nonce }}}}\">{sc}\n</script>")
    if src_name == "cvss-calculator.html":
        js_lines.append(f"<script nonce=\"{{{{ csp_nonce }}}}\">{PDF_SCRIPT_CVSS}\n</script>")
    elif src_name == "risk-tool.html":
        js_lines.append(f"<script nonce=\"{{{{ csp_nonce }}}}\">{PDF_SCRIPT_RISK}\n</script>")
    return (
        "{{% extends \"base.html\" %}}\n{{% block title %}}{title}{{% endblock %}}\n\n"
        "{{% block main_container_class %}}{main_cls}{{% endblock %}}\n\n"
        "{{% block extra_css %}}\n{css}\n{{% endblock %}}\n\n"
        "{{% block content %}}\n<div class=\"tool-body-wrap py-6\">\n{clean}\n</div>\n{{% endblock %}}\n\n"
        "{{% block extra_js %}}\n{js}\n{{% endblock %}}\n"
    ).format(title=title, main_cls=main_cls, css="\n".join(css_lines), clean=clean, js="\n".join(js_lines))

def main():
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    for src_name, cfg in TOOLS.items():
        src_path = TOOLS_DIR / src_name
        if not src_path.exists():
            print(f"SKIP: {src_path}")
            continue
        html = src_path.read_text(encoding="utf-8")
        style, ext_scripts, ext_links, body = extract_sections(html)
        out = make_tpl(src_name, cfg, style, ext_scripts, ext_links, body)
        out_path = TEMPLATES_DIR / cfg["template"]
        out_path.write_text(out, encoding="utf-8")
        print(f"OK: {out_path}")
    print("Done.")

if __name__ == "__main__":
    main()
