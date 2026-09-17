#!/usr/bin/env python3
"""overflow-probe.py -- what happens when the prompt exceeds num_ctx?

The most-repeated finding of v1/v2/v3: overflowing a baked num_ctx did NOT
error. Ollama silently kept half the window (prompt_eval == num_ctx/2 + 2) and
stopped emitting tool calls. v2 called it the worst failure mode on the box; v3
reproduced the exact arithmetic on four models at four window sizes, and noted
that granite4.2 was the ONLY model that returned HTTP 400 instead.

On 0.33.3 Tiel returned `400 ... request (264419 tokens) exceeds the available
context size`. If that is the runtime rather than the model, the silent-halving
era is over and a decade of "keep CLAUDE_CODE_MAX_CONTEXT_TOKENS well under the
baked window" advice changes character: you now get an error, not a wrong answer.

This sends one deliberately oversized prompt (~1.05x the tag's baked num_ctx)
per model and records which of the three regimes came back:
  ERROR_400   the server refused -- loud, safe
  HALVED      prompt_eval ~= num_ctx/2 -- the old silent bug
  OTHER       anything else, printed for inspection

Usage: overflow-probe.py [--host URL] <model> [<model>...]
"""
import argparse, json, re, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def show_ctx(host, model):
    req = urllib.request.Request(host + "/api/show", json.dumps({"model": model}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        p = (json.load(r).get("parameters") or "")
    m = re.search(r"num_ctx\s+(\d+)", p)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://192.168.100.67:11434")
    ap.add_argument("--over", type=float, default=1.05, help="prompt size as a multiple of num_ctx")
    ap.add_argument("models", nargs="+")
    a = ap.parse_args()
    host = a.host.rstrip("/")
    tsv = HERE / "results" / "overflow.tsv"
    tsv.parent.mkdir(exist_ok=True)
    if not tsv.exists():
        tsv.write_text("model\tnum_ctx\tsent_tok_est\tregime\tprompt_eval\tdetail\n")
    for model in a.models:
        ctx = show_ctx(host, model)
        if not ctx:
            print(f"  {model[:44]:44} no baked num_ctx; skipped")
            continue
        unit = "The service handles inbound requests and logs to a shard. "
        uwords = len(unit.split())

        def send(words):
            text = unit * ((words // uwords) + 1)
            body = {"model": model, "stream": False, "think": False,
                    "options": {"num_predict": 16, "temperature": 0},
                    "messages": [{"role": "user",
                                  "content": "Reply with the single word OK.\n\n" + text}]}
            req = urllib.request.Request(host + "/api/chat", json.dumps(body).encode(),
                                         {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=3600) as r:
                    return json.load(r), None
            except urllib.error.HTTPError as e:
                return None, (e.code, " ".join(e.read().decode(errors="replace")[:140].split()))

        # Calibrate: tokens per word varies per tokenizer (1.1-2.1 across this
        # field), and guessing it wrong means the "oversized" prompt fits and the
        # probe measures nothing -- which is exactly what happened on the first
        # attempt (estimated 275k tokens, actually sent 224k).
        probe_words = max(2000, int(ctx * 0.25))
        d0, err0 = send(probe_words)
        if err0:
            print(f"  {model[:44]:44} calibration failed: HTTP {err0[0]} {err0[1][:60]}")
            continue
        tpw = (d0.get("prompt_eval_count", 0) or 1) / probe_words
        target_words = int(ctx * a.over / tpw)
        target = int(target_words * tpw)

        d, err = send(target_words)
        regime = detail = ""
        pe = ""
        if err:
            regime, detail = f"ERROR_{err[0]}", err[1]
        elif d.get("error"):
            regime, detail = "ERROR_OTHER", str(d["error"])[:100]
        else:
            pe = d.get("prompt_eval_count", 0)
            half = ctx // 2
            if abs(pe - half) <= 8:
                regime = "HALVED"
                detail = f"prompt_eval {pe} ~= num_ctx/2 ({half}) -- the v1-v3 silent bug"
            elif pe < ctx * 0.98:
                regime = "SHORT"
                detail = f"prompt_eval {pe} < requested ~{target} (tok/word {tpw:.2f}); prompt fit after all"
            else:
                regime = "OTHER"
                detail = f"prompt_eval {pe}, done={d.get('done_reason')}"
        with tsv.open("a") as f:
            f.write(f"{model}\t{ctx}\t{target}\t{regime}\t{pe}\t{detail}\n")
        print(f"  {model[:44]:44} ctx={ctx:>7} sent~{target:>7} -> {regime:11} {detail[:80]}")


if __name__ == "__main__":
    main()
