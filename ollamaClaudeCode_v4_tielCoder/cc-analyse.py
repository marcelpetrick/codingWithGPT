#!/usr/bin/env python3
"""cc-analyse.py -- where did a Claude Code session's wall clock actually go?

v3 recorded one number per session (wall seconds) plus a tool histogram, and
could not explain ornith's 308 s. Re-reading v3's transcripts showed why the
number was hard to interpret: every session's time-to-first-token was 23-162 s,
because the model was cold-loaded inside the timed window, and ornith spent
351 s of API time on only 1,101 output tokens -- so "it was thinking" (v3's
hypothesis) could not have been the cause.

This reads one stream-json transcript and reports the parts separately:

  calls        distinct assistant message ids = real /v1/messages round trips.
               v3's "turns" counted content-block events, which is 1-4 per call.
  in/out tok   Claude Code's own modelUsage totals
  think_chars  characters inside thinking blocks (thinking_tokens is always 0
               through Ollama, so characters are the only volume signal)
  api_s/ttft_s from the result event
  max_gap_s    the longest wait between a tool result going in and the next
               assistant event coming out -- a reload shows up here first

Works on v3 transcripts (no timestamps; gap metrics come out as '-') and on v4
transcripts, where cc-session.sh stamps every line with "_t" (epoch seconds).

Usage: cc-analyse.py <transcript.jsonl> [--tsv]   (--tsv prints one tab row)
"""
import collections
import json
import sys

FIELDS = ["calls", "turns", "in_tok", "out_tok", "think_chars", "api_s", "ttft_s",
          "max_gap_s", "tools", "subagents_failed", "is_error"]


def analyse(path):
    ids, tools = [], collections.Counter()
    seen = set()
    think_chars = 0
    result = None
    last_input_t = None
    gaps = []
    for raw in open(path, errors="replace"):
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        t = ev.get("_t")
        kind = ev.get("type")
        if kind == "assistant":
            msg = ev.get("message", {})
            mid = msg.get("id")
            if mid not in seen:
                seen.add(mid)
                ids.append(mid)
                if t is not None and last_input_t is not None:
                    gaps.append(t - last_input_t)
            for block in msg.get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    tools[block.get("name", "?")] += 1
                elif block.get("type") == "thinking":
                    think_chars += len(block.get("thinking", "") or "")
        elif kind == "user" or (kind == "system" and ev.get("subtype") == "init"):
            last_input_t = t
        elif kind == "result":
            result = ev

    out = dict.fromkeys(FIELDS, "-")
    out["calls"] = len(ids)
    out["think_chars"] = think_chars
    out["tools"] = ",".join(f"{k}x{v}" for k, v in tools.most_common()) or "-"
    if gaps:
        out["max_gap_s"] = round(max(gaps), 1)
    if result:
        usage = result.get("modelUsage") or {}
        mu = next(iter(usage.values()), {}) if usage else {}
        out["turns"] = result.get("num_turns", "-")
        out["in_tok"] = mu.get("inputTokens", "-")
        out["out_tok"] = mu.get("outputTokens", "-")
        out["api_s"] = round((result.get("duration_api_ms") or 0) / 1000, 1)
        out["ttft_s"] = round((result.get("ttft_ms") or 0) / 1000, 1)
        out["is_error"] = result.get("is_error", "-")
        stats = result.get("subagent_stats") or {}
        out["subagents_failed"] = stats.get("failed", "-")
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    row = analyse(args[0])
    if "--tsv" in sys.argv:
        print("\t".join(str(row[f]) for f in FIELDS))
    else:
        for f in FIELDS:
            print(f"{f:18} {row[f]}")


if __name__ == "__main__":
    main()
