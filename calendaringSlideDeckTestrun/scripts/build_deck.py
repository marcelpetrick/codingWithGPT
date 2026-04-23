from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "calendaring-linkedin-carousel.pdf"
WIDTH, HEIGHT = 1080, 1350
MARGIN = 86

NAVY = colors.HexColor("#17243A")
INK = colors.HexColor("#223044")
CREAM = colors.HexColor("#F7F0E4")
SAND = colors.HexColor("#E9D9C1")
CORAL = colors.HexColor("#E7644D")
MINT = colors.HexColor("#82B99A")
BLUE = colors.HexColor("#4D7EA8")
GOLD = colors.HexColor("#D5A642")
WHITE = colors.HexColor("#FFFDF8")


SLIDES = [
    {
        "kicker": "A practical team habit",
        "title": "Calendaring is team infrastructure",
        "body": "Not just where meetings live. It is how people understand availability, priorities, and protected time.",
        "accent": CORAL,
        "kind": "cover",
    },
    {
        "num": "01",
        "title": "Availability",
        "body": "Make your working rhythm visible.",
        "bullets": ["Fewer scheduling pings", "Faster meeting decisions", "Less ambiguity across time zones"],
        "accent": BLUE,
    },
    {
        "num": "02",
        "title": "Focus Time",
        "body": "Quiet time only works when it is visible.",
        "bullets": ["Block deep work before the week fills up", "Treat focus blocks with meeting-level respect", "Show busy without explaining every detail"],
        "accent": MINT,
    },
    {
        "num": "03",
        "title": "Collaboration",
        "body": "Calendars reduce coordination friction.",
        "bullets": ["Shared visibility improves timing", "Teams respect constraints earlier", "Meetings land when context fits"],
        "accent": CORAL,
    },
    {
        "num": "04",
        "title": "Prioritization",
        "body": "Your calendar reveals what you actually value.",
        "bullets": ["Important work gets reserved space", "Reactive work stops owning the day", "Weekly reviews keep plans honest"],
        "accent": GOLD,
    },
    {
        "num": "05",
        "title": "Efficiency",
        "body": "A clean calendar lowers cognitive load.",
        "bullets": ["Less back-and-forth", "More predictable workflows", "Fewer forgotten commitments"],
        "accent": BLUE,
    },
    {
        "kicker": "Start small",
        "title": "A 5-minute setup",
        "bullets": ["One reliable source of truth", "Clear event names", "Focus time blocked first", "Availability settings shared", "Friday review for next week"],
        "accent": MINT,
        "kind": "setup",
    },
    {
        "kicker": "Calendaring done right",
        "title": "Not busier. Clearer.",
        "body": "Make time visible. Protect quiet work. Coordinate with less friction.",
        "accent": CORAL,
        "kind": "cta",
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


def text(c, value, x, y, size, font="NotoSans", color=INK, leading=None, max_width=None):
    c.setFont(font, size)
    c.setFillColor(color)
    if max_width is None:
        c.drawString(x, y, value)
        return y - (leading or size * 1.2)

    lines = []
    for paragraph in value.split("\n"):
        lines.extend(wrap_to_width(paragraph, font, size, max_width) or [""])
    step = leading or size * 1.22
    for line in lines:
        c.drawString(x, y, line)
        y -= step
    return y


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


def pill(c, label, x, y, fill, txt=WHITE):
    width = max(260, pdfmetrics.stringWidth(label.upper(), "NotoSans-Bold", 18) + 52)
    c.setFillColor(fill)
    c.roundRect(x, y - 34, width, 52, 24, stroke=0, fill=1)
    text(c, label.upper(), x + 26, y - 16, 18, "NotoSans-Bold", txt)


def draw_background(c, accent):
    c.setFillColor(CREAM)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
    c.setFillColor(SAND)
    c.circle(930, 1230, 210, stroke=0, fill=1)
    c.setFillColor(accent)
    c.circle(1000, 1265, 92, stroke=0, fill=1)
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.42))
    for i in range(6):
        c.roundRect(690 + i * 46, 1108 - i * 34, 130, 18, 9, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#DFCFB8"))
    c.setLineWidth(2)
    for x in range(130, 970, 120):
        c.line(x, 150, x, 1190)
    for y in range(190, 1170, 120):
        c.line(100, y, 980, y)


def draw_footer(c, idx):
    c.setFillColor(NAVY)
    c.roundRect(MARGIN, 56, 210, 38, 19, stroke=0, fill=1)
    text(c, f"{idx:02d} / {len(SLIDES):02d}", MARGIN + 28, 68, 16, "NotoSans-Bold", WHITE)
    text(c, "calendar hygiene for better work", WIDTH - 420, 68, 16, "NotoSans", INK)


def draw_bullets(c, bullets, x, y, accent):
    for bullet in bullets:
        c.setFillColor(accent)
        c.roundRect(x, y - 18, 20, 20, 8, stroke=0, fill=1)
        y = text(c, bullet, x + 46, y - 4, 32, "NotoSans-Bold", INK, max_width=720)
        y -= 34
    return y


def draw_calendar_card(c, accent, x=612, y=705, scale=1):
    c.saveState()
    c.translate(x, y)
    c.scale(scale, scale)
    x, y, w, h = 0, 0, 330, 330
    c.setFillColor(WHITE)
    c.roundRect(x, y, w, h, 36, stroke=0, fill=1)
    c.setFillColor(accent)
    c.roundRect(x, y + h - 82, w, 82, 36, stroke=0, fill=1)
    c.setFillColor(WHITE)
    for bx in (x + 72, x + 248):
        c.roundRect(bx, y + h - 34, 34, 70, 15, stroke=0, fill=1)
    c.setStrokeColor(SAND)
    c.setLineWidth(2)
    for i in range(1, 4):
        c.line(x + 42, y + 52 + i * 54, x + w - 42, y + 52 + i * 54)
        c.line(x + 34 + i * 66, y + 44, x + 34 + i * 66, y + h - 114)
    c.setFillColor(accent)
    c.roundRect(x + 102, y + 150, 118, 42, 16, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.roundRect(x + 230, y + 94, 54, 42, 16, stroke=0, fill=1)
    c.restoreState()


def render_slide(c, slide, idx):
    accent = slide["accent"]
    draw_background(c, accent)

    if slide.get("kind") == "cover":
        pill(c, slide["kicker"], MARGIN, 1172, accent)
        text(c, slide["title"], MARGIN, 1015, 84, "NotoSerif-Bold", NAVY, leading=90, max_width=610)
        text(c, slide["body"], MARGIN, 690, 36, "NotoSans-Bold", INK, leading=48, max_width=640)
        draw_calendar_card(c, accent, 750, 735, 0.72)
        text(c, "Swipe for 5 practical habits", MARGIN, 235, 34, "NotoSans-Bold", accent)
    elif slide.get("kind") == "setup":
        pill(c, slide["kicker"], MARGIN, 1172, accent)
        text(c, slide["title"], MARGIN, 1030, 78, "NotoSerif-Bold", NAVY, max_width=820)
        draw_bullets(c, slide["bullets"], MARGIN, 805, accent)
        c.setFillColor(NAVY)
        c.roundRect(644, 214, 302, 134, 32, stroke=0, fill=1)
        text(c, "Friday", 686, 292, 34, "NotoSerif-Bold", WHITE)
        text(c, "review next week", 686, 248, 22, "NotoSans-Bold", WHITE)
    elif slide.get("kind") == "cta":
        pill(c, slide["kicker"], MARGIN, 1172, NAVY)
        text(c, slide["title"], MARGIN, 1005, 86, "NotoSerif-Bold", NAVY, leading=96, max_width=850)
        text(c, slide["body"], MARGIN, 770, 40, "NotoSans-Bold", INK, leading=54, max_width=760)
        c.setFillColor(accent)
        c.roundRect(MARGIN, 365, 806, 150, 42, stroke=0, fill=1)
        text(c, "Save this for your next weekly reset.", MARGIN + 46, 447, 34, "NotoSans-Bold", WHITE, max_width=710)
        text(c, "Question: What calendar habit would help your team most?", MARGIN, 255, 30, "NotoSans-Bold", INK, max_width=850)
    else:
        draw_calendar_card(c, accent)
        c.setFillColor(accent)
        c.roundRect(MARGIN, 1110, 128, 86, 28, stroke=0, fill=1)
        text(c, slide["num"], MARGIN + 36, 1132, 36, "NotoSans-Bold", WHITE)
        text(c, slide["title"], MARGIN, 975, 86, "NotoSerif-Bold", NAVY, max_width=560)
        text(c, slide["body"], MARGIN, 830, 38, "NotoSans-Bold", INK, max_width=560)
        draw_bullets(c, slide["bullets"], MARGIN, 735, accent)

    draw_footer(c, idx)
    c.showPage()


def main():
    register_fonts()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "previews").mkdir(exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(WIDTH, HEIGHT))
    c.setTitle("Calendaring Is Team Infrastructure")
    c.setAuthor("codingWithGPT test run")
    for idx, slide in enumerate(SLIDES, 1):
        render_slide(c, slide, idx)
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
