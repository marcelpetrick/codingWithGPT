#!/usr/bin/env python3
"""
Generate A4 PDF certificates from an INI file.
Each recipient gets their own PDF.

Requires:
    pip install reportlab

Usage:
    python generate_certificates.py config.ini
"""

import sys
import os
import configparser
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, Color, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------- Helpers ----------

def parse_color(value, fallback="#1a73e8"):
    try:
        return HexColor(value.strip())
    except Exception:
        return HexColor(fallback)

def try_register_font():
    """
    Try to register a Unicode TTF for better glyph coverage.
    If 'DejaVuSans.ttf' is present in the working directory, we'll use it.
    Otherwise we fall back to built-in Helvetica (ASCII-safe).
    """
    ttf_candidates = [
        "DejaVuSans.ttf",                  # same folder
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # common Linux path
        "/Library/Fonts/DejaVuSans.ttf",  # possible mac path
        "C:\\Windows\\Fonts\\DejaVuSans.ttf",
    ]
    for path in ttf_candidates:
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                return "DejaVuSans"
            except Exception:
                pass
    return "Helvetica"

def read_ini(path):
    cfg = configparser.ConfigParser()
    cfg.optionxform = str  # preserve case for names if you want
    with open(path, "r", encoding="utf-8") as f:
        cfg.read_file(f)

    # Required section/keys with defaults where sensible
    title = cfg.get("certificate", "title", fallback="Certificate")
    subtitle = cfg.get("certificate", "subtitle", fallback="")
    issuer = cfg.get("certificate", "issuer", fallback="")
    date_str = cfg.get("certificate", "date", fallback=datetime.now().strftime("%Y-%m-%d"))

    # Colors & style
    primary = parse_color(cfg.get("design", "primary_color", fallback="#1a73e8"))
    accent = parse_color(cfg.get("design", "accent_color", fallback="#34a853"))
    border = parse_color(cfg.get("design", "border_color", fallback="#222222"))
    bg_tint = parse_color(cfg.get("design", "background_tint", fallback="#f7f7fb"))

    # Recipients: multiline INI value (indented lines under "names")
    raw_names = cfg.get("recipients", "names", fallback="").strip("\n")
    # Split by lines, strip empties
    names = [n.strip() for n in raw_names.splitlines() if n.strip()]

    # Output directory
    out_dir = cfg.get("output", "directory", fallback="output")

    return {
        "title": title,
        "subtitle": subtitle,
        "issuer": issuer,
        "date": date_str,
        "primary": primary,
        "accent": accent,
        "border": border,
        "bg_tint": bg_tint,
        "names": names,
        "out_dir": out_dir,
    }

# ---------- Drawing primitives ----------

def draw_border(c, w, h, border_color, margin=1.2*cm, thickness=3):
    c.setStrokeColor(border_color)
    c.setLineWidth(thickness)
    c.rect(margin, margin, w - 2*margin, h - 2*margin)

def draw_background_tint(c, w, h, tint_color):
    c.setFillColor(tint_color)
    c.rect(0, 0, w, h, stroke=0, fill=1)

def draw_logo(c, x, y, size, primary, accent):
    """
    Draw a simple stylized rosette + ribbon logo as vector paths.
    (x, y) is the center point. size is the overall diameter.
    """
    c.saveState()
    c.translate(x, y)

    r = size/2.0
    inner = r * 0.65

    # Outer "petals" circle
    c.setFillColor(primary)
    c.setStrokeColor(primary)
    c.setLineWidth(1.2)
    for i in range(16):
        c.saveState()
        c.rotate(i * (360/16))
        c.circle(0, r*0.55, r*0.22, stroke=0, fill=1)
        c.restoreState()

    # Inner circle
    c.setFillColor(white)
    c.circle(0, 0, inner, stroke=0, fill=1)

    # Accent ring
    c.setLineWidth(3)
    c.setStrokeColor(accent)
    c.circle(0, 0, inner*0.9, stroke=1, fill=0)

    # Tiny star in the middle
    c.setFillColor(primary)
    star_pts = []
    spikes = 5
    R = inner*0.45
    r_small = inner*0.2
    from math import sin, cos, pi
    for k in range(spikes*2):
        ang = pi/2 + k*pi/spikes
        rad = R if k % 2 == 0 else r_small
        star_pts.append((rad*cos(ang), rad*sin(ang)))
    c.beginPath()
    p = c._code
    # Draw polygon manually
    path = c.beginPath()
    path.moveTo(star_pts[0][0], star_pts[0][1])
    for (xx, yy) in star_pts[1:]:
        path.lineTo(xx, yy)
    path.close()
    c.drawPath(path, stroke=0, fill=1)

    # Ribbons
    c.setFillColor(accent)
    c.saveState()
    c.rotate(-15)
    c.rect(-r*0.35, -r*1.25, r*0.25, r*0.8, stroke=0, fill=1)
    c.restoreState()

    c.saveState()
    c.rotate(15)
    c.rect(r*0.10, -r*1.25, r*0.25, r*0.8, stroke=0, fill=1)
    c.restoreState()

    c.restoreState()

def draw_centered_text(c, text, center_x, y, font_name, font_size, color=black, tracking=0):
    c.setFillColor(color)
    c.setFont(font_name, font_size)
    # apply basic tracking by inserting spaces if requested
    if tracking:
        text = (" " * tracking).join(list(text))
    width = c.stringWidth(text, font_name, font_size)
    c.drawString(center_x - width/2.0, y, text)

def generate_certificate(
        out_path, title, name, date_str, issuer,
        primary, accent, border, bg_tint,
        font_heading, font_body):
    w, h = A4  # 595 x 842 points approx

    c = canvas.Canvas(out_path, pagesize=A4)

    # Background & border
    draw_background_tint(c, w, h, bg_tint)
    draw_border(c, w, h, border_color=border)

    # Logo
    logo_size = 5.2*cm
    draw_logo(c, w/2, h - 5.8*cm, logo_size, primary, accent)

    # Header text
    draw_centered_text(c, title, w/2, h - 8.2*cm, font_heading, 28, primary)
    if issuer:
        draw_centered_text(c, f"Issued by {issuer}", w/2, h - 9.4*cm, font_body, 12, Color(0,0,0,0.7))

    # Recipient name
    draw_centered_text(c, name, w/2, h/2 + 0.7*cm, font_heading, 36, black)

    # Subtitle / statement
    statement = "This certifies that the above recipient has successfully completed the program."
    draw_centered_text(c, statement, w/2, h/2 - 0.6*cm, font_body, 12, Color(0,0,0,0.85))

    # Date + signature line area
    left_x = w/2 - 7*cm
    right_x = w/2 + 7*cm
    baseline = 5*cm

    # Date box
    c.setLineWidth(1)
    c.setStrokeColor(border)
    c.line(left_x, baseline, left_x + 5.5*cm, baseline)
    draw_centered_text(c, f"Date: {date_str}", left_x + 2.75*cm, baseline - 0.6*cm, font_body, 11, Color(0,0,0,0.9))

    # Signature box
    c.line(right_x - 5.5*cm, baseline, right_x, baseline)
    draw_centered_text(c, "Signature", right_x - 2.75*cm, baseline - 0.6*cm, font_body, 11, Color(0,0,0,0.9))

    # Footer accent bar
    c.setFillColor(primary)
    c.rect(0, 0, w, 0.6*cm, stroke=0, fill=1)

    c.showPage()
    c.save()

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_certificates.py config.ini")
        sys.exit(1)

    cfg_path = sys.argv[1]
    if not os.path.isfile(cfg_path):
        print(f"Config file not found: {cfg_path}")
        sys.exit(1)

    data = read_ini(cfg_path)

    if not data["names"]:
        print("No recipients found in [recipients] -> names")
        sys.exit(1)

    os.makedirs(data["out_dir"], exist_ok=True)

    # Fonts
    heading_font = try_register_font()
    body_font = heading_font  # keep it consistent

    for person in data["names"]:
        safe_name = "".join(ch for ch in person if ch not in r'<>:"/\|?*').strip()
        if not safe_name:
            safe_name = "recipient"
        filename = f"Certificate - {safe_name}.pdf"
        out_path = os.path.join(data["out_dir"], filename)

        generate_certificate(
            out_path=out_path,
            title=data["title"],
            name=person,
            date_str=data["date"],
            issuer=data["issuer"],
            primary=data["primary"],
            accent=data["accent"],
            border=data["border"],
            bg_tint=data["bg_tint"],
            font_heading=heading_font,
            font_body=body_font
        )
        print(f"✓ Created: {out_path}")

    print("\nAll done!")

if __name__ == "__main__":
    main()
