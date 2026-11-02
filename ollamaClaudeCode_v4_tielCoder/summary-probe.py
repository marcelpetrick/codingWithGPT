#!/usr/bin/env python3
"""summary-probe.py -- long-text summary correctness, plus speed, cache and context.

One synthetic project log of about 150k tokens (114000 words, measured on two tokenizers) goes to the model three times:
  r1 cold    the whole document: prefill speed, and proof that the window holds it
  r2 repeat  the same request: prefix cache
  r3 extend  the document plus one new section: the agent-turn cache case

Score (of 16): 12 facts placed at the start, middle and end, and 4 corrections,
where the corrected value must appear and the superseded value must not.
Output is capped at 8192 tokens. A model that spends them all on reasoning scores what it wrote.
A transport error, an empty answer or a truncated prompt stops the job or voids
the row. It is never booked as a low score.

Usage: summary-probe.py [--host URL] [--arm rb1102] [--words 114000] <model>...
       summary-probe.py --print-doc      prints the document, for a check
"""
import argparse
import json
import random
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
# (position 0..1, sentence, pattern that proves the fact)
FACTS = [
    (0.02, "Decision: the release freeze for version 7.4 starts on 14 March.", r"14\s*March|March\s*14"),
    (0.05, "Decision: the Windows installer moves to WiX 5, owner Nadia.", r"WiX\s*5"),
    (0.09, "Risk: the sensor vendor Halberg stops delivery of the K9 board in June.", r"Halberg|K9"),
    (0.46, "Decision: the telemetry retention drops to 45 days because of the audit.", r"45\s*days"),
    (0.49, "Action: Tomasz writes the serial port recovery test before the demo.", r"Tomasz"),
    (0.52, "Root cause of the outage on Tuesday: a full disk on build agent nine.", r"(full|out of).{0,20}disk|disk.{0,20}full"),
    (0.55, "Risk: the Qt license renewal costs 38000 euro, and the budget has 30000.", r"38[ ,.]?000"),
    (0.90, "Decision: the customer pilot moves from Graz to Linz.", r"Linz"),
    (0.93, "Action: Priya reviews the installer signing key before Friday.", r"Priya"),
    (0.95, "Risk: the database migration needs a two hour downtime window.", r"two[- ]hour|2[- ]?h(ou)?r?s?\b"),
    (0.97, "Decision: the support hotline for the pilot opens at 7 in the morning.", r"\b7\s*(am|a\.m|in the morning|:00|o.clock)|07:00"),
    (0.985, "Action: Rafael sends the final price list to the Linz customer.", r"Rafael"),
]
# (old position, old sentence, new position, new sentence, new pattern, old pattern)
CORRECTIONS = [
    (0.12, "Decision: the Hamburg trade fair budget is 90000 euro.", 0.60,
     "Correction: the Hamburg trade fair budget is now 65000 euro, and the old figure is void.", r"65[ ,.]?000", r"90[ ,.]?000"),
    (0.20, "Decision: Oskar leads the Android port.", 0.70,
     "Correction: Oskar left the project, so Lena leads the Android port.", r"Lena", r"Oskar leads"),
    (0.30, "Decision: the API gateway uses port 8443.", 0.80,
     "Correction: the API gateway uses port 9443, because 8443 collides with the proxy.", r"9443", r"\buses port 8443"),
    (0.38, "Decision: the beta starts on 3 May.", 0.88,
     "Correction: the beta starts on 17 May, not on the earlier date.", r"17\s*May|May\s*17", r"\b3\s*May|May\s*3\b"),
]
EXTRA = "\n\n## Late addition\nDecision: the team drops the nightly Solaris build. Action: Mirela updates the CI matrix.\n"
NOUNS = "module parser widget scheduler dialog exporter logger cache adapter queue report driver".split()
VERBS = "reviewed merged refactored tested documented rebuilt profiled cleaned".split()
PROMPT = ("Below is the running log of a software project. Write a summary for the project lead, in at most 450 words. "
          "List every decision that is still valid, every open risk and every action with its owner. "
          "Where the log corrects an earlier statement, give only the valid state. Use only facts from the log.\n\n")


def document(words=85000):
    rnd = random.Random(20261102)
    placed = [(p, s) for p, s, _ in FACTS] + [(c[0], c[1]) for c in CORRECTIONS] + [(c[2], c[3]) for c in CORRECTIONS]
    placed.sort()
    out, n, i, day = [], 0, 0, 1
    while n < words:
        if n // 700 != (n + 40) // 700:
            out.append(f"\n## Status entry {day}\n"); day += 1
        while i < len(placed) and n >= placed[i][0] * words:
            out.append(placed[i][1] + "\n"); i += 1
        line = "The team %s the %s %s in ticket %d, and the %s stays on schedule with no change for the lead. " % (
            rnd.choice(VERBS), rnd.choice(NOUNS), rnd.choice(NOUNS), rnd.randint(1000, 9999), rnd.choice(NOUNS))
        out.append(line); n += len(line.split())
    return "".join(out)


def score(text):
    missed, k = [], 0
    for _, sent, pat in FACTS:
        if re.search(pat, text, re.I):
            k += 1
        else:
            missed.append(sent[:40])
    for _, _, _, sent, new, old in CORRECTIONS:
        if re.search(new, text, re.I) and not re.search(old, text, re.I):
            k += 1
        else:
            missed.append(sent[:40])
    return k, missed


def strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S)


MAX_OUTPUT = 8192   # a model that loops in its reasoning ends here, at about 100 s


def chat(host, model, content, timeout=600):
    body = {"model": model, "stream": False, "options": {"num_predict": MAX_OUTPUT},
            "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request(host.rstrip("/") + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d, time.time() - t0


HEAD = "model\trun\tphase\tollama\tscore\twords\tprompt_tok\tprefill_s\tprefill_tps\tgen_tok\tgen_tps\twall_s\tvoid\tmissed\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://192.168.100.67:11434")
    ap.add_argument("--arm", default="rb1102")
    ap.add_argument("--words", type=int, default=114000)
    ap.add_argument("--min-prompt", type=int, default=140000, help="a cold prompt below this was truncated")
    ap.add_argument("--print-doc", action="store_true")
    ap.add_argument("models", nargs="*")
    a = ap.parse_args()
    doc = document(a.words)
    if a.print_doc:
        print(doc); return
    tsv = HERE / "results" / f"summary-{a.arm}.tsv"
    if not tsv.exists():
        tsv.write_text(HEAD)
    with urllib.request.urlopen(a.host.rstrip("/") + "/api/version", timeout=10) as r:
        ver = json.load(r)["version"]
    for model in a.models:
        for run, phase, text in ((1, "cold", doc), (2, "repeat", doc), (3, "extend", doc + EXTRA)):
            try:
                d, wall = chat(a.host, model, PROMPT + text)
            except TimeoutError:
                with tsv.open("a") as f:
                    f.write("\t".join(map(str, (model, run, phase, ver, "0/16", 0, "", "", "", "", "", "600", "request timeout", ""))) + "\n")
                print(f"  {model[:40]:40} {phase:7} void: request timeout")
                continue
            except Exception as e:
                raise SystemExit(f"summary transport error for {model}: {e}; nothing booked")
            if d.get("error"):
                raise SystemExit(f"summary error for {model}: {d['error']}; nothing booked")
            answer = strip_think(d.get("message", {}).get("content", "") or "")
            ptok, gtok = d.get("prompt_eval_count", 0), d.get("eval_count", 0)
            ps, gs = d.get("prompt_eval_duration", 0) / 1e9, d.get("eval_duration", 0) / 1e9
            void = ""
            looped = d.get("done_reason") == "length"
            if not answer.strip() and not looped:
                void = "empty answer"   # a harness or server fault; a loop below is the model's own result
            elif phase == "cold" and ptok < a.min_prompt:
                void = f"prompt truncated to {ptok} tokens"
            k, missed = score(answer)
            words = len(answer.split())
            with tsv.open("a") as f:
                f.write("\t".join(map(str, (model, run, phase, ver, f"{k}/16", words, ptok, f"{ps:.1f}",
                        f"{ptok / ps:.0f}" if ps else "", gtok, f"{gtok / gs:.1f}" if gs else "", f"{wall:.1f}", void,
                        "; ".join(missed)))) + "\n")
            (HERE / "results" / "cc" / f"{model.replace(':', '_').replace('/', '_')}-summary-{a.arm}-r{run}.txt").write_text(answer)
            print(f"  {model[:40]:40} {phase:7} {k}/16 words={words} done={d.get("done_reason")} prompt={ptok} prefill={ps:.1f}s gen={gtok}tok wall={wall:.0f}s {void}")


if __name__ == "__main__":
    main()
