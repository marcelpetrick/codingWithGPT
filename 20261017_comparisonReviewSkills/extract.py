#!/usr/bin/env python3
"""Turn each run's stream-json transcript into metrics + the reported findings.

Writes runs/<run>/findings.md and results/metrics.json. Fails loudly on a run without a
result event, so a dead session is never booked as "few findings".
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
RUNS = HERE / "runs"
OUT = HERE / "results"


def load(path):
    events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def analyse(run_dir):
    events = load(run_dir / "transcript.jsonl")
    results = [e for e in events if e.get("type") == "result"]
    if not results:
        raise SystemExit(f"{run_dir.name}: no result event — dead session, not a result")
    res = results[-1]
    meta = dict(kv.split("=", 1) for kv in (run_dir / "meta.txt").read_text().split() if "=" in kv)

    tool_calls, subagents, report_findings, msg_ids = {}, 0, [], set()
    for e in events:
        if e.get("type") != "assistant":
            continue
        msg_ids.add(e["message"].get("id"))
        for c in e["message"].get("content", []):
            if c.get("type") != "tool_use":
                continue
            name = c["name"]
            tool_calls[name] = tool_calls.get(name, 0) + 1
            if name in ("Agent", "Task"):
                subagents += 1
            if name == "ReportFindings":
                report_findings = c["input"].get("findings", [])

    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    per_model = {}
    for model, mu in (res.get("modelUsage") or {}).items():
        per_model[model] = mu
        usage["input"] += mu.get("inputTokens", 0)
        usage["output"] += mu.get("outputTokens", 0)
        usage["cache_read"] += mu.get("cacheReadInputTokens", 0)
        usage["cache_write"] += mu.get("cacheCreationInputTokens", 0)

    text = res.get("result") or ""
    if not report_findings:
        # /code-review's subagent returns a JSON array in a ```json block instead of the tool.
        m = re.search(r"```json\s*(\[.*?\])\s*```", text, re.S)
        if m:
            report_findings = json.loads(m.group(1))
    if report_findings:
        lines = [f"#{i}  {f.get('category','')}  {f['file']}:{f.get('line','')}\n"
                 f"    {f['summary']}\n    Scenario: {f['failure_scenario']}"
                 for i, f in enumerate(report_findings, 1)]
        findings_md = "\n\n".join(lines)
        n_findings = len(report_findings)
    else:
        findings_md = text
        # /reviewBranch: "#1  HIGH  Code  path:line"; /code-review: "1. `path:line`: ..."
        n_findings = (len(re.findall(r"^#\d+\s+(HIGH|MEDIUM|LOW)", text, re.M))
                      or len(re.findall(r"^\d+\. `[^`]+`", text, re.M)))

    (run_dir / "findings.md").write_text(findings_md + "\n\n---\nFinal text:\n" + text + "\n")
    fixture, arm, rep = run_dir.name.split("_")
    return {
        "run": run_dir.name, "fixture": fixture, "arm": arm, "rep": int(rep),
        "claude": meta.get("claude"), "wall_s": int(meta.get("wall_s", 0)),
        # num_turns is 0 for /code-review (a local command), so count API messages for both arms.
        "turns": len(msg_ids), "num_turns_reported": res.get("num_turns"), "cost_usd": res.get("total_cost_usd"),
        "api_ms": res.get("duration_api_ms"), "is_error": res.get("is_error"),
        "tokens": usage, "tokens_total": sum(usage.values()), "models": list(per_model),
        "tool_calls": tool_calls, "subagents": subagents, "findings": n_findings,
        "worktree_dirty": any(l.strip() not in ("?? node_modules", "?? .venv")
                              for l in (run_dir / "worktree_after.txt").read_text().splitlines()),
    }


def main():
    rows = [analyse(d) for d in sorted(RUNS.iterdir()) if d.is_dir()]
    OUT.mkdir(exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(rows, indent=1))
    hdr = f"{'run':<16}{'turns':>6}{'subag':>6}{'tok_total':>11}{'out':>8}{'usd':>8}{'wall':>6}{'find':>5}"
    print(hdr)
    for r in rows:
        print(f"{r['run']:<16}{r['turns']:>6}{r['subagents']:>6}{r['tokens_total']:>11}"
              f"{r['tokens']['output']:>8}{r['cost_usd']:>8.2f}{r['wall_s']:>6}{r['findings']:>5}")


if __name__ == "__main__":
    sys.exit(main())
