# This script generates a 10-slide (pages) PDF, each 1080x1080 pixels,
# with a bright pink/violet & neon green color scheme, Comic Sans (or a playful fallback),
# and your exact 10-point ticket workflow text. It saves to /mnt/data/ticket_workflow_slides.pdf

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import os, sys, textwrap

W = H = 1080  # pixels/points at 72dpi for PDF
OUTPUT_PATH = "/mnt/data/ticket_workflow_slides.pdf"

# --- Color palette: bright pink/violet + neon green
PINK = HexColor("#FF00CC")
VIOLET = HexColor("#7A00FF")
NEON_GREEN = HexColor("#39FF14")
DARK_VIOLET = HexColor("#3B0077")
DEEP_PINK = HexColor("#FF0099")

# --- Try to register a playful font (Comic Sans if available), else DejaVu Sans, else Helvetica
def try_register_fonts():
    font_candidates = [
        # Comic Sans variants & Comic Neue
        ("ComicSansMS", ["/usr/share/fonts/truetype/msttcorefonts/Comic_Sans_MS.ttf",
                         "/usr/share/fonts/truetype/msttcorefonts/comic.ttf",
                         "/usr/share/fonts/truetype/microsoft/Comic_Sans_MS.ttf",
                         "/usr/share/fonts/truetype/comic-sans-ms/ComicSansMS3.ttf",
                         "/usr/share/fonts/truetype/Comic_Sans_MS.ttf",
                         "/Library/Fonts/Comic Sans MS.ttf",
                         os.path.expanduser("~/Library/Fonts/Comic Sans MS.ttf")]),
        ("ComicNeue-Bold", ["/usr/share/fonts/truetype/comicneue/ComicNeue-Bold.ttf",
                            "/usr/share/fonts/TTF/ComicNeue-Bold.ttf"]),
        # DejaVu & Noto as robust Unicode fallbacks
        ("DejaVuSans", ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"]),
        ("NotoSans", ["/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"]),
        ("ArialUnicode", ["/usr/share/fonts/truetype/arphic/ukai.ttc", # unlikely but try
                          "/usr/share/fonts/truetype/arial-unicode-ms/ArialUnicodeMS.ttf"]),
    ]
    for name, paths in font_candidates:
        for p in paths:
            if os.path.exists(p):
                try:
                    pdfmetrics.registerFont(TTFont(name, p))
                    return name
                except Exception as e:
                    pass
    # Fallback to Helvetica (built-in Type 1)
    return "Helvetica"

FONT_NAME = try_register_fonts()

# For headings we can use bold-like style: if ComicNeue-Bold available, great; else same font
FONT_BOLD = FONT_NAME

# --- Slide data (exact text requested) ---
slides = [
    {
        "title": "1) Grundprinzip: Alles ist ein Ticket",
        "bullets": [
            "End-to-End Traceability: Requirement → Ticket → MR → Release.",
            "Auch spontane Ideen oder Stakeholder-Anfragen: erst Ticket, dann Arbeit."
        ]
    },
    {
        "title": "2) Ticket-Inhalt & Qualität",
        "bullets": [
            "Pflicht: Beschreibung, Anforderungen, Erwartung, techn. Details.",
            "Tickets mit unklaren Anforderungen werden nicht gestartet."
        ]
    },
    {
        "title": "3) Aufwand & Planung",
        "bullets": [
            "Jedes Ticket: 3-Punkt-Aufwandsschätzung + Due Date.",
            "Diese Daten ermöglichen realistische Planung in Sprints/Milestones."
        ]
    },
    {
        "title": "4) Ticket-Pflege",
        "bullets": [
            "Änderungen dokumentieren: Kommentare, neue Infos → Ticket-Update.",
            "Scope-Änderungen = neue Schätzung (nicht „still“ weitermachen)."
        ]
    },
    {
        "title": "5) Verantwortlichkeiten",
        "bullets": [
            "Jedes Ticket hat eine*n klare*n Verantwortliche*n.",
            "Dev-Team trägt die Durchführungsverantwortung, Stakeholder geben Input."
        ]
    },
    {
        "title": "6) Milestones als Container",
        "bullets": [
            "Tickets werden Milestones zugeordnet (Start- & Enddatum).",
            "Scope eines Milestones bleibt fix während des Sprints; Änderungen nur im Notfall."
        ]
    },
    {
        "title": "7) Umgang mit Überlauf",
        "bullets": [
            "Nicht fertig? Prüfen: Restsplit in neues Ticket (Ausnahme) oder verschieben.",
            "Ziel: Planbarkeit statt Überraschungen."
        ]
    },
    {
        "title": "8) Merge Requests & Tickets",
        "bullets": [
            "MR immer mit Ticket verknüpft („Closes #123“).",
            "Optimal: 1 MR pro Ticket, MR-Text referenziert Ticketnummer."
        ]
    },
    {
        "title": "9) Ticket-Abschluss",
        "bullets": [
            "Schließen erst, wenn alle Anforderungen erfüllt.",
            "DoD: Requirements erfüllt, Tests/Docs ok, MR gemerged."
        ]
    },
    {
        "title": "10) Effizienz & Taktung",
        "bullets": [
            "Milestones ≥ 2 Wochen – kürzere bedeuten Overhead.",
            "Fokus auf Planbarkeit, Sichtbarkeit, Zuverlässigkeit für Stakeholder."
        ]
    },
]

# --- Layout helpers ---
def draw_background(c, idx):
    # Alternate loud backgrounds: stripes/gradients vibe with neon contrast
    if idx % 2 == 0:
        bg1, bg2 = PINK, NEON_GREEN
    else:
        bg1, bg2 = VIOLET, NEON_GREEN

    # Big diagonal blocks
    c.setFillColor(bg1)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(bg2)
    c.saveState()
    c.translate(W*0.2, -H*0.1)
    c.rotate(35)
    c.rect(0, 0, W*1.2, H*0.5, fill=1, stroke=0)
    c.restoreState()

    # Doodles: circles
    c.setFillColor(white)
    for i in range(6):
        r = 24 + 10*i
        c.circle(W - 120 - i*30, H - 120 + (i%2)*10, r, fill=0, stroke=1)

def fit_text_lines(text, font_name, font_size, max_width):
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

def draw_slide(c, idx, title, bullets):
    # Choose high-contrast text color against background
    text_color = white if idx % 2 == 0 else white
    accent = black if idx % 2 == 0 else black

    draw_background(c, idx)

    # Title
    title_size = 60
    c.setFont(FONT_BOLD, title_size)
    c.setFillColor(text_color)
    title_max_width = W - 160
    title_lines = fit_text_lines(title, FONT_BOLD, title_size, title_max_width)

    y = H - 140
    for line in title_lines:
        c.drawString(80, y, line)
        y -= title_size * 1.1

    # Funny subtitle ribbon
    c.setFillColor(accent)
    c.rect(70, y + 10, 280, 14, fill=1, stroke=0)
    c.setFillColor(text_color)
    c.setFont(FONT_NAME, 16)
    c.drawString(80, y + 12, "Ticket-Workflow • 1080×1080 • 💥")

    # Bullets
    y -= 40
    bullet_font_size = 34
    c.setFont(FONT_NAME, bullet_font_size)
    bullet_box_width = W - 160

    for b in bullets:
        y -= 24
        # fun bullet prefix
        prefix = "• "
        # Wrap each bullet
        lines = fit_text_lines(prefix + b, FONT_NAME, bullet_font_size, bullet_box_width)
        for j, line in enumerate(lines):
            c.drawString(80, y, line)
            y -= bullet_font_size * 1.15
        y -= 8  # extra space between bullets

    # Footer page number
    c.setFillColor(text_color)
    c.setFont(FONT_NAME, 18)
    c.drawRightString(W - 30, 30, f"{idx+1}/10")

# --- Generate PDF ---
c = canvas.Canvas(OUTPUT_PATH, pagesize=(W, H))

for i, slide in enumerate(slides):
    draw_slide(c, i, slide["title"], slide["bullets"])
    c.showPage()

c.save()

OUTPUT_PATH
