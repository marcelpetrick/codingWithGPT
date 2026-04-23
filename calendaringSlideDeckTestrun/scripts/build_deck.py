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

PAPER = colors.HexColor("#F3F8EF")
PAPER_DARK = colors.HexColor("#DDEBDA")
GRID = colors.HexColor("#D5E5D0")
INK = colors.HexColor("#143A2E")
MUTED = colors.HexColor("#4E6F60")
DEEP = colors.HexColor("#173F32")
LEAF = colors.HexColor("#679C72")
SAGE = colors.HexColor("#AFCDB4")
MINT = colors.HexColor("#CFE4D0")
WHITE = colors.HexColor("#FFFFFA")


SLIDES = [
    {
        "kicker": "Hook",
        "title": "Most teams use calendars wrong",
        "accent": DEEP,
        "lines": [
            ("body", "They optimize for availability."),
            ("body", "Not output."),
            ("gap", ""),
            ("body", "So work gets shredded:"),
            ("bullet", "Constant interruptions"),
            ("bullet", "Fragmented build time"),
            ("bullet", "Slow decisions"),
            ("strong", "Use calendars as a boundary system."),
        ],
    },
    {
        "kicker": "01",
        "title": "Protect build time",
        "accent": LEAF,
        "lines": [
            ("body", "Deep work will not protect itself."),
            ("bullet", "Block 09:00-11:00 daily as Focus"),
            ("bullet", "Decline meetings in that window"),
            ("bullet", "Label it: Focus - build/debug/review"),
            ("script", "Script:"),
            ("quote", '"Can we move this? I keep mornings for build work."'),
            ("reality", "Reality: people will push back. Hold the line."),
        ],
    },
    {
        "kicker": "02",
        "title": "Make collaboration predictable",
        "accent": colors.HexColor("#719F7A"),
        "lines": [
            ("body", "The goal is not fewer conversations."),
            ("body", "The goal is fewer surprise interruptions."),
            ("script", "If you are an IC:"),
            ("bullet", "Propose afternoon sync windows"),
            ("bullet", "Avoid ad-hoc calls"),
            ("script", "If you are a lead:"),
            ("bullet", "Batch meetings into 2-3 blocks"),
            ("bullet", "Protect the rest"),
        ],
    },
    {
        "kicker": "03",
        "title": "Give stakeholders clear access",
        "accent": colors.HexColor("#7FAE87"),
        "lines": [
            ("body", "Stakeholders will interrupt."),
            ("body", "Unless you define access first."),
            ("bullet", "Set two weekly review windows"),
            ("bullet", "Share them openly"),
            ("example", "Example: Tue/Thu 14:00-16:00"),
            ("strong", "Everything else: async, backlog, or one escalation path."),
        ],
    },
    {
        "kicker": "04",
        "title": "Make boundaries enforceable",
        "accent": colors.HexColor("#5F916C"),
        "lines": [
            ("body", "A calendar only works if the team respects it."),
            ("bullet", "Focus = no meetings"),
            ("bullet", "Busy = not available"),
            ("bullet", "Free = okay to book"),
            ("bullet", "Emergencies = rare"),
            ("strong", "If everything flexes, nothing works."),
        ],
    },
    {
        "kicker": "CTA",
        "title": "Try this tomorrow",
        "accent": DEEP,
        "lines": [
            ("body", "Do not redesign the whole org."),
            ("body", "Change one visible habit."),
            ("bullet", "Block one Focus window"),
            ("bullet", "Add one stakeholder window"),
            ("bullet", "Ask your team to respect both"),
            ("cta", 'Comment "calendar" if you want the template.'),
        ],
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
    step = leading or size * 1.22

    if max_width is None:
        c.drawString(x, y, value)
        return y - step

    for paragraph in value.split("\n"):
        for line in wrap_to_width(paragraph, font, size, max_width) or [""]:
            c.drawString(x, y, line)
            y -= step
    return y


def pill(c, label, x, y, fill, txt=WHITE):
    width = max(140, pdfmetrics.stringWidth(label.upper(), "NotoSans-Bold", 18) + 58)
    c.setFillColor(fill)
    c.roundRect(x, y - 34, width, 52, 24, stroke=0, fill=1)
    text(c, label.upper(), x + 29, y - 16, 18, "NotoSans-Bold", txt)


def draw_background(c, accent):
    c.setFillColor(PAPER)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)

    c.setStrokeColor(GRID)
    c.setLineWidth(2)
    for x in range(135, 1000, 132):
        c.line(x, 190, x, 1136)
    for y in range(238, 1110, 132):
        c.line(100, y, 980, y)

    c.setFillColor(PAPER_DARK)
    c.circle(940, 1190, 246, stroke=0, fill=1)
    c.setFillColor(MINT)
    c.circle(1016, 1266, 104, stroke=0, fill=1)

    c.setFillColor(colors.Color(1, 1, 1, alpha=0.42))
    for i in range(4):
        c.roundRect(712 + i * 42, 1078 - i * 42, 150, 18, 9, stroke=0, fill=1)

    c.setFillColor(accent)
    c.roundRect(902, 190, 96, 96, 25, stroke=0, fill=1)
    c.setFillColor(SAGE)
    c.roundRect(802, 224, 62, 62, 18, stroke=0, fill=1)


def draw_footer(c, idx):
    c.setFillColor(DEEP)
    c.roundRect(MARGIN, 56, 198, 40, 20, stroke=0, fill=1)
    text(c, f"{idx:02d} / {len(SLIDES):02d}", MARGIN + 28, 69, 16, "NotoSans-Bold", WHITE)
    text(c, FOOTER, WIDTH - 356, 69, 19, "NotoSans-Bold", DEEP)


def draw_line(c, kind, value, x, y, accent):
    if kind == "gap":
        return y - 16

    if kind == "bullet":
        c.setFillColor(accent)
        c.roundRect(x, y - 17, 20, 20, 8, stroke=0, fill=1)
        return text(c, value, x + 48, y - 3, 30, "NotoSans-Bold", INK, leading=38, max_width=820) - 20

    if kind == "script":
        return text(c, value.upper(), x, y, 19, "NotoSans-Bold", accent, leading=30, max_width=820) - 6

    if kind == "quote":
        return text(c, value, x, y, 30, "NotoSerif-Bold", INK, leading=40, max_width=850) - 18

    if kind == "example":
        c.setFillColor(MINT)
        c.roundRect(x - 22, y - 35, 780, 58, 22, stroke=0, fill=1)
        return text(c, value, x, y - 14, 28, "NotoSans-Bold", INK, leading=36, max_width=730) - 22

    if kind == "reality":
        c.setFillColor(PAPER_DARK)
        c.roundRect(x - 22, y - 35, 850, 62, 22, stroke=0, fill=1)
        return text(c, value, x, y - 14, 27, "NotoSans-Bold", DEEP, leading=35, max_width=800) - 24

    if kind == "cta":
        c.setFillColor(accent)
        c.roundRect(x - 22, y - 46, 858, 78, 27, stroke=0, fill=1)
        return text(c, value, x, y - 18, 31, "NotoSans-Bold", WHITE, leading=38, max_width=810) - 26

    if kind == "strong":
        return text(c, value, x, y, 34, "NotoSans-Bold", DEEP, leading=43, max_width=860) - 22

    return text(c, value, x, y, 33, "NotoSans-Bold", MUTED, leading=42, max_width=860) - 12


def render_slide(c, slide, idx):
    accent = slide["accent"]
    draw_background(c, accent)
    pill(c, slide["kicker"], MARGIN, 1172, accent)

    title_size = 80 if idx == 1 else 72
    title_end = text(
        c,
        slide["title"],
        MARGIN,
        1010,
        title_size,
        "NotoSerif-Bold",
        INK,
        leading=title_size * 1.08,
        max_width=790,
    )
    y = title_end - 38
    for kind, value in slide["lines"]:
        y = draw_line(c, kind, value, MARGIN, y, accent)

    draw_footer(c, idx)
    c.showPage()


def main():
    register_fonts()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "previews").mkdir(exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(WIDTH, HEIGHT))
    c.setTitle("Most Teams Use Calendars Wrong")
    c.setAuthor("codingWithGPT test run")
    for idx, slide in enumerate(SLIDES, 1):
        render_slide(c, slide, idx)
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
