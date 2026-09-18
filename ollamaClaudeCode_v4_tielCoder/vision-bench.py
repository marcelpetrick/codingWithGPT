#!/usr/bin/env python3
"""vision-bench.py -- can this model read an image, scored, at its baked window?

v1-v3 recorded vision as a capability flag plus one qualitative screenshot read.
This scores it: the three fixtures and 25 objective string checks from
../ollamaClaude_ImageProcessing/benchmark_vision.py (invoice OCR 9, UI description
6, chart extraction 10), unchanged, so the qwen3-vl:32b numbers there are a
reference point.

Two deliberate differences from that harness:

* No num_ctx override. The request runs at the tag's BAKED window, because that
  is the window Claude Code will use. On .67 an image needs a vision workspace on
  top of the resident model: qwen3-vl loaded fine at 53,248 and returned HTTP 500
  on the first image. A model that reads images only at a smaller window than it
  is deployed with does not have vision in the configuration that matters.
* think:false instead of the "/no_think" prompt prefix, which is a Qwen-only
  convention. Every model in v4's field honours think:false on /api/chat (checked
  per model; an ignored flag shows up as a nonzero thinking length in the TSV).

An HTTP error is recorded as a result (ERROR with the message), not raised.

Usage: vision-bench.py [--host URL] [--num-predict N] <model> [<model>...]
"""
import argparse
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE.parent / "ollamaClaude_ImageProcessing" / "fixtures"
# v2 scoring, 2026-09-18. v1 asked only "does this string appear anywhere in the
# answer" and every model in the field scored a perfect 25/25 -- a test nothing
# ever fails separates nothing (BENCHMARK_HARNESS.md §0 applies to our own
# instruments too). Three changes, none of which need new fixtures:
#
#   needles  as before: facts that must be present.
#   pairs    a label and its value must appear WITHIN `PAIR_WINDOW` characters of
#            each other. Listing every number and every label in separate blocks
#            no longer scores -- the model has to actually associate them, which
#            is the thing OCR-of-a-table is for.
#   traps    plausible misreadings that must NOT appear: a transposed invoice
#            number, an O-for-Q confusion in the reference code, a wrong VAT rate,
#            categories that are not in the chart. Each one found is a penalty.
#            Hallucinating confidently now costs points instead of being free.
#
# Every trap here was validated against results/vision.raw.jsonl: any candidate
# that fired on an already-correct stored answer was discarded rather than
# shipped, so a trap firing means the model was wrong, not that the trap is.
PAIR_WINDOW = 60

CASES = [
    ("ocr-invoice", "ocr-invoice.png",
     "Perform OCR on this invoice. Transcribe every visible line exactly, preserving "
     "numbers, punctuation, and item order. Return only the transcription.",
     ["R-2026-0831", "31 August 2026", "Ada Lovelace Labs", "Vision benchmark",
      "EUR 1,278.50", "EUR 242.92", "EUR 1,521.42", "VISION-7Q4K-92", "14 days",
      "GPU server hour", "319.50", "19%"],
     [("Vision benchmark", "319.50"), ("GPU server hour", "40.00"),
      ("VAT", "242.92"), ("TOTAL", "1,521.42"), ("Subtotal", "1,278.50")],
     ["R-2026-0813", "VISION-7O4K-92", "1,521.40", "1,278.05", "20%", "21%",
      "30 days", "1 September 2026"]),

    ("embedded-ui", "embedded-ui.png",
     "Describe the visible application UI precisely. Include the window title, main "
     "heading, all three button labels and colors, status text, and slider position.",
     ["LVGL Simulator", "LVGL - Embedded UI Demo", "Accept", "Cancel", "Config",
      "total clicks: 8", "green", "red"],
     [("Accept", "green"), ("Cancel", "red")],
     ["total clicks: 3", "total clicks: 9", "total clicks: 0", "LVGL Emulator",
      "Embedded GUI Demo", "Submit", "Apply"]),

    ("expenses-treemap", "expenses-treemap.png",
     "Describe this chart and transcribe every category and euro value. State which "
     "category is largest and explain what rectangle area represents.",
     ["Rent", "1200", "Food", "1000", "Kids", "900", "Car", "200", "Clothes", "100"],
     [("Rent", "1200"), ("Food", "1000"), ("Kids", "900"), ("Car", "200"),
      ("Clothes", "100")],
     ["Travel", "Utilities", "Insurance", "Groceries", "1300", "1100", "750"]),
]


def score(answer, needles, pairs, traps):
    """(needle hits, pair hits, trap hits). `answer` is already casefolded."""
    hits = sum(n.casefold() in answer for n in needles)
    pair_hits = 0
    for label, value in pairs:
        lab, val = label.casefold(), value.casefold()
        found, start = False, 0
        while (i := answer.find(lab, start)) != -1 and not found:
            window = answer[i:i + len(lab) + PAIR_WINDOW]
            found = val in window
            start = i + 1
        pair_hits += found
    trap_hits = sum(t.casefold() in answer for t in traps)
    return hits, pair_hits, trap_hits


def post(url, payload, timeout):
    req = urllib.request.Request(url, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode(errors='replace')[:160]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://192.168.100.67:11434")
    ap.add_argument("--num-predict", type=int, default=2048)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("models", nargs="+")
    a = ap.parse_args()
    host = a.host.rstrip("/")
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    # v2 schema. The v1 file scored a different thing (bare substring presence) and
    # is kept untouched as results/vision-v1.tsv rather than appended to -- mixing
    # two scoring regimes in one table is exactly the silent inconsistency §0 is
    # about.
    tsv = out / "vision-v2.tsv"
    if not tsv.exists():
        tsv.write_text("model\tcase\tchecks\tpairs\ttraps\tscore\twall_s\tprompt_tok\t"
                       "gen_tok\tgen_tps\tthinking_chars\tdone\tresident_gb\tpct_gpu\t"
                       "ctx\terror\n")
    raw = out / "vision.raw.jsonl"
    for model in a.models:
        total = possible = 0
        for name, image, prompt, needles, pairs, traps in CASES:
            img = base64.b64encode((FIX / image).read_bytes()).decode()
            t0 = time.monotonic()
            d = post(host + "/api/chat", {
                "model": model, "stream": False, "think": False, "keep_alive": "10m",
                "options": {"temperature": 0, "seed": 42, "num_predict": a.num_predict},
                "messages": [{"role": "user", "content": prompt, "images": [img]}],
            }, a.timeout)
            wall = time.monotonic() - t0
            with raw.open("a") as f:
                f.write(json.dumps({"model": model, "case": name, "response": d}) + "\n")
            with urllib.request.urlopen(host + "/api/ps", timeout=30) as r:
                ps = json.load(r)
            res = next((m for m in ps.get("models", []) if m.get("name") == model), {})
            size, vram = res.get("size", 0), res.get("size_vram", 0)
            err = d.get("error", "")
            msg = d.get("message") or {}
            answer = (msg.get("content") or "").casefold()
            hits, pair_hits, trap_hits = (0, 0, 0) if err else \
                score(answer, needles, pairs, traps)
            # A trap is a penalty, so a confident hallucination costs more than a
            # silent omission. The score can go negative; that is the point.
            got = hits + pair_hits - trap_hits
            can = len(needles) + len(pairs)
            total += got
            possible += can
            ec, ed = d.get("eval_count", 0), d.get("eval_duration", 0)
            row = [model, name, f"{hits}/{len(needles)}", f"{pair_hits}/{len(pairs)}",
                   trap_hits, f"{got}/{can}", f"{wall:.1f}",
                   d.get("prompt_eval_count", ""), ec, f"{ec / (ed / 1e9):.1f}" if ed else "",
                   len(msg.get("thinking") or ""), d.get("done_reason", ""),
                   f"{size / 1e9:.2f}" if size else "", f"{100 * vram / size:.0f}" if size else "",
                   res.get("context_length", ""), err.replace("\t", " ")[:120]]
            with tsv.open("a") as f:
                f.write("\t".join(str(x) for x in row) + "\n")
            flag = "  <-- TRAPS" if trap_hits else ""
            print(f"  {model[:44]:44} {name:17} needles {hits}/{len(needles)} "
                  f"pairs {pair_hits}/{len(pairs)} traps {trap_hits} "
                  f"= {got}/{can} wall={wall:5.1f}s {err[:40]}{flag}")
        print(f"  {model[:44]:44} TOTAL {total}/{possible}")


if __name__ == "__main__":
    main()
