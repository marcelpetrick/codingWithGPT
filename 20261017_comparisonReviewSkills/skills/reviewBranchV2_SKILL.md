---
name: reviewBranchV2
description: Risk-based review of the current branch's changes against its integration branch (main/master/develop), reporting up to ten ranked Code and Architecture findings with severity, file path and new-file line number, in human-readable Markdown. Use when the user asks to review the branch, run an ai-review, or check what this branch changed before merging.
---

# Review Branch (v2 candidate)

Do a risk-based review of this branch's changes.

## Scope

Review only what this branch adds on top of its integration branch — nothing else in the
repository, and no pre-existing issues in untouched code.

Determine the base yourself:

1. Of the branches `main`, `master` and `develop`, find those that exist (check local refs and
   `origin/*`).
2. If more than one exists, compute `git merge-base HEAD <branch>` for each and use the branch
   whose merge-base is the most recent commit — that is the branch this work was actually cut
   from.
3. Review `git diff <merge-base>...HEAD`. Use the three-dot form so commits that landed on the
   base branch after the fork point are not attributed to this branch.

State the resolved base branch and merge-base commit at the top of the report, so the user can
tell immediately if the wrong one was picked.

If the diff is empty, say so and stop.

## Categories

Two categories only:

- **Code** — correctness, regressions, edge cases, error handling, data handling, resource
  lifetime and ownership, concurrency, undefined behaviour, numerical edge cases, malformed or
  hostile input, algorithmic complexity, memory use, portability, tests, CI behaviour.
- **Architecture** — module boundaries, coupling, abstractions, API contracts, invariants that
  now span too many places, migration and rollout risk, observability, and whether the design
  fits the surrounding codebase.

Ignore security-specific concerns and pure style or formatting nits unless they cause a concrete
Code or Architecture defect.

## How to review

Depth over speed. Think hard before concluding, and spend the tool calls: open every file the
diff touches, read the surrounding code, and follow the call sites that matter. Trace real
control and data flow instead of pattern-matching on how the code looks — follow a value from
where it enters to where it is used, work the error path and not just the happy path, and ask
what input breaks each assumption.

Removed and bypassed behaviour gets its own pass. For every check, guard, validation, required
field, error path or cleanup that the diff deletes, weakens, narrows or routes around — including
a new early return, exception list, fallback or special case — name the invariant it enforced and
find the place in the new code that still enforces it. If no place does, that is a finding. Do not
clear such a change because the remaining code looks consistent; clear it only when you have found
where the invariant is re-established.

Verify every finding against the actual file contents before reporting it. A finding confirmed
in the code is worth more than three suspected from reading the patch. Drop anything that could
not be confirmed; drop anything speculative. Do not invent issues to fill the list, and never
report a problem that the changed code already handles somewhere that was not read.

## Output

Human-readable Markdown. No JSON, no machine-readable block, no preamble about what is about to
be done — print the report and nothing else.

```
Base: <branch> @ <merge-base short sha>   Head: <short sha>
Files changed: <n>   +<added> / -<removed> lines
```

Then **Findings**: up to ten, the worst first, ranked by real impact. Fewer is correct when fewer
are real — zero findings is a legitimate result, and if the branch is clean, say so plainly.
Never pad to ten.

One block per finding, in exactly this shape:

```
#1  HIGH  Code  path/to/File.cpp:142
    What is wrong, and why it matters here. What should change instead.
```

- Rank starts at 1 for the worst.
- Severity is HIGH, MEDIUM or LOW:
  - HIGH — likely correctness failure, data loss, crash, or a design mistake that will be
    expensive to undo later.
  - MEDIUM — real defect or design weakness that should be fixed before merge.
  - LOW — worth fixing but not blocking. Omit it entirely if it is speculative.
- Category is Code or Architecture.
- Path is repo-relative.
- The line number is the line in the NEW version of the file — the numbering shown on the
  right-hand side of the diff — not an offset into the patch text and not a count from the hunk
  header. Derive it from the `@@ -a,b +c,d @@` header (the first line after the header is
  new-file line `c`; context and added lines advance the counter, removed lines do not), then
  confirm it by opening the file and checking that the code at that line is what is being
  described. A wrong number points at unrelated code, which is worse than none.
- If the finding concerns removed code or applies to the file or design as a whole, write the
  path with no line number and name the location in the text instead.
- The body is at most two sentences: what is wrong and why it matters, then what should change.
  No filler, no restating the diff.

Close with **Verdict**: one or two sentences — is this branch mergeable as it stands, and if not,
which finding numbers block it.
