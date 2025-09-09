#!/usr/bin/env python3
import argparse
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -----------------------------
# Defaults
# -----------------------------
DEFAULT_W = 1080
DEFAULT_H = 1080
DEFAULT_OUTPUT = "ticket_workflow_slides_v2.pdf"

# Colors
PINK = HexColor("#FF00CC")
VIOLET = HexColor("#7A00FF")
NEON_GREEN = HexColor("#39FF14")

# Example slides (shortened for brevity)
slides = [
    {"title": "1) Grundprinzip: Alles ist ein Ticket",
     "bullets": [
         "End-to-End Traceability: Requirement → Ticket → MR → Release.",
         "Auch spontane Ideen oder Stakeholder-Anfragen: erst Ticket, dann Arbeit."
     ]},
    {"title": "2) Ticket-Inhalt & Qualität",
     "bullets": [
         "Pflicht: Beschreibung, Anforderungen, Erwartung, techn. Details.",
         "Tickets mit unklaren Anforderungen werden nicht gestartet."
     ]},
]


def draw_background(c: canvas.Canvas, idx: int, W: int, H: int) -> None:
    if idx % 2 == 0:
        bg1, bg2 = PINK, NEON_GREEN
    else:
        bg1, bg2 = VIOLET, NEON_GREEN
    c.setFillColor(bg1)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(bg2)
    c.saveState()
    c.translate(W * 0.2, -H * 0.1)
    c.rotate(35)
    c.rect(0, 0, W * 1.2, H * 0.5, fill=1, stroke=0)
    c.restoreState()


def fit_text_lines(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_slide(c: canvas.Canvas, idx: int, title: str, bullets: list[str], W: int, H: int) -> None:
    text_color = white
    draw_background(c, idx, W, H)

    # Title
    title_size = 60
    c.setFont("Helvetica-Bold", title_size)
    c.setFillColor(text_color)
    title_max_width = W - 160
    title_lines = fit_text_lines(title, "Helvetica-Bold", title_size, title_max_width)

    y = H - (H * 0.2)
    for line in title_lines:
        c.drawString(80, y, line)
        y -= title_size * 1.1

    # Bullets
    y -= 40
    bullet_font_size = 34
    c.setFont("Helvetica", bullet_font_size)
    bullet_box_width = W - 160

    for b in bullets:
        y -= 24
        lines = fit_text_lines("• " + b, "Helvetica", bullet_font_size, bullet_box_width)
        for line in lines:
            c.drawString(80, y, line)
            y -= bullet_font_size * 1.15
        y -= 8

    # Footer page number
    c.setFillColor(text_color)
    c.setFont("Helvetica", 18)
    c.drawRightString(W - 30, 30, f"{idx + 1}/{len(slides)}")


# -----------------------------
# CLI / main
# -----------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate the ticket workflow slides PDF.")
    p.add_argument(
        "--out",
        type=str,
        default=DEFAULT_OUTPUT,
        help="Output PDF filename or path (default: ticket_workflow_slides_v2.pdf)",
    )
    p.add_argument("--width", type=int, default=DEFAULT_W, help="Page width in points (default: 1080)")
    p.add_argument("--height", type=int, default=DEFAULT_H, help="Page height in points (default: 1080)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    W, H = int(args.width), int(args.height)

    out_path = Path(args.out)
    if out_path.is_dir():
        out_path = out_path / DEFAULT_OUTPUT
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out_path), pagesize=(W, H))
    for i, slide in enumerate(slides):
        draw_slide(c, i, slide["title"], slide["bullets"], W, H)
        c.showPage()
    c.save()

    print(f"Wrote {out_path.resolve()}")


if __name__ == "__main__":
    main()
