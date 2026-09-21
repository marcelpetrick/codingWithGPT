#!/usr/bin/env python3
"""s9-parse.py -- the readers s9-candidates.sh needs, kept out of the shell.

Every one of these answers a question from a file the harness already writes, so
the screen never re-measures anything it can read, and never parses a number out
of a log line when a TSV carries it.

  size   <base> <tag>    GiB the tag occupies on the box   (/api/tags)
  native <base> <tag>    the model's own context length     (/api/show)
  caps   <base> <tag>    reported capabilities              (/api/show)
  ps     <base> <tag>    "resident_gb vram_gb"              (/api/ps)
  gen   <tag>            last recorded generation tok/s from results/tokrate.tsv
  ledger <tag>           "median_wall median_hidden" from results/cc-session.tsv
                         (hard fixture, thinking on, this tag only)
  verdict <med> <hid>    the pre-registered G3 rule, in one place
"""
import csv
import json
import statistics
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
G3_MAX_MEDIAN_S = 150.0   # 2.5x the best standing model on the same fixture
G3_MIN_HIDDEN = 16.0      # out of 18 held-out tests


def _api(base, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def size(base, tag):
    for m in _api(base, "/api/tags").get("models", []):
        if m["name"] == tag:
            return f"{m['size'] / 2**30:.2f}"
    return "0"


def native(base, tag):
    info = _api(base, "/api/show", {"model": tag}).get("model_info", {})
    for k, v in info.items():
        if k.endswith(".context_length"):
            return str(v)
    return "262144"


def caps(base, tag):
    return ",".join(_api(base, "/api/show", {"model": tag}).get("capabilities", [])) or "none"


def ps(base, tag):
    """Resident size and the part of it that is actually on the GPU.

    These are the two numbers that decide G1. A model that reports a smaller
    size_vram than size has spilled into system RAM, which cost 5.3x in v1 and
    reads as a bad model rather than a full box.
    """
    for m in _api(base, "/api/ps").get("models", []):
        if m["name"] == tag:
            return f"{m['size'] / 1e9:.2f} {m.get('size_vram', 0) / 1e9:.2f}"
    return "0 0"


def fit(res, vram):
    try:
        res, vram = float(res), float(vram)
    except ValueError:
        return "FAIL"
    return "PASS" if vram > 0 and abs(res - vram) / max(res, 1e-9) < 0.01 else "FAIL"


def sizematch(got, expected, tol=0.03):
    """The hf.co quant label is not unique -- byteshape ships two Q4_K_S files."""
    try:
        return "yes" if abs(float(got) - float(expected)) / float(expected) < tol else "no"
    except (ValueError, ZeroDivisionError):
        return "no"


def clamp_ctx(nativ, ceiling="262144"):
    try:
        return str(min(int(nativ), int(ceiling)))
    except ValueError:
        return ceiling


def _rows(name):
    p = HERE / "results" / name
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def gen(tag):
    rows = [r for r in _rows("tokrate.tsv") if r.get("model") == tag]
    if not rows:
        return "-"
    for key in ("gen_toks_s", "gen_tok_s", "generation", "gen"):
        if key in rows[-1]:
            return rows[-1][key]
    return "-"


def ledger(tag):
    rows = [r for r in _rows("cc-session.tsv")
            if r.get("model") == tag and r.get("fixture") == "hard"
            and r.get("thinking") == "on"]
    if not rows:
        return "- -"
    walls = [float(r["wall_s"]) for r in rows if r.get("wall_s")]
    hid = [int(r["hidden"].split("/")[0]) for r in rows if "/" in r.get("hidden", "")]
    med = f"{statistics.median(walls):.0f}" if walls else "-"
    return f"{med} {statistics.median(hid):.0f}" if hid else f"{med} -"


def verdict(med, hid):
    try:
        return ("SCREENED-IN" if float(med) <= G3_MAX_MEDIAN_S
                and float(hid) >= G3_MIN_HIDDEN else "CUT-G3")
    except ValueError:
        return "CUT-G3"


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    print({"gen": gen, "ledger": ledger, "verdict": verdict, "size": size,
           "native": native, "caps": caps, "ps": ps, "fit": fit,
           "sizematch": sizematch, "clamp_ctx": clamp_ctx}[cmd](*args))
