"""Generate docs/architecture-diagram.png — the TrustLens architecture flow.

Pure-Python (Pillow only). Run from the project root:
    python docs/build_diagram.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DOCS = Path(__file__).resolve().parent
OUT = DOCS / "architecture-diagram.png"

# ---- Palette ----
BG = "#ffffff"
NAVY = "#0b3d91"
BOX_FILL = "#eef3fb"
BOX_BORDER = "#0b3d91"
TEXT = "#14253f"
SUB = "#4a5a72"
ACCENT = "#1769d1"

# ---- Fonts (Arial on Windows) ----
def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

F_TITLE = _font("C:/Windows/Fonts/arialbd.ttf", 40)
F_NAME = _font("C:/Windows/Fonts/arialbd.ttf", 26)
F_DESC = _font("C:/Windows/Fonts/arial.ttf", 19)
F_TAG = _font("C:/Windows/Fonts/arial.ttf", 16)

# ---- Layout ----
W = 1040
MARGIN_TOP = 110
BOX_W = 720
BOX_X = (W - BOX_W) // 2
GAP = 56          # vertical gap (arrow lives here)
PAD = 18          # inner box padding

# Each node: (name, [desc lines], side-tag or None)
NODES = [
    ("User input", ["Free text: article, URL, claim, or monitoring topic"], None),
    ("Router Agent", ['Classifies the input: "public" or "newsroom"'], "Gemini Flash Lite"),
    ("Scout Agent", ["Searches the web via the Tavily MCP Server",
                     "Never fabricates a source"], "MCP Server"),
    ("Verifier Agent", ["Separates facts / opinions / unsupported / refuted claims",
                        "Detects contradictions between sources"], "Gemini Flash"),
    ("Scorer Agent", ["Public:  verdict + deterministic trust score + explanation",
                      "Newsroom:  structured journalistic brief"], "Gemini Flash"),
    ("JSON response", ["Mode-adapted output, in the user's language"], None),
]


def box_height(desc_lines):
    return PAD * 2 + 34 + 26 * len(desc_lines)


def rounded(draw, xy, radius, **kw):
    draw.rounded_rectangle(xy, radius=radius, **kw)


def arrow(draw, cx, y0, y1):
    draw.line([(cx, y0), (cx, y1 - 11)], fill=NAVY, width=4)
    draw.polygon([(cx - 9, y1 - 12), (cx + 9, y1 - 12), (cx, y1)], fill=NAVY)


def main():
    # Compute total height
    total = MARGIN_TOP
    heights = [box_height(d) for _, d, _ in NODES]
    for i, h in enumerate(heights):
        total += h
        if i < len(NODES) - 1:
            total += GAP
    total += 60  # bottom margin

    img = Image.new("RGB", (W, total), BG)
    d = ImageDraw.Draw(img)

    # Title
    d.text((BOX_X, 38), "TrustLens — Multi-Agent Architecture", font=F_TITLE, fill=NAVY)
    d.line([(BOX_X, 92), (BOX_X + BOX_W, 92)], fill="#cdd7e5", width=2)

    y = MARGIN_TOP
    for i, (name, desc, tag) in enumerate(NODES):
        h = heights[i]
        # Box
        rounded(d, (BOX_X, y, BOX_X + BOX_W, y + h), 12,
                fill=BOX_FILL, outline=BOX_BORDER, width=3)
        # Name
        d.text((BOX_X + PAD, y + PAD), name, font=F_NAME, fill=NAVY)
        # Description lines
        ty = y + PAD + 36
        for line in desc:
            d.text((BOX_X + PAD, ty), line, font=F_DESC, fill=TEXT)
            ty += 26
        # Side tag (model / tool)
        if tag:
            tw = d.textlength(tag, font=F_TAG)
            tag_x = BOX_X + BOX_W + 16
            ty2 = y + h // 2 - 14
            d.rounded_rectangle((tag_x, ty2, tag_x + tw + 20, ty2 + 28), radius=14,
                                fill="#ffffff", outline=ACCENT, width=2)
            d.text((tag_x + 10, ty2 + 5), tag, font=F_TAG, fill=ACCENT)

        # Arrow to next box
        if i < len(NODES) - 1:
            arrow(d, W // 2, y + h, y + h + GAP)
        y += h + GAP

    img.save(OUT, "PNG")
    print(f"Diagram written: {OUT}  ({OUT.stat().st_size // 1024} KB, {img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
