#!/usr/bin/env python3
"""cache-probe.py -- does this runtime cache the prompt prefix, and what is it worth?

New in v4. Ollama 0.33.3 reports `cache_read_input_tokens` on /v1/messages and
0.32.15 did not: every v3 transcript has cache_read = 0. That matters more than a
throughput delta, because an agent turn is "the same long prefix, plus a tool
result at the end" -- exactly the shape a prefix cache serves. v3's rule that
prefill is paid on every turn is derived from a runtime that no longer behaves
that way, so this measures it per model rather than assuming it.

Four requests, in order, with a UUID in the prompt so a cold run is really cold:
  cold      a unique 30k-token prompt            -> cold prefill tok/s
  repeat    byte-identical to the previous       -> pure cache hit
  extend    the same prefix with a new tail      -> the agent-turn case
  unique    a different unique prompt            -> confirms cold is reproducible

Reports prefilled vs cached tokens and the wall clock for each.

Usage: cache-probe.py [--host URL] [--words N] <model> [<model>...]
"""
import argparse, json, time, urllib.request, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent


def call(host, model, text, max_tokens=32):
    body = {"model": model, "max_tokens": max_tokens,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(host.rstrip("/") + "/v1/messages", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "x-api-key": "ollama",
                                  "anthropic-version": "2023-06-01"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    wall = time.time() - t0
    u = d.get("usage", {}) or {}
    new = u.get("input_tokens") or 0
    cached = u.get("cache_read_input_tokens") or 0
    return new, cached, wall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://192.168.100.67:11434")
    ap.add_argument("--words", type=int, default=24000)
    ap.add_argument("models", nargs="+")
    a = ap.parse_args()
    out = HERE / "results"; out.mkdir(exist_ok=True)
    tsv = out / "cache.tsv"
    if not tsv.exists():
        tsv.write_text("model\tphase\tnew_tok\tcached_tok\ttotal_tok\twall_s\timplied_tps\n")
    filler = "alpha beta gamma delta epsilon zeta eta theta. " * (a.words // 8)
    for model in a.models:
        base = f"Unique run {uuid.uuid4().hex}. {filler}"
        other = f"Unique run {uuid.uuid4().hex}. {filler}"
        phases = [("cold", base), ("repeat", base),
                  ("extend", base + " One extra tail sentence appended here."),
                  ("unique", other)]
        for name, text in phases:
            try:
                new, cached, wall = call(a.host, model, text)
            except Exception as e:
                print(f"  {model[:44]:44} {name:8} ERROR {str(e)[:60]}")
                continue
            total = new + cached
            with tsv.open("a") as f:
                f.write(f"{model}\t{name}\t{new}\t{cached}\t{total}\t{wall:.2f}\t{total / wall:.0f}\n")
            print(f"  {model[:44]:44} {name:8} new={new:>6} cached={cached:>6} "
                  f"total={total:>6} wall={wall:6.2f}s  {total / wall:>8.0f} tok/s")
        print()


if __name__ == "__main__":
    main()
