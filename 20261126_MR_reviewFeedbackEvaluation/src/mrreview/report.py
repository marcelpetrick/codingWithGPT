# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the single self-contained HTML dashboard (REQ-UI-1, REQ-SEC-1).

The data goes into a <script type="application/json"> block. Every character that could end
the block or start markup is escaped, so review text can never become HTML or script.
"""

from __future__ import annotations

import json
import os
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Any

from mrreview.config import Config
from mrreview.dataset import build_dataset

_ESCAPES = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}


def embed_json(data: Any) -> str:
    """Serialise data for an inline JSON script block."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for ch, rep in _ESCAPES.items():
        text = text.replace(ch, rep)
    return text


def _asset(name: str) -> str:
    return (resources.files("mrreview") / "assets" / name).read_text(encoding="utf-8")


def render_html(dataset: dict[str, Any], title: str = "Review & Collaboration Analytics") -> str:
    """Return the complete HTML document."""
    js = _asset("dashboard.js")
    css = _asset("dashboard.css")
    if "</script" in js.lower() or "</style" in css.lower():
        raise ValueError("asset contains a closing tag")
    page = _asset("dashboard.html")
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    page = page.replace("__TITLE__", safe_title).replace("__CSS__", css).replace("__JS__", js)
    return page.replace("__DATA__", embed_json(dataset), 1)


def write_report(conn: sqlite3.Connection, cfg: Config, out: Path, *, demo: bool = False) -> Path:
    """Build the dataset and write the HTML file atomically."""
    ds = build_dataset(conn, cfg)
    ds["meta"]["demo"] = demo
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(render_html(ds), encoding="utf-8")
    os.replace(tmp, out)
    return out
