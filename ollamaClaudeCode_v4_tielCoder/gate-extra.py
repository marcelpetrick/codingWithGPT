#!/usr/bin/env python3
"""gate-extra.py -- the agentic gates T1-T7 does not cover.

v1's battery checks that a model can call a tool, pick the right one, consume a
result, call two at once, fill a nested schema, and keep doing it at depth. Four
things an agent actually depends on are missing from it, and all four fail
silently rather than loudly:

  T8  structured output      Ollama's `format` (JSON schema) path. Never tested
                             in v1-v4. Agent frameworks lean on it even where
                             Claude Code does not.
  T9  tool-error recovery    T3 only ever feeds a SUCCESSFUL tool_result. What an
                             agent does with an error result -- correct the call,
                             or repeat it verbatim -- decides whether a loop
                             terminates. The Sharp template even injects a
                             "consecutive tool errors" warning; nothing tested it.
  T10 argument fidelity      Paths with spaces and quotes, embedded newlines,
                             non-ASCII. Tool args are JSON inside a chat template
                             inside HTTP; every layer is a chance to mangle them,
                             and the damage shows up as a file written to the
                             wrong path rather than as an error.
  T11 zero-argument tool     A tool whose schema takes no parameters. Some
                             templates emit `{}`, some omit `arguments`, some
                             invent a field.

Scored per model, n runs each (default 3) because v3 §19f and v4 §8 both showed
a single sample at the shipped temperature flips.

Usage: gate-extra.py [--host URL] [--n 3] <model> [<model>...]
"""
import argparse
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
HDR = {"Content-Type": "application/json", "x-api-key": "ollama",
       "anthropic-version": "2023-06-01"}

WRITE_TOOL = {
    "name": "write_file", "description": "Write content to a file on disk",
    "input_schema": {"type": "object",
                     "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                     "required": ["path", "content"]}}
STATUS_TOOL = {
    "name": "get_build_status", "description": "Return the current build status. Takes no arguments.",
    "input_schema": {"type": "object", "properties": {}}}
READ_TOOL = {
    "name": "read_file", "description": "Read a file from disk",
    "input_schema": {"type": "object", "properties": {"path": {"type": "string"}},
                     "required": ["path"]}}


def post(host, path, body, timeout=1200):
    req = urllib.request.Request(host.rstrip("/") + path, json.dumps(body).encode(), HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)[:160]}


def msg(host, model, **kw):
    body = {"model": model, "max_tokens": 4000, "thinking": {"type": "disabled"}}
    body.update(kw)
    return post(host, "/v1/messages", body)


def tool_uses(d):
    return [b for b in d.get("content", []) if b.get("type") == "tool_use"]


# ---------------------------------------------------------------- T8
def t8_structured_output(host, model):
    """Ollama's /api/chat `format` takes a JSON schema. Does the model honour it?"""
    schema = {"type": "object",
              "properties": {"language": {"type": "string"},
                             "functions": {"type": "array", "items": {"type": "string"}},
                             "has_tests": {"type": "boolean"},
                             "line_count": {"type": "integer"}},
              "required": ["language", "functions", "has_tests", "line_count"]}
    src = ("def add(a, b):\n    return a + b\n\n"
           "def mul(a, b):\n    return a * b\n\n"
           "def test_add():\n    assert add(1, 2) == 3\n")
    d = post(host, "/api/chat", {
        "model": model, "stream": False, "think": False, "format": schema,
        "options": {"temperature": 0, "seed": 42, "num_predict": 512},
        "messages": [{"role": "user",
                      "content": "Describe this source file.\n\n" + src}]})
    if d.get("error"):
        return "ERROR", str(d["error"])[:60]
    txt = (d.get("message") or {}).get("content", "") or ""
    try:
        obj = json.loads(txt)
    except ValueError:
        return "FAIL", f"not JSON: {txt[:50]!r}"
    missing = [k for k in schema["required"] if k not in obj]
    if missing:
        return "FAIL", "missing " + ",".join(missing)
    if not isinstance(obj.get("functions"), list) or not isinstance(obj.get("has_tests"), bool):
        return "PARTIAL", f"types off: {json.dumps(obj)[:60]}"
    # content check: it should find the three functions and notice the test
    fns = {str(x).split("(")[0].strip() for x in obj["functions"]}
    ok = {"add", "mul"} <= fns and obj["has_tests"] is True
    return ("PASS", f"valid+correct {json.dumps(obj)[:52]}") if ok else \
           ("PARTIAL", f"valid schema, content off: {json.dumps(obj)[:52]}")


# ---------------------------------------------------------------- T9
def t9_error_recovery(host, model):
    """Hand back an error tool_result. Does it CHANGE the call or repeat it?"""
    first = msg(host, model, tools=[READ_TOOL],
                messages=[{"role": "user",
                           "content": "Read the project config at /app/cfg/settings.yaml and tell me the port."}])
    tu = tool_uses(first)
    if not tu:
        return "FAIL", "no tool call on turn 1"
    bad_path = tu[0]["input"].get("path", "")
    convo = [
        {"role": "user",
         "content": "Read the project config at /app/cfg/settings.yaml and tell me the port."},
        {"role": "assistant", "content": first["content"]},
        {"role": "user", "content": [{
            "type": "tool_result", "tool_use_id": tu[0]["id"], "is_error": True,
            "content": ("Error: ENOENT no such file /app/cfg/settings.yaml. "
                        "A file exists at /app/config/settings.yaml")}]},
    ]
    second = msg(host, model, tools=[READ_TOOL], messages=convo)
    if second.get("error"):
        return "ERROR", str(second["error"])[:60]
    tu2 = tool_uses(second)
    if not tu2:
        txt = " ".join(b.get("text", "") for b in second.get("content", []) if b.get("type") == "text")
        return ("PARTIAL", "gave up, no retry: " + txt[:45]) if txt else ("FAIL", "no output")
    new_path = tu2[0]["input"].get("path", "")
    if new_path == bad_path:
        return "FAIL", f"repeated the failing path {new_path!r}"
    if "config/settings.yaml" in new_path:
        return "PASS", f"corrected to {new_path!r}"
    return "PARTIAL", f"changed but not to the hint: {new_path!r}"


# ---------------------------------------------------------------- T10
def t10_argument_fidelity(host, model):
    """Spaces, quotes, newlines and non-ASCII must survive the round trip."""
    path = '/tmp/my project/notes "final".txt'
    content = 'Zeile 1: Grüße\nline 2\tafter a tab\n"quoted" and \\backslash\nEnde – äöü ß €'
    prompt = ("Write a file using the write_file tool.\n"
              f"The path must be exactly: {path}\n"
              "The content must be exactly these four lines, byte for byte:\n"
              "---8<---\n" + content + "\n---8<---\n"
              "Do not escape, reformat, or comment on them.")
    d = msg(host, model, tools=[WRITE_TOOL],
            messages=[{"role": "user", "content": prompt}])
    if d.get("error"):
        return "ERROR", str(d["error"])[:60]
    tu = tool_uses(d)
    if not tu:
        return "FAIL", "no tool call"
    got_p = tu[0]["input"].get("path", "")
    got_c = tu[0]["input"].get("content", "")
    pok, cok = got_p == path, got_c.rstrip("\n") == content
    if pok and cok:
        return "PASS", "path+content byte-exact"
    if pok:
        return "PARTIAL", f"path ok, content differs: {got_c[:40]!r}"
    if cok:
        return "PARTIAL", f"content ok, path differs: {got_p!r}"
    return "FAIL", f"both differ: path={got_p!r}"


# ---------------------------------------------------------------- T11
def t11_zero_arg_tool(host, model):
    """A tool with no parameters. Calling it must not require inventing fields."""
    d = msg(host, model, tools=[STATUS_TOOL],
            messages=[{"role": "user", "content": "Is the build currently passing? Use the tool."}])
    if d.get("error"):
        return "ERROR", str(d["error"])[:60]
    tu = tool_uses(d)
    if not tu:
        return "FAIL", f"no tool call (stop={d.get('stop_reason')})"
    if tu[0]["name"] != "get_build_status":
        return "FAIL", "wrong tool " + tu[0]["name"]
    args = tu[0].get("input", {})
    if args in ({}, None):
        return "PASS", "called with no arguments"
    return "PARTIAL", f"invented arguments: {json.dumps(args)[:50]}"


GATES = {"T8_structured_output": t8_structured_output,
         "T9_error_recovery": t9_error_recovery,
         "T10_argument_fidelity": t10_argument_fidelity,
         "T11_zero_arg_tool": t11_zero_arg_tool}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://192.168.100.67:11434")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--gate", action="append", choices=sorted(GATES))
    ap.add_argument("models", nargs="+")
    a = ap.parse_args()
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    tsv = out / "gate-extra.tsv"
    if not tsv.exists():
        tsv.write_text("model\tgate\tpass_n\truns\tverdicts\tlast_detail\n")
    raw = (out / "gate-extra.raw.jsonl").open("a")
    chosen = a.gate or sorted(GATES)
    for model in a.models:
        print(f"\n### {model}")
        for name in chosen:
            verdicts, detail = [], ""
            for i in range(a.n):
                v, detail = GATES[name](a.host, model)
                verdicts.append(v)
                raw.write(json.dumps({"model": model, "gate": name, "run": i + 1,
                                      "verdict": v, "detail": detail}) + "\n")
                raw.flush()
            n_pass = verdicts.count("PASS")
            with tsv.open("a") as f:
                f.write(f"{model}\t{name}\t{n_pass}\t{a.n}\t{','.join(verdicts)}\t{detail}\n")
            mark = "PASS" if n_pass == a.n else ("FAIL" if n_pass == 0 else "FLAKY")
            print(f"  {name:24} {mark:6} {n_pass}/{a.n}  {detail[:64]}")


if __name__ == "__main__":
    main()
