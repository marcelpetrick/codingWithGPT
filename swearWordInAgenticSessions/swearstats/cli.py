"""Command-line interface for Agentic Swear Jar."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

from . import __version__
from .analyzer import SOURCE_NAMES, analyze, load_lexicon, parse_boundary, serialize
from .report import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swear-stats",
        description="Generate private profanity statistics from Claude Code and Codex CLI histories.",
    )
    parser.add_argument("--claude-history", type=Path, default=Path("~/.claude/history.jsonl"))
    parser.add_argument("--codex-history", type=Path, default=Path("~/.codex/history.jsonl"))
    parser.add_argument("--lexicon", action="append", type=Path, default=[], metavar="TSV")
    parser.add_argument("--replace-lexicon", action="store_true", help="use only --lexicon files")
    parser.add_argument(
        "--since", metavar="YYYY-MM-DD", help="include prompts on or after this local date"
    )
    parser.add_argument(
        "--until", metavar="YYYY-MM-DD", help="include prompts through this local date"
    )
    parser.add_argument("-o", "--output", type=Path, default=Path("report.html"))
    parser.add_argument("--json", dest="json_output", type=Path, help="also write aggregate JSON")
    parser.add_argument(
        "--open", action="store_true", help="open the report in the default browser"
    )
    parser.add_argument(
        "--strict-inputs", action="store_true", help="fail if either history is missing"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    requested = {
        "claude": args.claude_history.expanduser(),
        "codex": args.codex_history.expanduser(),
    }
    missing = {source: path for source, path in requested.items() if not path.is_file()}
    if missing and args.strict_inputs:
        for source, path in missing.items():
            print(f"error: {SOURCE_NAMES[source]} history not found: {path}", file=sys.stderr)
        return 2
    for source, path in missing.items():
        print(
            f"warning: skipping {SOURCE_NAMES[source]}; history not found: {path}", file=sys.stderr
        )
    sources = {source: path for source, path in requested.items() if source not in missing}
    if not sources:
        print("error: no history files found", file=sys.stderr)
        return 2

    bundled = Path(str(files("swearstats").joinpath("data/en.tsv")))
    lexicon_paths = [path.expanduser() for path in args.lexicon]
    if not args.replace_lexicon:
        lexicon_paths.insert(0, bundled)
    if not lexicon_paths:
        print("error: --replace-lexicon requires at least one --lexicon", file=sys.stderr)
        return 2
    try:
        lexicon = load_lexicon(lexicon_paths)
        since = parse_boundary(args.since)
        until = parse_boundary(args.until, end=True)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if since and until and since >= until:
        print("error: --since must be on or before --until", file=sys.stderr)
        return 2

    result = analyze(sources.items(), lexicon, since=since, until=until)
    data = serialize(result, sources, len(lexicon))
    output = args.output.expanduser().resolve()
    write_report(data, output)
    if args.json_output:
        json_path = args.json_output.expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    total = data["sources"]["all"]["totals"]
    print(f"Report: {output}")
    print(
        f"Scanned {total['prompts']:,} prompts from {len(sources)} tools; "
        f"found {total['hits']:,} matches in {total['profane_prompts']:,} prompts "
        f"({total['prompt_rate']:.2f}%)."
    )
    for source in ("claude", "codex"):
        if source in data["sources"]:
            totals = data["sources"][source]["totals"]
            print(
                f"  {SOURCE_NAMES[source]}: {totals['hits']:,} matches / "
                f"{totals['prompts']:,} prompts ({totals['prompt_rate']:.2f}%)"
            )
    if args.open:
        webbrowser.open(output.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
