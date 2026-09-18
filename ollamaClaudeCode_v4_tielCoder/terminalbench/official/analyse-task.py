#!/usr/bin/env python3
"""analyse-task.py -- what the agents actually DID on one terminal-bench task.

A resolved rate says a model failed; it does not say how. For that you have to
read the transcript, and the interesting failures in this round were not the
model giving up -- they were the model doing confident, competent, *wrong* work.

`oom` is the case that motivated this. The test loads with local_files_only=True,
which reads the DEFAULT cache path, so the model must end up in
/root/.cache/huggingface/hub/ no matter how it got there. Three routes appear:

  * remove the cause -- delete the 75 MB junk file, download in place (CyberTiel);
  * work around, then reconcile -- relocate to /tmp, then copy the files back into
    the default path (qwen3.6);
  * work around and stop -- relocate to /tmp and declare success (everyone else).

The third route satisfies the user's literal request and scores zero, because the
default cache is still empty. Relocating is not the error; leaving the default
path unpopulated is. That distinction is invisible in the score and plain in the
transcript, and it is the failure mode most likely to pass a human review.

Usage:
  ./analyse-task.py oom
  ./analyse-task.py oom --grep HF_HOME --grep large_model_file
  ./analyse-task.py fix-git --commands
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Per-task markers worth counting. Extend as new findings appear.
MARKERS = {
    "oom": {
        "found-junk-file": r"large_model_file",
        "relocated-cache": r"HF_HOME|TRANSFORMERS_CACHE|hf_cache",
        "deleted-junk-file": r"rm +(?:-[rf]+ +)*[^\s;|&]*large_model_file",
        "wrote-default-cache": r"(?:cp|mv|mkdir)[^\n]{0,120}/root/\.cache/huggingface/hub/models--albert",
    },
}


def trials(task):
    """Yield (run_id, trial_name, resolved, transcript_text)."""
    for rj in sorted((HERE / "runs").glob("*/results.json")):
        run_id = rj.parent.name
        if run_id.startswith(("selfcheck", "smoke")) or "void" in run_id:
            continue
        try:
            res = json.loads(rj.read_text())
        except ValueError:
            continue
        by_trial = {r.get("trial_name"): r for r in res.get("results", [])}
        for d in sorted((rj.parent / task).glob("*")) if (rj.parent / task).is_dir() else []:
            pane = d / "panes" / "post-agent.txt"
            if not pane.is_file():
                continue
            r = by_trial.get(d.name, {})
            yield (run_id.rsplit("-n", 1)[0], d.name, bool(r.get("is_resolved")),
                   r.get("failure_mode", "?"), pane.read_text(errors="replace"))


def commands(text):
    """The Bash commands the agent issued, in order."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        for c in (d.get("message", {}).get("content") or []):
            if isinstance(c, dict) and c.get("type") == "tool_use":
                cmd = (c.get("input") or {}).get("command")
                if cmd:
                    out.append(" ; ".join(cmd.split("\n")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--grep", action="append", default=[],
                    help="extra regex to count per trial")
    ap.add_argument("--commands", action="store_true",
                    help="print every Bash command each agent issued")
    a = ap.parse_args()

    pats = dict(MARKERS.get(a.task, {}))
    pats.update({g: g for g in a.grep})

    rows = list(trials(a.task))
    if not rows:
        print(f"no trials found for task '{a.task}'")
        return

    names = list(pats)
    w = max(len(m) for m, *_ in rows) + 2
    print(f"{'model':{w}} {'trial':>9} {'verdict':>8}  " +
          "  ".join(f"{n:>18}" for n in names))
    for model, trial, ok, fm, text in sorted(rows, key=lambda r: (not r[2], r[0])):
        n_of = re.search(r"\d-of-\d", trial)
        counts = [len(re.findall(p, text)) for p in pats.values()]
        verdict = "SOLVED" if ok else ("TIMEOUT" if fm == "agent_timeout" else "fail")
        print(f"{model:{w}} {n_of.group(0) if n_of else '?':>9} {verdict:>8}  " +
              "  ".join(f"{c:>18}" for c in counts))
        if a.commands:
            for c in commands(text):
                print(f"      | {c[:150]}")

    if a.task in MARKERS:
        solved = [r for r in rows if r[2]]
        failed = [r for r in rows if not r[2]]
        print(f"\n{len(solved)}/{len(rows)} trials solved.")
        if a.task == "oom" and solved and failed:
            for label, pat in (("relocated the cache", MARKERS["oom"]["relocated-cache"]),
                               ("left the DEFAULT cache populated",
                                MARKERS["oom"]["deleted-junk-file"] + "|" +
                                MARKERS["oom"]["wrote-default-cache"])):
                s = sum(bool(re.search(pat, r[4])) for r in solved)
                f = sum(bool(re.search(pat, r[4])) for r in failed)
                print(f"{label}: {s}/{len(solved)} of the solves, "
                      f"{f}/{len(failed)} of the failures.")


if __name__ == "__main__":
    main()
