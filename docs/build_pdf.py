"""Convert the Kaggle writeup Markdown into a styled PDF.

Pure-Python pipeline (no system deps): markdown -> HTML -> PDF via xhtml2pdf.
The ASCII architecture diagram in the Markdown is replaced, for the PDF only,
by a clean box-flow diagram (the Markdown stays readable on GitHub).

Run from the project root:  python docs/build_pdf.py
"""

import re
from pathlib import Path

import markdown
from xhtml2pdf import pisa

DOCS = Path(__file__).resolve().parent
SRC = DOCS / "kaggle-writeup.md"
OUT = DOCS / "TrustLens-Kaggle-Writeup.pdf"

CSS = """
@page { size: A4; margin: 2cm 2.2cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt;
       color: #1a1a1a; line-height: 1.45; }
h1 { font-size: 20pt; color: #0b3d91; margin: 0 0 2pt 0; }
h2 { font-size: 13pt; color: #0b3d91; border-bottom: 1px solid #cdd7e5;
     padding-bottom: 3pt; margin: 16pt 0 6pt 0; }
h3 { font-size: 11pt; color: #21436b; margin: 12pt 0 4pt 0; }
p  { margin: 0 0 7pt 0; text-align: justify; }
strong { color: #0b3d91; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0 10pt 0; font-size: 9.5pt; }
th { background: #0b3d91; color: #fff; text-align: left; padding: 4pt 6pt; }
td { border-bottom: 1px solid #d6dde7; padding: 4pt 6pt; vertical-align: top; }
ol, ul { margin: 0 0 8pt 0; padding-left: 16pt; }
li { margin-bottom: 3pt; }
pre { background: #f4f6f9; border: 1px solid #d6dde7; border-radius: 3px;
      padding: 7pt; font-family: Courier, monospace; font-size: 8.2pt;
      color: #20303f; white-space: pre-wrap; }
hr { border: 0; border-top: 1px solid #cdd7e5; margin: 10pt 0; }

/* Architecture diagram image */
div.arch { text-align: center; margin: 8pt 0 12pt 0; }
div.arch img { width: 380pt; }
"""

# Replace the ASCII block in the PDF with the rendered architecture diagram PNG.
ARCH_HTML = '<div class="arch"><img src="architecture-diagram.png" /></div>'


def _link_callback(uri, rel):
    """Resolve local asset references (e.g. the diagram PNG) to absolute paths."""
    candidate = DOCS / Path(uri).name
    return str(candidate) if candidate.exists() else uri


def main() -> None:
    md_text = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    # Replace the ASCII architecture <pre> block with the clean box diagram.
    body = re.sub(
        r"<pre>.*?Router Agent.*?</pre>",
        ARCH_HTML,
        body,
        count=1,
        flags=re.DOTALL,
    )

    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"

    with OUT.open("wb") as fh:
        result = pisa.CreatePDF(html, dest=fh, encoding="utf-8", link_callback=_link_callback)

    if result.err:
        raise SystemExit(f"PDF generation failed with {result.err} error(s).")
    print(f"PDF written: {OUT}")


if __name__ == "__main__":
    main()
