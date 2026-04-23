from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "calendaring-linkedin-carousel.pdf"
WIDTH, HEIGHT = 1080, 1350
MARGIN = 86
FOOTER = "solutions; not code"

PAPER = colors.HexColor("#F2F7EF")
PAPER_2 = colors.HexColor("#E5F0E3")
GRID = colors.HexColor("#D5E4D1")
INK = colors.HexColor("#18372E")
MUTED = colors.HexColor("#4D6A5E")
DEEP = colors.HexColor("#24483C")
SAGE = colors.HexColor("#AFCDB4")
MINT = colors.HexColor("#CFE4D0")
LEAF = colors.HexColor("#6B9F78")
WHITE = colors.HexColor("#FFFFFA")


SLIDES = [
    {
        "kicker": "Software teams",
        "title": "Calendars are team APIs",
        "body": "They expose when people can talk, when focus should be protected, and when stakeholders get predictable access.",
        "bullets": [
            "When can we talk?",
            "When should we not interrupt?",
            "When do stakeholders get access?",
        ],
        "accent": LEAF,
        "kind": "cover",
    },
    {
        "num": "01",
        "title": "Protect build time",
        "body": "Architecture, debugging, reviews, and delivery need uninterrupted blocks. If deep work is not scheduled, it gets consumed.",
        "bullets": [
            "Reserve focus blocks before the week fills up",
            "Keep them visible, not overly detailed",
            "Treat them as real commitments",
        ],
        "accent": LEAF,
    },
    {
        "num": "02",
        "title": "Make collaboration predictable",
        "body": "The goal is not no meetings. The goal is fewer surprise interruptions and clearer windows for conversation.",
        "bullets": [
            "Cluster team syncs into agreed windows",
            "Use office hours for ad-hoc technical questions",
            "Prefer async when no decision is needed",
        ],
        "accent": colors.HexColor("#7DAE87"),
    },
    {
        "num": "03",
        "title": "Give stakeholders clear access",
        "body": "Stakeholders should not have to chase the team. They also should not fragment every developer's day.",
        "bullets": [
            "Offer recurring stakeholder windows",
            "Share realistic review and decision availability",
            "Route urgent topics through one escalation path",
        ],
        "accent": colors.HexColor("#88B893"),
    },
    {
        "num": "04",
        "title": "Make boundaries explicit",
        "body": "A good calendar creates trust: available means available, focus means focus, and emergencies stay rare.",
        "bullets": [
            "Use clear labels: Focus, Review, Pairing, Stakeholder Sync",
            "Mark focus time as busy",
            "Make collaboration possible without sacrificing focus",
        ],
        "accent": colors.HexColor("#679973"),
    },
]


def register_fonts():
    fonts = {
        "NotoSans": "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "NotoSans-Bold": "/usr/share/fonts/noto/NotoSans-Bold.ttf",
        "NotoSerif-Bold": "/usr/share/fonts/noto/NotoSerif-Bold.ttf",
    }
    for name, path in fonts.items():
        pdfmetrics.registerFont(TTFont(name, path))


def wrap_to_width(value, font, size, max_width):
    words = value.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdfmetrics.stringWidth(candidate, font, size) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def text(c, value, x, y, size, font="NotoSans", color=INK, leading=None, max_width=None):
    c.setFont(font, size)
    c.setFillColor(color)
    if max_width is None:
        c.drawString(x, y, value)
        return y - (leading or size * 1.2)

    step = leading or size * 1.22
    for paragraph in value.split("\n"):
        for line in wrap_to_width(paragraph, font, size, max_width) or [""]:
            c.drawString(x, y, line)
            y -= step
    return y


def pill(c, label, x, y, fill, txt=WHITE):
    width = max(230, pdfmetrics.stringWidth(label.upper(), "NotoSans-Bold", 17) + 54)
    c.setFillColor(fill)
    c.roundRect(x, y - 34, width, 52, 24, stroke=0, fill=1)
    text(c, label.upper(), x + 27, y - 16, 17, "NotoSans-Bold", txt)


def draw_background(c, accent):
    c.setFillColor(PAPER)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)

    c.setFillColor(PAPER_2)
    c.circle(912, 1185, 260, stroke=0, fill=1)
    c.setFillColor(colors.Color(0.69, 0.80, 0.70, alpha=0.48))
    c.circle(1016, 1268, 112, stroke=0, fill=1)

    c.setStrokeColor(GRID)
    c.setLineWidth(2)
    for x in range(135, 980, 132):
        c.line(x, 190, x, 1136)
    for y in range(238, 1110, 132):
        c.line(100, y, 980, y)

    c.setFillColor(colors.Color(1, 1, 1, alpha=0.34))
    for i in range(5):
        c.roundRect(700 + i * 44, 1078 - i * 40, 154, 18, 9, stroke=0, fill=1)

    c.setFillColor(accent)
    c.roundRect(912, 184, 86, 86, 24, stroke=0, fill=1)
    c.setFillColor(MINT)
    c.roundRect(820, 215, 58, 58, 18, stroke=0, fill=1)


def draw_footer(c, idx):
    c.setFillColor(DEEP)
    c.roundRect(MARGIN, 56, 198, 40, 20, stroke=0, fill=1)
    text(c, f"{idx:02d} / {len(SLIDES):02d}", MARGIN + 28, 69, 16, "NotoSans-Bold", WHITE)
    text(c, FOOTER, WIDTH - 356, 69, 19, "NotoSans-Bold", DEEP)


def draw_calendar_panel(c, accent, x, y, w=338, h=300):
    c.setFillColor(WHITE)
    c.roundRect(x, y, w, h, 34, stroke=0, fill=1)
    c.setFillColor(MINT)
    c.roundRect(x, y + h - 78, w, 78, 34, stroke=0, fill=1)
    c.setFillColor(accent)
    c.roundRect(x + 36, y + h - 50, 142, 22, 11, stroke=0, fill=1)

    c.setStrokeColor(GRID)
    c.setLineWidth(2)
    for i in range(1, 4):
        c.line(x + 38, y + 54 + i * 46, x + w - 38, y + 54 + i * 46)
    for i in range(1, 4):
        c.line(x + 40 + i * 64, y + 46, x + 40 + i * 64, y + h - 104)

    c.setFillColor(accent)
    c.roundRect(x + 72, y + 138, 126, 38, 14, stroke=0, fill=1)
    c.setFillColor(DEEP)
    c.roundRect(x + 216, y + 88, 62, 38, 14, stroke=0, fill=1)


def draw_bullets(c, bullets, x, y, accent, max_width=770):
    for bullet in bullets:
        c.setFillColor(accent)
        c.roundRect(x, y - 17, 20, 20, 8, stroke=0, fill=1)
        y = text(c, bullet, x + 44, y - 3, 29, "NotoSans-Bold", INK, leading=37, max_width=max_width)
        y -= 28
    return y


def render_cover(c, slide, idx):
    accent = slide["accent"]
    draw_background(c, accent)
    pill(c, slide["kicker"], MARGIN, 1172, DEEP)
    text(c, slide["title"], MARGIN, 1010, 86, "NotoSerif-Bold", INK, leading=90, max_width=760)
    text(c, slide["body"], MARGIN, 768, 35, "NotoSans-Bold", MUTED, leading=45, max_width=620)
    draw_bullets(c, slide["bullets"], MARGIN, 575, accent, max_width=790)
    draw_calendar_panel(c, accent, 716, 782, 292, 260)
    text(c, "5 slides for teams that need both flow and focus", MARGIN, 238, 30, "NotoSans-Bold", accent, max_width=780)
    draw_footer(c, idx)
    c.showPage()


def render_factor(c, slide, idx):
    accent = slide["accent"]
    draw_background(c, accent)
    pill(c, slide["num"], MARGIN, 1172, accent)
    title_end = text(c, slide["title"], MARGIN, 1002, 68, "NotoSerif-Bold", INK, leading=74, max_width=600)
    body_y = min(802, title_end - 14)
    body_end = text(c, slide["body"], MARGIN, body_y, 33, "NotoSans-Bold", MUTED, leading=43, max_width=790)
    bullet_y = min(604, body_end - 34)
    draw_bullets(c, slide["bullets"], MARGIN, bullet_y, accent, max_width=800)
    draw_calendar_panel(c, accent, 722, 916, 286, 246)
    draw_footer(c, idx)
    c.showPage()


def main():
    register_fonts()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "previews").mkdir(exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(WIDTH, HEIGHT))
    c.setTitle("Calendars Are Team APIs")
    c.setAuthor("codingWithGPT test run")
    for idx, slide in enumerate(SLIDES, 1):
        if slide.get("kind") == "cover":
            render_cover(c, slide, idx)
        else:
            render_factor(c, slide, idx)
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
