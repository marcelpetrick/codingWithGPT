#!/usr/bin/env python3
"""
Repair structurally-broken unified diffs in a SWE-bench predictions file.

The model's code edits are left untouched. Only the mechanical envelope of the
diff is fixed -- the parts `patch`/`git apply` parse before they ever look at
the edit itself:

  1. markdown fence remnants (``` lines) left in by the extractor
  2. trailing prose after the last diff line
  3. hunk headers whose line counts disagree with the hunk body
     (recomputed from the body -- the counts are redundant metadata)
  4. missing trailing newline (causes "patch unexpectedly ends in middle of line")

Line *numbers* in hunk headers are deliberately not touched: the harness falls
back to `patch --batch --fuzz=5 -p1`, which relocates hunks by context.
"""

import argparse
import os
import json
import re

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\s*(\d+))? \+(\d+)(?:,\s*(\d+))? @@(.*)$")
# Same header, but the model dropped the closing "@@" and ran the section
# heading straight on, e.g. "@@ -30, 7 +26, 6 class MarkEvaluator:".
HUNK_NO_CLOSE_RE = re.compile(r"^@@ -(\d+)(?:,\s*(\d+))? \+(\d+)(?:,\s*(\d+))?\s+(.*)$")
# Placeholder headers the model sometimes emits instead of real numbers,
# e.g. "@@ ... @@" or "@@ -...". The counts are rebuilt from the body and the
# start line is left to `patch --fuzz`, which relocates hunks by context.
PLACEHOLDER_RE = re.compile(r"^@@\s*[-+.\s]*@?@?\s*$")


def is_body_line(line: str) -> bool:
    """True if the line can appear inside a hunk body."""
    return line == "" or line[0] in " +-\\"


def strip_noise(text: str) -> list[str]:
    """Drop fence remnants and any trailing non-diff prose."""
    lines = [l for l in text.split("\n") if l.strip() != "```"]
    lines = [l for l in lines if not l.startswith("```")]

    # Walk back to the last line that is plausibly part of a diff.
    last = -1
    for i, l in enumerate(lines):
        if (
            is_body_line(l)
            or l.startswith("@@")
            or l.startswith("--- ")
            or l.startswith("+++ ")
            or l.startswith("diff ")
            or l.startswith("index ")
            or l.startswith("new file mode")
            or l.startswith("deleted file mode")
        ):
            last = i
    return lines[: last + 1]


def find_hunk_end(lines: list[str], start: int) -> int:
    """Index one past the last body line of the hunk beginning at `start`."""
    i = start + 1
    while i < len(lines):
        l = lines[i]
        if (
            l.startswith("@@")
            or l.startswith("--- ")
            or l.startswith("+++ ")
            or l.startswith("diff ")
            or l.startswith("index ")
        ):
            break
        if not is_body_line(l):
            break
        i += 1
    return i


def recount(body: list[str]) -> tuple[int, int]:
    """Count old-file and new-file lines represented by a hunk body."""
    old = new = 0
    for l in body:
        if l.startswith("\\"):  # "\ No newline at end of file"
            continue
        if l.startswith("-"):
            old += 1
        elif l.startswith("+"):
            new += 1
        else:  # " " context, or a bare empty line the model emitted as context
            old += 1
            new += 1
    return old, new


def repair(patch: str) -> tuple[str, list[str]]:
    """Return (repaired_patch, list_of_fix_labels)."""
    if not patch or not patch.strip():
        return patch, []

    fixes = []
    if "```" in patch:
        fixes.append("fence")

    lines = strip_noise(patch)
    if not lines:
        return patch, []

    out: list[str] = []
    i = 0
    recounted = False
    while i < len(lines):
        line = lines[i]
        m = HUNK_RE.match(line)
        if m is None and line.startswith("@@"):
            m = HUNK_NO_CLOSE_RE.match(line)
        placeholder = m is None and PLACEHOLDER_RE.match(line) is not None
        if m is None and not placeholder:
            out.append(line)
            i += 1
            continue

        end = find_hunk_end(lines, i)
        body = lines[i + 1 : end]

        # A context line the model emitted as "" must become " " so that
        # `patch` does not read it as the end of the hunk.
        body = [(" " if l == "" else l) for l in body]

        old_n, new_n = recount(body)
        if placeholder:
            # No usable numbers at all; start at line 1 and let fuzz relocate.
            old_start = new_start = 1
            suffix = ""
            recounted = True
        else:
            old_start = int(m.group(1))
            new_start = int(m.group(3))
            suffix = m.group(5)
            # Normalise the recovered heading to the standard " text" form.
            if suffix and not suffix.startswith(" "):
                suffix = " " + suffix
            stated_old = int(m.group(2)) if m.group(2) is not None else 1
            stated_new = int(m.group(4)) if m.group(4) is not None else 1
            if stated_old != old_n or stated_new != new_n:
                recounted = True

        # A zero-length side must have start 0 per the unified-diff spec.
        if old_n == 0:
            old_start = 0
        if new_n == 0:
            new_start = 0

        out.append(f"@@ -{old_start},{old_n} +{new_start},{new_n} @@{suffix}")
        out.extend(body)
        i = end

    if recounted:
        fixes.append("hunk-counts")

    repaired = "\n".join(out)
    if not repaired.endswith("\n"):
        repaired += "\n"
        fixes.append("trailing-newline")

    return repaired, fixes


def remap_paths(preds: list, repo_cache: str) -> int:
    """Rewrite `--- a/<path>` headers that name a file missing at the base commit
    but resolvable to exactly one real path by suffix (e.g. `flask/x.py` when the
    tree has `src/flask/x.py`). Ambiguous cases are left alone.
    """
    import subprocess
    from datasets import load_dataset

    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    meta = {i["instance_id"]: (i["repo"], i["base_commit"]) for i in ds}

    tree_cache: dict = {}

    def tree(repo: str, commit: str):
        key = (repo, commit)
        if key not in tree_cache:
            d = os.path.join(repo_cache, repo.replace("/", "__"))
            if not os.path.isdir(d):
                tree_cache[key] = None
            else:
                r = subprocess.run(
                    ["git", "ls-tree", "-r", "--name-only", commit],
                    cwd=d, capture_output=True, text=True,
                )
                tree_cache[key] = set(r.stdout.split("\n")) if r.returncode == 0 else None
        return tree_cache[key]

    fixed = 0
    for p in preds:
        patch = p.get("model_patch", "")
        if not patch.strip() or p["instance_id"] not in meta:
            continue
        repo, commit = meta[p["instance_id"]]
        t = tree(repo, commit)
        if not t:
            continue
        changed = False
        for f in set(re.findall(r"^--- a/(.+)$", patch, re.M)):
            if f in t:
                continue
            cands = [q for q in t if q.endswith("/" + f)]
            if len(cands) == 1:
                patch = patch.replace(f"--- a/{f}", f"--- a/{cands[0]}")
                patch = patch.replace(f"+++ b/{f}", f"+++ b/{cands[0]}")
                changed = True
        if changed:
            p["model_patch"] = patch
            fixed += 1
    return fixed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="predictions_full.json")
    ap.add_argument("--output", default="predictions_repaired.json")
    ap.add_argument(
        "--repo-cache",
        help="Directory of bare/full clones (named owner__repo). Enables path remapping.",
    )
    args = ap.parse_args()

    with open(args.input) as f:
        preds = json.load(f)

    counts = {"fence": 0, "hunk-counts": 0, "trailing-newline": 0}
    changed = 0
    empty = 0

    for p in preds:
        original = p.get("model_patch", "")
        if not original.strip():
            empty += 1
            continue
        fixed, fixes = repair(original)
        if fixed != original:
            changed += 1
            p["model_patch"] = fixed
        for f in fixes:
            counts[f] = counts.get(f, 0) + 1

    remapped = 0
    if args.repo_cache:
        remapped = remap_paths(preds, args.repo_cache)

    with open(args.output, "w") as f:
        json.dump(preds, f, indent=2)

    print(f"input:   {args.input} ({len(preds)} predictions, {empty} empty)")
    print(f"output:  {args.output}")
    print(f"changed: {changed}")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    if args.repo_cache:
        print(f"  path-remap: {remapped}")


if __name__ == "__main__":
    main()
