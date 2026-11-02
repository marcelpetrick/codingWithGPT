#!/usr/bin/env python3
"""refresh-compare.py -- validity and verdict for the rb1102 refresh (s15-refresh.sh).

A session counts only when the harness can prove that it measured the model:
  transcript ended in a non-error result (or the session hit its timeout),
  the model was seen in /api/ps, it never spilled (size_vram == size),
  it did not reload, and no foreign model was resident.

The rule, fixed before the data (ROUND_2026-11-02.md):
  correctness  the mean, over four tasks, of the median share of checks passed
  gate         T5 at least 7/8, else not ranked
  ranking      the highest correctness; within 3 points, the shorter median session time
  n            3 runs per task is final; 2 is preliminary; below 2 is not ranked
  summary      an answer above 600 words scores 0 (the prompt asks for 450)

Usage: refresh-compare.py --valid <tag> <fixture> <run>   exit 0 if the run counts, else 1
       refresh-compare.py --summary-done <tag>            exit 0 if 3 valid summary rows exist
       refresh-compare.py [--arm rb1102]                  write results/refresh-<arm>.md
"""
import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
SESSIONS = ("hard", "qtcpp", "gitlab")
RUNS = 3
T5_MIN = 7
TIE_POINTS = 3.0
MAX_SUMMARY_WORDS = 600
CONTROL = "qwen3.6:35b-a3b-q4_K_M-agentic"
CONTROL_DRIFT = 0.05


def safe(tag):
    return tag.replace(":", "_").replace("/", "_")


def rows(arm, res=RES):
    """The last row per model, fixture and run: a re-run replaces a void run."""
    f = res / f"cc-session-{arm}.tsv"
    out = {}
    if f.exists():
        with f.open() as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if r["thinking"] == "on" and r["fixture"] in SESSIONS:
                    out[(r["model"], r["fixture"], int(r["run"]))] = r
    return out


def void_reason(row, tag, fixture, run, arm, res=RES):
    """None if the session counts, else why it does not."""
    base = f"{safe(tag)}-{fixture}-thinkon-{arm}-r{run}"
    if row is None:
        return "no row"
    if row["ollama"] in ("", "?"):
        return "server version unknown"
    if row["foreign"] != "-":
        return "foreign model resident: " + row["foreign"]
    if row["reloads"] != "0":
        return "reloaded %s times" % row["reloads"]
    if "/" not in row["hidden"]:
        return "no score"
    seen = False
    try:
        for line in (res / "cc" / (base + ".ps.tsv")).read_text().splitlines():
            for item in line.split("\t", 1)[-1].split(" "):
                f = item.split("|")
                if f[0] == tag and len(f) >= 3:
                    seen = True
                    if f[1] != f[2]:
                        return "spilled: size %s, size_vram %s" % (f[1], f[2])
    except OSError:
        return "no ps log"
    if not seen:
        return "model never resident"
    if "timeout" in row.get("note", ""):
        return None  # a slow model is a result, and it has no result event
    last = None
    try:
        for line in (res / "cc" / (base + ".jsonl")).read_text().splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "result":
                last = ev
    except OSError:
        return "no transcript"
    if last is None:
        return "no result event"
    if last.get("is_error"):
        return "session ended in an error"
    return None


def summary_rows(arm, res=RES):
    """The last row per model and run."""
    f = res / f"summary-{arm}.tsv"
    out = {}
    if f.exists():
        with f.open() as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                out[(r["model"], int(r["run"]))] = r
    return out


def summary_score(r):
    """The share of checks passed, or None for a void row."""
    if r["void"]:
        return None
    if int(r["words"]) > MAX_SUMMARY_WORDS:
        return 0.0
    k, n = r["score"].split("/")
    return int(k) / int(n)


def t5(res=RES):
    out = {}
    f = res / "gate-rerun.tsv"
    if f.exists():
        for line in f.read_text().splitlines():
            c = line.split("\t")
            if len(c) >= 4 and c[1] == "T5":
                out[c[0]] = c[2]
    return out


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize(arm, res=RES):
    by = {}
    def entry(tag):
        return by.setdefault(tag, {
            "tasks": {k: [] for k in SESSIONS + ("summary",)}, "walls": {k: [] for k in SESSIONS},
            "void": [], "speed": {}})
    for (tag, fx, run), r in sorted(rows(arm, res).items(), key=lambda kv: kv[0][2]):
        e = entry(tag)
        why = void_reason(r, tag, fx, run, arm, res)
        if why:
            e["void"].append("%s r%d: %s" % (fx, run, why))
            continue
        k, n = r["hidden"].split("/")
        e["tasks"][fx].append(int(k) / int(n))
        if num(r["wall_s"]) is not None:
            e["walls"][fx].append(float(r["wall_s"]))
    for (tag, run), r in sorted(summary_rows(arm, res).items(), key=lambda kv: kv[0][1]):
        e = entry(tag)
        s = summary_score(r)
        if s is None:
            e["void"].append("summary r%d: %s" % (run, r["void"]))
            continue
        e["tasks"]["summary"].append(s)
        e["speed"][r["phase"]] = r
    gates = t5(res)
    for tag, e in by.items():
        e["t5"] = gates.get(tag, "-")
        e["n"] = min(len(v) for v in e["tasks"].values())
        med = [statistics.median(v) for v in e["tasks"].values() if v]
        e["correct"] = 100 * sum(med) / 4 if len(med) == 4 else None
        w = [statistics.median(v) for v in e["walls"].values() if v]
        e["session_s"] = sum(w) if len(w) == 3 else None
        d = e["t5"].split("/")[0]
        e["ranked"] = e["correct"] is not None and e["n"] >= 2 and d.isdigit() and int(d) >= T5_MIN
    return by


def ranking(by):
    """Highest correctness first. Models within TIE_POINTS of the best go by session time."""
    rest = sorted((t for t, e in by.items() if e["ranked"]), key=lambda t: -by[t]["correct"])
    out = []
    while rest:
        top = by[rest[0]]["correct"]
        group = [t for t in rest if top - by[t]["correct"] <= TIE_POINTS]
        out += sorted(group, key=lambda t: by[t]["session_s"])
        rest = [t for t in rest if t not in group]
    return out


def control_drift(by, arm="rb1019", res=RES):
    f = res / f"cc-session-{arm}.tsv"
    if not f.exists() or CONTROL not in by or not by[CONTROL]["walls"]["hard"]:
        return None
    with f.open() as fh:
        old = [float(r["wall_s"]) for r in csv.DictReader(fh, delimiter="\t")
               if r["model"] == CONTROL and r["fixture"] == "hard" and r["thinking"] == "on"]
    return statistics.median(by[CONTROL]["walls"]["hard"]) / statistics.median(old) - 1 if old else None


def pct(values):
    return "%.0f%%" % (100 * statistics.median(values)) if values else "-"


def report(arm, res=RES):
    by = summarize(arm, res)
    versions = sorted({r["ollama"] for r in rows(arm, res).values()} | {r["ollama"] for r in summary_rows(arm, res).values()})
    order = ranking(by) + [t for t in by if not by[t]["ranked"]]
    L = ["# Refresh %s (generated by refresh-compare.py, do not edit)" % arm, "",
         "Ollama: %s. Valid runs only." % ", ".join(versions), "",
         "## Correctness", "",
         "| model | correct | Python | Qt/C++ | GitLab | summary | T5 | n | session s |",
         "|---|---|---|---|---|---|---|---|---|"]
    for t in order:
        e = by[t]
        L.append("| %s | %s | %s | %s | %s | %s | %s | %d | %s |" % (
            t, "%.1f" % e["correct"] if e["correct"] is not None else "-", pct(e["tasks"]["hard"]), pct(e["tasks"]["qtcpp"]),
            pct(e["tasks"]["gitlab"]), pct(e["tasks"]["summary"]), e["t5"], e["n"],
            "%.0f" % e["session_s"] if e["session_s"] is not None else "-"))
    L += ["", "## Speed, cache and context (summary probe)", "",
          "| model | prompt tokens, cold | prefill tok/s, cold | prefill s, repeat | prefill s, extend | generation tok/s |",
          "|---|---|---|---|---|---|"]
    for t in order:
        s = by[t]["speed"]
        g = [num(r["gen_tps"]) for r in s.values() if num(r["gen_tps"])]
        L.append("| %s | %s | %s | %s | %s | %s |" % (
            t, s.get("cold", {}).get("prompt_tok", "-"), s.get("cold", {}).get("prefill_tps", "-"),
            s.get("repeat", {}).get("prefill_s", "-"), s.get("extend", {}).get("prefill_s", "-"),
            "%.0f" % statistics.median(g) if g else "-"))
    voids = [(t, by[t]["void"]) for t in order if by[t]["void"]]
    if voids:
        L += ["", "## Void runs (not counted)", ""] + ["- %s: %s" % (t, "; ".join(v)) for t, v in voids]
    rank = ranking(by)
    L.append("")
    if rank:
        n = by[rank[0]]["n"]
        L.append("**Pick by the rule: %s%s.**" % (rank[0], "" if n >= RUNS else " (preliminary, n=%d)" % n))
    else:
        L.append("**No model is ranked yet.**")
    d = control_drift(by, res=res)
    if d is None:
        L.append("Control drift against rb1019: not available.")
    else:
        L.append("Control drift against rb1019: %+.0f%% (median wall, Python task). %s" % (
            100 * d, "Within 5%." if abs(d) <= CONTROL_DRIFT
            else "Outside 5%: rank inside this arm only, and treat the change as a finding."))
    text = "\n".join(L) + "\n"
    (res / ("refresh-%s.md" % arm)).write_text(text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="rb1102")
    ap.add_argument("--valid", nargs=3, metavar=("TAG", "FIXTURE", "RUN"))
    ap.add_argument("--summary-done", metavar="TAG")
    a = ap.parse_args()
    if a.valid:
        tag, fx, run = a.valid[0], a.valid[1], int(a.valid[2])
        why = void_reason(rows(a.arm).get((tag, fx, run)), tag, fx, run, a.arm)
        if why:
            print(why)
        sys.exit(1 if why else 0)
    if a.summary_done:
        got = [summary_rows(a.arm).get((a.summary_done, r)) for r in (1, 2, 3)]
        sys.exit(0 if all(g and not g["void"] for g in got) else 1)
    print(report(a.arm), end="")


if __name__ == "__main__":
    main()
