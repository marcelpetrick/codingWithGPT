#!/usr/bin/env python3
"""
SWE-bench Lite inference — generate patches with a local Ollama model.

Feeds each task instance (issue + repo) to the model via Ollama's
OpenAI-compatible /v1/chat/completions endpoint, extracts the unified
diff from the response, and writes predictions incrementally to a JSON
file so runs can be resumed.

Usage:
    python inference.py                          # all 300 instances
    python inference.py --output preds.json      # custom output path
    python inference.py --start_from 150         # resume at instance 150
    python inference.py --instances subset.json  # run a subset
    python inference.py --max_workers 2          # eval workers (inference is always 1)
"""

import argparse
import collections
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from datasets import load_dataset
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://192.168.100.67:11434/v1"
MODEL_NAME = "qwen3.6:35b-a3b-q4_K_M-agentic"
MAX_TOKENS = 16384
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 5  # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def clone_repo(repo: str, commit: str, tmp_dir: str) -> str:
    """Clone the target repo at the given commit into tmp_dir. Returns path."""
    repo_dir = os.path.join(tmp_dir, repo.replace("/", "__"))
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    # Clone without --depth so we can checkout any commit (SWE-bench uses
    # arbitrary historical commits, not just HEAD).
    subprocess.run(
        ["git", "clone", f"https://github.com/{repo}.git", repo_dir],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", commit],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    return repo_dir


def get_repo_tree(repo_dir: str) -> str:
    """Get the repo file tree."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def get_file_contents(repo_dir: str, files: list[str], max_total_chars: int = 120_000) -> str:
    """Read file contents, stopping when we hit the budget."""
    parts = []
    total = 0
    for f in files:
        fpath = os.path.join(repo_dir, f)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", errors="replace") as fh:
                content = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        if total + len(content) > max_total_chars:
            parts.append(f"\n--- {f} (truncated, budget exceeded) ---\n")
            parts.append(content[: max(0, max_total_chars - total)] + "\n... [truncated] ...\n")
            break
        parts.append(f"\n--- {f} ---\n{content}\n")
        total += len(content)
    return "".join(parts)


def oracle_files(instance: dict) -> list[str]:
    """Files the reference patch edits -- the standard SWE-bench "oracle" context.

    This tells the model *where* to look, not *what* to write; the reference
    patch body is never shown. It is the setting most non-agentic SWE-bench
    numbers are reported under, so results are comparable.
    """
    return sorted({
        line[len("--- a/"):].strip()
        for line in instance.get("patch", "").split("\n")
        if line.startswith("--- a/")
    })


_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def retrieved_files(instance: dict, repo_dir: str, top_k: int = 5) -> list[str]:
    """Rank source files by lexical overlap with the issue text.

    A dependency-free stand-in for BM25: score each candidate by how many
    distinct issue identifiers it mentions, weighted towards rarer ones. Used
    for the honest "no oracle" setting.
    """
    query = collections.Counter(
        t.lower() for t in _TOKEN_RE.findall(
            instance.get("problem_statement", "") + "\n" + instance.get("hints_text", "")
        )
    )
    if not query:
        return []

    candidates = [
        f for f in get_repo_tree(repo_dir).split("\n")
        if f.endswith(".py") and "/tests/" not in f and not os.path.basename(f).startswith("test_")
    ]

    doc_freq: collections.Counter = collections.Counter()
    per_file: dict[str, set] = {}
    for f in candidates:
        try:
            with open(os.path.join(repo_dir, f), errors="replace") as fh:
                toks = {t.lower() for t in _TOKEN_RE.findall(fh.read())} & set(query)
        except OSError:
            continue
        if toks:
            per_file[f] = toks
            doc_freq.update(toks)

    n = len(per_file) or 1
    scored = [
        (sum(query[t] * math.log(1 + n / (1 + doc_freq[t])) for t in toks), f)
        for f, toks in per_file.items()
    ]
    scored.sort(reverse=True)
    return [f for _, f in scored[:top_k]]


def build_prompt(instance: dict, repo_dir: str, context: str = "oracle") -> str:
    """Build the prompt for a single SWE-bench instance."""
    problem = instance.get("problem_statement", "")
    hints = instance.get("hints_text", "")

    # NOTE: do NOT derive these from FAIL_TO_PASS. That field holds test node
    # IDs ("path/to/test_x.py::test_name"), so splitting on "::" yields the
    # *test* files -- never the source files that need editing. An earlier
    # revision did exactly that, and in all 300 instances the model was shown
    # only tests and had to invent the source it was patching. That single bug
    # accounted for the bulk of the "hallucinated context" apply failures.
    if context == "oracle":
        target_files = oracle_files(instance)
    else:
        target_files = retrieved_files(instance, repo_dir)

    if not target_files:  # retrieval found nothing usable
        target_files = [
            f for f in get_repo_tree(repo_dir).split("\n") if f.endswith(".py")
        ][:10]

    tree = get_repo_tree(repo_dir)
    contents = get_file_contents(repo_dir, target_files)

    prompt = f"""You are a software engineer tasked with fixing a bug in a GitHub repository.

## Issue
{problem}
"""
    if hints:
        prompt += f"\n## Hints\n{hints}\n"

    # Extract repo root directory name from the GitHub org/repo path.
    # e.g. "matplotlib/matplotlib" → root dir is "matplotlib"
    # The patch paths must use this as the prefix (or nothing if root-level).
    repo_root = instance["repo"].split("/")[-1]

    prompt += f"""
## Repository: {instance['repo']}
## Commit: {instance['base_commit']}
## Repo root directory: {repo_root}/

### Repository structure (first 80 files):
```
{tree[:4000]}
"""
    if len(tree) > 4000:
        prompt += "... [truncated]\n"
    prompt += "```\n"

    prompt += f"""
### Target files content:
{contents}
"""

    prompt += f"""
## Task
Generate a unified diff (patch) that fixes the issue described above.

Rules:
- Output ONLY the unified diff, no explanation or commentary.
- Use `--- a/<path>` and `+++ b/<path>` headers.
- Paths are relative to the repo root directory ({repo_root}/).
  For files in the repo root, use `--- a/filename.py`.
  For files in subdirectories, use `--- a/subdir/filename.py`.
- Only include files that need changes.
- Preserve existing indentation and formatting.
- The patch will be applied to the repository at the given commit.

Output the diff now:
"""
    return prompt


def extract_patch(response_text: str) -> str | None:
    """Extract a unified diff from the model's response text.

    Tries markdown code fences first, then bare diff.
    """
    # NOTE: only leading whitespace may be stripped. A unified diff must end in
    # a newline -- stripping it makes `patch` report "patch unexpectedly ends in
    # middle of line" and reject the whole file.
    # Try fenced code block
    fence_match = re.search(r"```(?:diff|patch)?\s*\n(--- .*)", response_text, re.DOTALL)
    if fence_match:
        patch = fence_match.group(1).lstrip()
        # Find the end of the diff (next code fence or end of string)
        end_match = re.search(r"\n```", patch)
        if end_match:
            patch = patch[: end_match.start()]
        if patch.startswith("---"):
            return patch.rstrip() + "\n"

    # Try bare diff
    bare_match = re.search(r"(--- a/.*)(?=\n--- a/|\n\+\+\+ b/|\Z)", response_text, re.DOTALL)
    if bare_match:
        return bare_match.group(1).rstrip() + "\n"

    return None


def retry_request(client: OpenAI, prompt: str, instance_id: str) -> str:
    """Send a request with retry logic and exponential backoff."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
            )
            content = response.choices[0].message.content
            # The model may output thinking/reasoning tokens that consume
            # the budget, leaving content empty. Check for that.
            if content:
                return content
            # Check if reasoning consumed the budget
            reasoning = getattr(response.choices[0].message, "reasoning", None)
            if reasoning and len(reasoning) > 500:
                print(
                    f"  [WARN] {instance_id}: model spent {len(reasoning)} chars on "
                    f"thinking, no content left (attempt {attempt}/{RETRY_ATTEMPTS})",
                    file=sys.stderr,
                )
            else:
                print(
                    f"  [WARN] {instance_id}: empty response, retry {attempt}/{RETRY_ATTEMPTS}",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"  [ERROR] {instance_id}: {e} (attempt {attempt}/{RETRY_ATTEMPTS})", file=sys.stderr)

        if attempt < RETRY_ATTEMPTS:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"  [WAIT] retrying in {delay}s...", file=sys.stderr)
            time.sleep(delay)

    return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="SWE-bench Lite inference")
    parser.add_argument("--output", default="predictions.json", help="Output predictions JSON path")
    parser.add_argument("--start_from", type=int, default=0, help="Start from instance index")
    parser.add_argument("--instances", help="Path to a subset JSON (list of instance dicts)")
    parser.add_argument("--tmp_dir", default="/tmp/swebench-inference", help="Temp directory for repos")
    parser.add_argument("--dry_run", action="store_true", help="Print prompts without sending to model")
    parser.add_argument(
        "--context",
        choices=["oracle", "retrieved"],
        default="oracle",
        help="Which source files to show the model: 'oracle' = the files the "
             "reference patch edits (standard SWE-bench oracle setting, "
             "comparable to published numbers); 'retrieved' = lexical retrieval "
             "over the repo, no gold-patch information used.",
    )
    args = parser.parse_args()

    # Load dataset
    print("Loading SWE-bench Lite dataset...", file=sys.stderr)
    if args.instances:
        with open(args.instances) as f:
            instances = json.load(f)
    else:
        ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
        instances = [dict(inst) for inst in ds]  # convert to plain dicts
    print(f"  {len(instances)} instances loaded.", file=sys.stderr)

    # Resume: skip already-completed instances
    existing_ids = set()
    if os.path.exists(args.output):
        with open(args.output) as f:
            existing = json.load(f)
        existing_ids = {p["instance_id"] for p in existing}
        if existing_ids:
            print(f"  Resuming: {len(existing_ids)} predictions already exist.", file=sys.stderr)
            instances = [i for i in instances if i["instance_id"] not in existing_ids]
            print(f"  {len(instances)} instances remaining.", file=sys.stderr)
            # Preserve existing predictions so incremental writes don't lose them
            predictions = list(existing)
    else:
        predictions = []

    if args.start_from > 0:
        instances = instances[args.start_from:]
        print(f"  Skipped to index {args.start_from}: {len(instances)} instances.", file=sys.stderr)

    if not instances:
        print("Nothing to do.", file=sys.stderr)
        return

    # Initialize client
    client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

    # Warm the model
    print(f"Warming model {MODEL_NAME}...", file=sys.stderr)
    try:
        client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
        )
        print("  Model warmed.", file=sys.stderr)
    except Exception as e:
        print(f"  Warm failed: {e}", file=sys.stderr)
        print("  Make sure the model is loaded on the server.", file=sys.stderr)
        sys.exit(1)

    # Create temp dir
    os.makedirs(args.tmp_dir, exist_ok=True)

    # Process instances
    if not predictions:
        predictions = []
    start_time = time.time()

    for i, inst in enumerate(instances):
        iid = inst["instance_id"]
        print(f"[{i + 1}/{len(instances)}] {iid}", file=sys.stderr)

        # Clone repo
        repo_dir = clone_repo(inst["repo"], inst["base_commit"], args.tmp_dir)

        # Build prompt
        prompt = build_prompt(inst, repo_dir, context=args.context)

        if args.dry_run:
            print(f"  [DRY RUN] prompt length: {len(prompt)} chars", file=sys.stderr)
            predictions.append({
                "instance_id": iid,
                "model_patch": "",
                "model_name_or_path": MODEL_NAME,
            })
            continue

        # Send to model
        response_text = retry_request(client, prompt, iid)

        # Extract patch
        patch = extract_patch(response_text) if response_text else None

        if patch:
            print(f"  -> patch extracted ({len(patch)} chars)", file=sys.stderr)
        else:
            print(f"  -> NO patch extracted (response: {repr(response_text[:100])})", file=sys.stderr)

        predictions.append({
            "instance_id": iid,
            "model_patch": patch or "",
            "model_name_or_path": MODEL_NAME,
        })

        # Write incrementally
        with open(args.output, "w") as f:
            json.dump(predictions, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\nDone. {len(predictions)} predictions in {elapsed:.0f}s ({elapsed/max(len(instances), 1):.1f}s/instance)", file=sys.stderr)
    print(f"Predictions written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
