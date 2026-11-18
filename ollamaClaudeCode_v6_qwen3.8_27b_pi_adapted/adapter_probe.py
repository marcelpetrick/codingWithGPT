#!/usr/bin/env python3
"""Does the merged adapter change behaviour? Greedy answers to 6 prompts and token logprobs, pi vs base.

Usage: adapter_probe.py HOST PI_TAG BASE_TAG  -> results/adapter_probe.json
"""
import json, sys, urllib.request
from pathlib import Path
PROMPTS = [
    "Write a Python function that returns the n-th Fibonacci number iteratively. Code only.",
    "A pytest run fails with 'ModuleNotFoundError: No module named src'. List the three most likely causes and the fix for each.",
    "You are in a git repo. Give the exact shell commands to find which commit introduced the string 'TODO-42', and nothing else.",
    "Explain in five sentences how Qt's parent-child ownership deletes QObjects.",
    "Write a bash one-liner that prints the 5 largest files under the current directory.",
    "In C++, why can a std::vector<T>::push_back invalidate iterators? Answer in three sentences.",
]
def chat(host, model, prompt):
    body = {"model": model, "stream": False, "logprobs": True,
            "options": {"temperature": 0, "seed": 1, "num_predict": 300},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(f"http://{host}:11434/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))
def main(host, pi, base):
    out = []
    for model in (pi, base):          # all prompts per model: one load each
        out.append([chat(host, model, p) for p in PROMPTS])
    rows = []
    for p, a, b in zip(PROMPTS, *out):
        ta, tb = a["message"]["content"], b["message"]["content"]
        la, lb = a.get("logprobs") or [], b.get("logprobs") or []
        n = 0
        while n < min(len(la), len(lb)) and la[n]["token"] == lb[n]["token"]:
            n += 1
        dl = [abs(x["logprob"] - y["logprob"]) for x, y in zip(la[:n], lb[:n])]
        rows.append({"prompt": p[:50], "identical": ta == tb, "common_prefix_tokens": n,
                     "tokens": [len(la), len(lb)], "mean_abs_dlogprob": round(sum(dl) / len(dl), 5) if dl else None,
                     "max_abs_dlogprob": round(max(dl), 4) if dl else None, "pi": ta, "base": tb})
    Path(__file__).resolve().parent.joinpath("results/adapter_probe.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(f"identical={r['identical']!s:5} prefix={r['common_prefix_tokens']:3}/{r['tokens']} "
              f"mean|dlp|={r['mean_abs_dlogprob']} max={r['max_abs_dlogprob']}  {r['prompt']}")
if __name__ == "__main__":
    main(*sys.argv[1:4])
