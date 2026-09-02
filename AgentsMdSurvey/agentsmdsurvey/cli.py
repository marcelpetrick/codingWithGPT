"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import report, synth
from .redact import STEMS_FILE, load_stems, redact
from .discovery import discover, mark_duplicates
from .parse import parse
from .stats import UNIVERSAL_MIN_SCOPES, Survey
from .taxonomy import classify_all

DEFAULT_ROOT = Path.home() / "repos"
TEXT_KINDS = {"agents_md", "claude_md", "gemini_md", "codex_md", "skill", "cursor", "windsurf", "copilot"}


def build_survey(root: Path, *, use_git: bool = True) -> Survey:
    """Run the deterministic pipeline end to end."""
    files, repos = discover(root, use_git=use_git)
    duplicates = mark_duplicates(files)

    parsed = {}
    for item in files:
        if item.kind not in TEXT_KINDS or not item.text:
            continue
        document = parse(item.text)
        classify_all(document.directives)
        parsed[item.path] = document

    survey = Survey(str(root), files, repos, parsed, duplicates)
    survey.compute_findings()
    return survey


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentsmdsurvey",
        description="Survey the agent instruction files under a directory of repositories.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=str(DEFAULT_ROOT),
        help=f"directory to scan (default: {DEFAULT_ROOT})",
    )
    parser.add_argument("-o", "--out", default="out", help="output directory (default: out)")
    parser.add_argument(
        "--min-scopes",
        type=int,
        default=UNIVERSAL_MIN_SCOPES,
        help="scopes a rule must appear in to enter the canonical file (default: %(default)s)",
    )
    parser.add_argument("--no-git", action="store_true", help="skip git history (faster, loses staleness findings)")
    parser.add_argument(
        "--redact",
        nargs="?",
        const="@file",
        default="",
        metavar="STEMS",
        help=(
            "mask repository names before writing anything, for output that leaves the machine. "
            f"Bare --redact reads the stems from {STEMS_FILE.name} beside run.py (untracked, one per "
            "line); pass a comma-separated list to override it. Counts are unaffected: only the "
            "names are masked."
        ),
    )
    parser.add_argument(
        "--llm",
        choices=("off", "ollama"),
        default="off",
        help="semantic enrichment of the directives the lexicon missed (default: off)",
    )
    parser.add_argument("--llm-host", default="http://localhost:11434", help="Ollama host for --llm ollama")
    parser.add_argument("--llm-model", default="qwen3.8:30b-a3b-q4_K_M", help="model for labelling clusters")
    parser.add_argument("--llm-embed-model", default="nomic-embed-text", help="model for embeddings")
    parser.add_argument("--cache", default=".cache", help="model-call cache directory (default: .cache)")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    print(f"scanning {root} …", file=sys.stderr)
    survey = build_survey(root, use_git=not args.no_git)

    if args.llm != "off":
        from .llm import enrich

        enrich(
            survey,
            host=args.llm_host,
            model=args.llm_model,
            embed_model=args.llm_embed_model,
            cache_dir=Path(args.cache).expanduser().resolve(),
        )

    canonical = synth.render(survey, args.min_scopes)
    document = report.render(survey, canonical)
    payload = json.dumps(survey.to_dict(), indent=2)

    if args.redact:
        # Masking the finished text rather than the model catches a name
        # wherever it surfaced — a scope, a path, a table cell, a quoted rule.
        if args.redact == "@file":
            stems = load_stems()
            if not stems:
                print(
                    f"--redact found no stems: create {STEMS_FILE} with one name stem per line, "
                    f"or pass them directly as --redact name1,name2.",
                    file=sys.stderr,
                )
                return 2
        else:
            stems = tuple(s.strip().lower() for s in args.redact.split(",") if s.strip())
        canonical, document, payload = (redact(t, stems) for t in (canonical, document, payload))
        print(f"redacted {len(stems)} name stems: {', '.join(stems)}", file=sys.stderr)

    (out / "AGENTS.canonical.md").write_text(canonical, encoding="utf-8")
    (out / "survey.json").write_text(payload, encoding="utf-8")
    (out / "report.html").write_text(document, encoding="utf-8")

    head = survey.headline()
    print(
        f"{head['files_first_party']} first-party files in {head['scopes']} scopes across "
        f"{head['repos_with_instructions']}/{head['repos_scanned']} repositories; "
        f"{head['directives']:,} directives, {head['total_tokens']:,} tokens.",
        file=sys.stderr,
    )
    print(f"wrote {out}/report.html", file=sys.stderr)
    print(f"wrote {out}/AGENTS.canonical.md", file=sys.stderr)
    print(f"wrote {out}/survey.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
