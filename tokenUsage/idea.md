
what are reported token numbers for usaege per month for software developers? what does web say, what reddit and so on? what for agentic workflows? give numbers and stats and scales. long research
Which context should the monthly token-usage stats focus on?
Individual freelance/indie developer (Recommended)
Which providers are you most interested in for token-usage numbers?
All of the above, whatever data exists
What types of workloads should be the primary focus?
Coding assistants & agentic dev tools (Recommended)
How would you like the research structured?
Report (detailed markdown, sections, tables) (Recommended)

Active individual developers show reported usage from roughly tens of millions up to several hundred million+ tokens per month, with agentic workflows commonly pushing into the 100M–400M+ tokens/month per developer or owned workflow, according to Reddit self‑reports, GitHub Copilot agent metrics, and independent cost audits.

A full markdown report is attached with the long-form research you asked for — it pulls together Reddit threads, vendor cost breakdowns, GitHub agentic workflow stats, and recent agentic-software-engineering papers, and synthesizes per‑task, per‑session, and per‑month token scales specifically for coding assistants and agentic workflows.
make the report pretty with carts and graphs
monthly_ranges
Generated File
monthly_ranges.png.meta
JSON
agentic_stage_share
Generated File
agentic_stage_share.png.meta
JSON
task_type_tokens
Generated File
task_type_tokens.png.meta
JSON

I’ve added three visuals you can use alongside the report:

    A grouped bar chart showing approximate monthly token ranges (min/max in millions) for hobbyist, moderate, heavy, and agent‑heavy developers.

    A pie chart showing agentic token distribution by stage (code review, completion, coding, design, testing, docs) from the agentic SWE study.

    A log‑scale bar chart comparing tokens per task type (inline completion, code chat, code reasoning, agentic task) to highlight the ~1,000× jump for agentic workflows.

You can drop these PNGs into the markdown report (or a README/blog) and reference the same numbers the text discusses.
one single report as pdf or html
monthly_token_usage_report

Here’s a single self-contained HTML report that pulls everything together (text + charts). You can open it in a browser or print to PDF from there.
are thre tools to check for a (local) codex and claude code installation how man ytokens were burnt? like data or logs? and whow could i process them?
monthly_token_usage_report.html

Yes – both Claude Code and Codex already log detailed token usage locally, and there are ready‑made tools plus simple ways to roll your own processing over those logs.

Below is a practical breakdown aimed at a local, CLI‑driven setup.
Where Claude Code stores token logs

Claude Code writes JSONL transcripts per session on disk with full token breakdowns.

    Default locations:

        Linux/macOS: ~/.claude/projects/**/*.jsonl

        Sometimes: ~/.config/claude/projects/**/*.jsonl

        Windows: %USERPROFILE%\.claude\projects\

    Each line is one event; assistant messages have a usage block, e.g.:

    json
    {
      "type": "assistant",
      "uuid": "…",
      "message": {
        "model": "claude-sonnet-4-6",
        "usage": {
          "input_tokens": 137,
          "cache_read_input_tokens": 815193,
          "cache_creation_input_tokens": 5521,
          "output_tokens": 4260
        },
        "created_at": "2026-06-17T10:23:45Z"
      }
    }

    Claude Code also writes a /usage HTML report to ~/.claude/usage-data/report.html with recent token and cost stats.

So you don’t need API dashboards: you can just parse these JSONL files.
Where Codex stores token logs

Codex does the same thing with its own directory structure.

    Default locations:

        Linux/macOS: ~/.codex/sessions/**/rollout-*.jsonl

        Windows: %USERPROFILE%\.codex\sessions\

    Files are JSONL “rollouts”; they include token_count events with cumulative counts per session; you derive per‑request usage by taking deltas.

Again: everything is local; perfect for your own accounting.
Existing tools for local Claude Code & Codex usage
1. ccusage CLI (multi‑tool usage analyzer)

ccusage is a small CLI that reads local usage logs for Claude Code, Codex and a pile of other coding CLIs and agents.

    It scans ~/.claude/projects and ~/.codex/sessions, totals tokens per day/month, and estimates USD cost using model prices.

    Example usage:

    bash
    # One-off daily report
    npx ccusage

    # Monthly totals
    npx ccusage monthly

    # 5‑hour “billing window” style breakdown
    npx ccusage blocks

    It runs entirely locally; nothing uploaded.

This is the fastest way to get a “how many tokens did I burn this month?” answer across Claude Code + Codex.
2. claude-usage & similar local dashboards

There are dashboards that sit on top of the same Claude logs, e.g.:

    phuryn/claude-usage

        Scans ~/.claude/projects/*.jsonl and stores usage into ~/.claude/usage.db (SQLite).

        Commands: python cli.py scan, python cli.py today, python cli.py week, python cli.py stats, python cli.py dashboard (opens browser UI).

    Claude Code Usage Monitor

        Terminal dashboard for real‑time token / cost usage and predictions; can keep a local “usage warehouse” and export CSV/JSON.

These are nice if you want charts and long‑term history without writing your own tooling.
3. Token Forest & ModelMeter (GUI / SaaS dashboards)

If you want “install once, get charts” options:

    Token Forest (desktop app) scans Claude Code & Codex logs and shows daily/weekly/monthly charts, per‑model breakdown, project view, etc., all computed offline.

    ModelMeter is a collector that reads the same logs and sends only aggregated token counts to a dashboard for cache hit‑rate, burn rate, etc.

For you this is overkill unless you want pretty trend visualizations; ccusage + a small Python script may be enough.
Built‑in views in Claude Code

For ad‑hoc inspection without extra tools:

    /usage in Claude Code: shows current session token usage, weekly cap consumption, and a cost estimate, computed locally from token counts.

    /stats: opens a mini dashboard of sessions, total tokens, model breakdown, and an activity heatmap (using the same local history).

Claude also supports emitting OpenTelemetry metrics like claude_code.token.usage if you prefer to ship everything into Prometheus/Grafana.
Rolling your own processing pipeline

If you want full control or to integrate with your own infra, the logs are easy to parse.
Quick-and-dirty CLI approach

For Claude Code, use jq to inspect one session:

bash
# Show usage blocks from one session
jq 'select(.message.usage) | .message.usage' \
  ~/.claude/projects/<project>/<session>.jsonl

For totals across all sessions, run jq in a loop or with find/xargs, but this gets unwieldy once you want per‑day/per‑model breakdowns.
Minimal Python script for Claude Code

This is roughly what many blog/gist scripts do: walk JSONL, dedupe by uuid, sum usage per model/day.

python
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

CLAUDE_DIR = Path.home() / ".claude" / "projects"

# model -> day -> counters
stats = defaultdict(lambda: defaultdict(lambda: {
    "input": 0,
    "cache_read": 0,
    "cache_write": 0,
    "output": 0,
}))
seen = set()

for path in CLAUDE_DIR.rglob("*.jsonl"):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            uuid = o.get("uuid")
            if not uuid or uuid in seen:
                continue
            seen.add(uuid)

            msg = o.get("message") or {}
            usage = msg.get("usage")
            if not usage:
                continue

            model = msg.get("model", "unknown")
            ts = msg.get("created_at") or o.get("created_at")
            day = ts[:10] if ts else "unknown"

            s = stats[model][day]
            s["input"]      += usage.get("input_tokens", 0)
            s["cache_read"] += usage.get("cache_read_input_tokens", 0)
            s["cache_write"]+= usage.get("cache_creation_input_tokens", 0)
            s["output"]     += usage.get("output_tokens", 0)

# print daily totals
for model, days in stats.items():
    print(f"=== {model} ===")
    for day, s in sorted(days.items()):
        total = s["input"] + s["cache_read"] + s["cache_write"] + s["output"]
        print(day, total, "tokens",
              f"(in={s['input']}, cache_r={s['cache_read']}, cache_w={s['cache_write']}, out={s['output']})")

You can extend this to:

    Dump CSV for each day/model and feed into Grafana/Metabase.

    Multiply tokens by model‑specific prices to estimate EUR/month.

    Aggregate by project folder (Claude encodes project path in the directory name).

For Codex, same idea but reading ~/.codex/sessions/**/rollout-*.jsonl and taking deltas from cumulative token counters.
For non‑local/API usage

For completeness: if you’re calling OpenAI/Anthropic/etc. directly (not via Claude Code / Codex):

    OpenAI’s dashboard shows per‑project token and cost breakdowns, and every API response includes a usage block (prompt_tokens, completion_tokens, total_tokens, plus optional cache/reasoning fields).

    You can also count tokens offline using tokenizers like tiktoken for OpenAI models if you only have text, not logs.

What you probably want in practice

Given your stack and bias for local tools, a pragmatic setup would be:

    Use ccusage to get quick local daily/monthly totals across Claude Code + Codex.

    Run a small Python collector (similar to the snippet above) via cron/systemd to:

        Read ~/.claude/projects and ~/.codex/sessions weekly/daily.

        Write aggregated CSV/SQLite in ~/ai-usage/.

    Optionally feed the CSV into Grafana, Metabase, or DuckDB + a simple dashboard for long‑term trend graphs.

That gives you precise “how many tokens did I actually burn?” for local Codex + Claude Code, with no cloud dependency and easy extensibility.
Artifacts
monthly_token_usage_report
Monthly Token Usage Patterns for Software Developers Using LLMs and Agentic Workflows (2025–2026)
Agentic Stage Share
Task Type Tokens
Monthly Ranges
monthly_ranges.png
monthly_ranges.png.meta.json
agentic_stage_share.png
agentic_stage_share.png.meta.json
task_type_tokens.png
task_type_tokens.png.meta.json
Sources
Web
30
Files
1
