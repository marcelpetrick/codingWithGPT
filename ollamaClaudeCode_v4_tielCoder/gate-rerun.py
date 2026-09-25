#!/usr/bin/env python3
"""gate-rerun.py -- re-run ONE tool gate N times, to tell variance from a defect.

agentic-test.sh fires each of T1-T5 once, at whatever temperature the tag ships
(0.6 for the Tiel tags). v3 §19f established that a single-shot gate result can
flip on a re-run, and v3 §25a used 8 repeats to show nemotron-cascade-2's
failures were systematic (50% and 87.5%) rather than noise. This is that tool,
so a re-run does not mean re-running the whole battery including the 250k needle.

The request bodies are copied from agentic-test.sh so a re-run measures the same
thing the battery measured: /v1/messages, thinking disabled, max_tokens 4000.

Usage: gate-rerun.py [--host URL] [--n 8] [--gate T5] <model> [<model>...]
"""
import argparse
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

TOOLS_MULTI = [
    {"name": "read_file", "description": "Read the contents of a file from disk",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "Absolute path"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file on disk",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "run_tests", "description": "Run the project test suite and return results",
     "input_schema": {"type": "object", "properties": {"suite": {"type": "string"}}, "required": ["suite"]}},
    {"name": "search_code", "description": "Search the repository for a regex pattern",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "glob": {"type": "string"}}, "required": ["pattern"]}},
]
COMPLEX = [{"name": "apply_patch", "description": "Apply a structured multi-file patch to the repository",
            "input_schema": {"type": "object", "properties": {
                "commit_message": {"type": "string"},
                "strategy": {"type": "string", "enum": ["merge", "rebase", "squash"]},
                "edits": {"type": "array", "items": {"type": "object", "properties": {
                    "path": {"type": "string"},
                    "mode": {"type": "string", "enum": ["create", "modify", "delete"]},
                    "hunks": {"type": "array", "items": {"type": "object", "properties": {
                        "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["old", "new"]}}},
                    "required": ["path", "mode"]}}},
                "required": ["commit_message", "strategy", "edits"]}}]

GATES = {
    "T1": (([{"name": "write_file", "description": "Write content to a file",
              "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}]),
           "Write hello world to /tmp/test.txt"),
    "T2": (TOOLS_MULTI, "Find every place in the repo where we call deprecated_api(). Do not read or write any file yet."),
    "T4": (TOOLS_MULTI, "Read both /app/a.txt and /app/b.txt. Issue both reads at once in a single turn."),
    "T5": (COMPLEX, 'Rename the function foo to bar in src/main.py, and delete src/old.py. '
                    'Use the squash strategy and commit message "refactor: rename foo to bar".'),
}


def judge(gate, d):
    tu = [b for b in d.get("content", []) if b.get("type") == "tool_use"]
    if d.get("error"):
        return "ERROR", str(d["error"])[:60]
    if gate == "T1":
        if d.get("stop_reason") == "tool_use" and tu and tu[0]["input"].get("path") == "/tmp/test.txt":
            return "PASS", "correct_args"
        return ("PARTIAL", "args_off") if tu else ("FAIL", f"stop={d.get('stop_reason')}")
    if gate == "T2":
        if not tu:
            return "FAIL", "no_tool_call"
        return ("PASS" if tu[0]["name"] == "search_code" else "FAIL"), "chose_" + tu[0]["name"]
    if gate == "T4":
        return ("PASS", f"{len(tu)}_parallel") if len(tu) >= 2 else ("PARTIAL", f"{len(tu)}_call_only")
    if gate == "T5":
        if not tu:
            return "FAIL", "no_tool_call"
        # name the failure precisely (review_20260925): occamy and ornith were booked
        # "edits_not_an_array" but actually called a tool that was never offered
        if tu[0].get("name") != "apply_patch":
            return "FAIL", f"wrong_tool:{tu[0].get('name')}"
        i = tu[0].get("input", {})
        ed = i.get("edits")
        if isinstance(ed, list) and not ed:
            return "FAIL", "empty_edits"
        if not isinstance(ed, list) or not isinstance(ed[0], dict):
            return "FAIL", f"edits_not_an_array({type(ed).__name__})"
        drift = [",".join(sorted({"path", "mode"} - set(e.keys()))) for e in ed if {"path", "mode"} - set(e.keys())]
        if drift:
            return "PARTIAL", "schema_drift_" + drift[0][:30]
        if i.get("strategy") != "squash":
            return "PARTIAL", f"strategy={i.get('strategy')}"
        return "PASS", f"exact_{len(ed)}_edits"
    return "?", "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://192.168.100.67:11434")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--gate", default="T5", choices=sorted(GATES))
    ap.add_argument("models", nargs="+")
    a = ap.parse_args()
    tools, prompt = GATES[a.gate]
    body_base = {"max_tokens": 4000, "thinking": {"type": "disabled"}, "tools": tools,
                 "messages": [{"role": "user", "content": prompt}]}
    for model in a.models:
        results = []
        for i in range(a.n):
            body = dict(body_base, model=model)
            req = urllib.request.Request(a.host.rstrip("/") + "/v1/messages",
                                         json.dumps(body).encode(),
                                         {"Content-Type": "application/json",
                                          "x-api-key": "ollama", "anthropic-version": "2023-06-01"})
            try:
                with urllib.request.urlopen(req, timeout=1200) as r:
                    d = json.load(r)
            except Exception as e:
                d = {"error": str(e)}
            v, why = judge(a.gate, d)
            results.append(v)
            out = HERE / "results"; out.mkdir(exist_ok=True)
            with (out / "gate-rerun.raw.jsonl").open("a") as f:
                f.write(json.dumps({"model": model, "gate": a.gate, "run": i + 1,
                                    "verdict": v, "why": why, "response": d}) + "\n")
            print(f"  {model[:44]:44} {a.gate} run{i + 1}: {v:8} {why}")
        n_pass = results.count("PASS")
        # v3 §25a's threshold: <= half the runs failing is 'systematic' and
        # disqualifying; a single failure in eight is sampling noise at the tag's
        # shipped temperature (v3 §19f) and must not be published as a defect.
        verdict = "clean" if n_pass == a.n else "systematic" if n_pass <= a.n // 2 else "flaky"
        with (HERE / "results" / "gate-rerun.tsv").open("a") as f:
            f.write(f"{model}\t{a.gate}\t{n_pass}/{a.n}\t{verdict}\n")
        print(f"  {model[:44]:44} {a.gate}: {n_pass}/{a.n} PASS  -> {verdict}\n")


if __name__ == "__main__":
    main()
