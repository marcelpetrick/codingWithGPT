#!/usr/bin/env python3
"""P2 + P4 checks: is the adapter active, does the tag fit, are tool calls and thinking right.

For each tag: wait for an idle box, ask the same questions greedily (temperature 0, seed 1),
read residency from /api/ps, then unload the tag. The adapter counts as active only if the
greedy answers of pi and base differ. A foreign model on the box stops the check (never evicted).

Usage: p2_check.py HOST PI_TAG BASE_TAG   -> results/p2_check.json, exit 0 if every check passes
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "results" / "p2_check.json"
PROMPT = "Write a Python function that returns the n-th Fibonacci number iteratively. Code only."
TOOL = {"type": "function", "function": {
    "name": "write_file", "description": "Write text to a file.",
    "parameters": {"type": "object", "required": ["path", "content"],
                   "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}}
TOOL_PROMPT = "Create the file hello.txt with the text 'hi there'. Use the tool."


def call(host, path, body, timeout=900):
    req = urllib.request.Request(f"http://{host}:11434{path}", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ps(host):
    with urllib.request.urlopen(f"http://{host}:11434/api/ps", timeout=10) as r:
        return json.load(r)["models"]


def wait_idle(host, ours):
    for _ in range(120):
        names = [m["name"] for m in ps(host)]
        foreign = [n for n in names if n not in ours]
        if not names:
            return
        if foreign:
            print("waiting, foreign model resident:", foreign, flush=True)
        else:
            for n in names:
                call(host, "/api/generate", {"model": n, "keep_alive": 0})
        time.sleep(10)
    raise SystemExit("STOPPED: the box did not become idle")


def check(host, tag, ours):
    wait_idle(host, ours)
    opts = {"temperature": 0, "seed": 1, "num_predict": 200}
    t0 = time.time()
    plain = call(host, "/api/chat", {"model": tag, "stream": False, "options": opts,
                                     "messages": [{"role": "user", "content": PROMPT}]})
    load_s = time.time() - t0
    res = {m["name"]: m for m in ps(host)}.get(tag)
    tool = call(host, "/api/chat", {"model": tag, "stream": False, "options": opts, "tools": [TOOL],
                                    "messages": [{"role": "user", "content": TOOL_PROMPT}]})
    calls = tool["message"].get("tool_calls") or []
    out = {
        "tag": tag,
        "answer": plain["message"]["content"],
        "thinking_chars": len(plain["message"].get("thinking") or "") + len(tool["message"].get("thinking") or ""),
        "gen_tok_s": round(plain["eval_count"] / (plain["eval_duration"] / 1e9), 1),
        "first_call_s": round(load_s, 1),
        "size_gb": round(res["size"] / 1e9, 2) if res else None,
        "gpu_share": round(res.get("size_vram", 0) / res["size"], 3) if res else None,
        "context_length": res.get("context_length") if res else None,
        "tool_calls": [c["function"] for c in calls],
        "tool_content": tool["message"]["content"][:300],
    }
    out["tool_ok"] = (len(calls) == 1 and calls[0]["function"]["name"] == "write_file"
                      and calls[0]["function"]["arguments"].get("path") == "hello.txt")
    call(host, "/api/generate", {"model": tag, "keep_alive": 0})
    return out


def main(host, pi, base):
    ours = {pi, base}
    r = {"pi": check(host, pi, ours), "base": check(host, base, ours)}
    r["adapter_active"] = r["pi"]["answer"] != r["base"]["answer"]
    r["pass"] = (r["adapter_active"] and all(r[k]["tool_ok"] for k in ("pi", "base"))
                 and all(r[k]["thinking_chars"] == 0 for k in ("pi", "base"))
                 and all(r[k]["gpu_share"] == 1.0 for k in ("pi", "base")))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(r, indent=1))
    for k in ("pi", "base"):
        x = r[k]
        print(f"{k}: {x['size_gb']} GB, GPU {x['gpu_share']}, ctx {x['context_length']}, {x['gen_tok_s']} tok/s, "
              f"think {x['thinking_chars']}, tool_ok {x['tool_ok']} {x['tool_calls']}")
    print("adapter active:", r["adapter_active"], "| PASS" if r["pass"] else "| FAIL")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
