# Project instructions

Assign independent work and review to sub-agents in parallel when their scopes do not overlap. Give each agent a clear outcome and file scope. Integrate the results and run the combined checks in the main session.

Use a lower-cost model for clearly scoped, low-risk work such as listing references or applying a mechanical change with a clear check. Use a stronger model for unclear requirements, architecture, risky changes, and final review.

Ask an advisor for a recommendation when a project rule is unclear, conflicting, or clearly obsolete. The agent may replace obsolete guidance such as Python 2 with the latest compatible, supported stable release allowed by the project’s long-term support policy. Record the recommendation and reasoning. Ask a human to resolve incompatible stakeholder requirements or approve changes to required behavior.

Make routine, reversible implementation decisions within the agreed scope, such as naming a private helper. Seek user approval before expanding scope, changing required behavior, publishing material, or taking an irreversible action.

Use the project’s preferred technologies (HTML, CSS, modern style). Explain any proposed change before adding a replacement.

Use these languages and frameworks: Shell, Python. When a task clearly needs a more domain-specific language, such as a query, shader, build, or hardware description language, use it and record why.

Prefer open-source tools where feasible. Honor explicit exceptions from the project or user, and record why an exception is needed.

Write Unicode-compliant code. Read and write text as UTF-8. Do not assume one byte or one code point per visible character: count, cut, and compare text by grapheme where users see it, and normalize text before comparing it. Test with accents, non-Latin scripts, and emoji.

Use Semantic Versioning for releases. Bump MAJOR for an incompatible public API change, MINOR for backward-compatible functionality, and PATCH for backward-compatible fixes. Update the version and release notes when preparing a release.

Use established tools for the project’s language. For Python, use Ruff for linting and Black for formatting. Choose one formatter per language to avoid conflicting rewrites, and run lint and format checks in the pipeline.

Pin exact resolved dependency versions in version-controlled files. Review them regularly and take compatible updates after verification. For each deferred update, record the requirement or failing check that blocks it.

Use Conventional Commits, for example `fix(parser): handle an empty field`. Keep each commit to one coherent change, include its tests, and put unrelated cleanup in a separate commit. Name the change and reference its requirement when one exists.

Keep the full commit message under 300 characters. Count the subject, body, footers, and all internal line breaks, including blank lines. The maximum is 299 characters.

Keep credentials out of committed files, commit messages, examples, logs, and generated artifacts. Use placeholders in examples and configure real secrets through the project’s approved secret store.

Write instructions like a flight manual. Use familiar words, short sentences, and concrete actions. Explain unfamiliar terms when they are needed, and state how the reader can see that each action is complete.

Record new user inputs and decisions in version-controlled Markdown under the project’s documentation directory. Link the intended outcome and decision rationale to a stable requirement, its implementation, an acceptance check, and the evidence. Use Git for the timestamp and make the checks reproducible from a clean checkout. Name the affected requirement ID in each commit message that implements or changes it.

Challenge requirements before implementation and review every atomic commit. Look for ambiguous goals, counterexamples, missing failure cases, and unsupported claims. Record the reviewed commit SHA, findings, evidence, and how each finding was resolved outside that commit. Reproduce the checks independently from a clean checkout when possible and mark any unverified claim. After each planning change and each implementation iteration, check that the result still fits the requirements and the plan, and repeat the review until it does or a person decides.

Write unit tests for isolated behavior. Check important results, edge cases, and errors with small, repeatable inputs.

Write integration tests for interactions across real module, process, or storage boundaries. Use controlled fixtures and verify the inputs, outputs, and failures on each side of the boundary.

Run end-to-end tests through the normal entry point of a built application. Follow a complete user journey and check its final result and important failure paths.

Agree on an observable acceptance check for each user outcome. Run it under the stated conditions and link the result to its requirement.

Prefer repeatable automated checks. Start with the project’s declared list of supported build targets, then compare it with CI jobs and their results. Build and test each supported target, flag missing or skipped results, and document any manual checks and why they remain.

Run mutation testing on unit tests by deliberately changing behavior, including known return values. Report surviving mutations and investigate whether they expose missing assertions or equivalent behavior.

Require at least 99% executable-line coverage of project-owned production source. Exclude tests, dependencies, and generated outputs. Document and justify any further exclusions before enabling the gate. Join coverage from the required suites and compare executed lines divided by eligible lines without rounding. Fail below the minimum and pass at or above it.

Start from a clean clone. Obtain pinned dependencies, configure the environment, build from repository sources, run every applicable pipeline job, and inspect the results for all declared targets. Document external prerequisites and required secret names, and run without relying on a developer machine or untracked files.

For each new behavior or defect, write one test first and confirm that it fails for the expected reason. Make the smallest change that passes it, then refactor and rerun the relevant suite. Keep the test runnable against both the prior and changed behavior.

Document the architecture with C4. Start with a system context view showing users, the system boundary, and external systems. Use a container view for applications, data stores, and their responsibilities. Add component or code views when a design question needs them, and verify every relationship against the documented design or revision.

Keep editable Mermaid blocks in version-controlled Markdown. State each diagram’s purpose and label its relationships. For C4 views, state the view level and scope. Verify the diagram renders in the intended viewer and update it when the architecture changes.

## Project specifics (mrreview)

This section adds the engineering conventions of this repository. The rules above stay valid.

- Living document: `WORKLOG.md`. Update it after every step. Requirements: `docs/requirements.md` (REQ-*). Owner inputs and decisions: `docs/decisions.md` (D-*).
- Gate: `./localPipeline.sh`. CI (`.github/workflows/mr-review-analytics.yml` in the monorepo root) runs exactly this script. Every commit is green.
- Versions: every commit bumps the patch version in `pyproject.toml` and `src/mrreview/__init__.py` and adds a line to `CHANGELOG.md`. A feature milestone bumps the minor version.
- Tests: unit tests in `tests/unit`, real-HTTP integration tests against `mrreview.demo.fake_gitlab` and `fake_ollama` in `tests/integration`, Chromium tests in `tests/e2e`. The synthetic fixture (`mrreview.demo.fixture`) records the ground truth (`truth`, `applied`) for assertions.
- Security: GitLab access is GET only. The token comes only from `MRREVIEW_GITLAB_TOKEN`. Review text reaches the LLM only with names replaced by role labels. Model output is validated data and is never executed.
- Live data: real GitLab data needs the authorization of VISION.md section 8 and the `--authorized` flag. Ollama live tests use synthetic threads only.
- The dashboard is generated from the database, never edited by hand. Every element that shows a number or a term has a `data-tip` tooltip; `tests/e2e` checks this.
- Markdown files must not contain a double curly brace or a curly-percent pair (the monorepo Pages build runs Liquid).
- Writing: Simplified Technical English, about 80% (see the monorepo `AGENTS.md`).

## Scope widening procedure (owner input D-015)

Widen the analysed scope step by step. Spend the Ollama box in chunks of one hour.

1. Finish the current step before the next one starts. The steps are:
   1. the focus user's projects only (`--focus-user <user> --focus-only`);
   2. the 50 most active projects in the window;
   3. the 100 most active projects;
   4. all active projects.

   The focus user's projects rank first in every step.
2. Run one chunk as `mrreview run <step arguments> --max-minutes 60`. Exit code 0 means the step is done. Exit code 3 means work remains, so run the same step again.
3. Use `scripts/widen.sh` to run the chain. Before each chunk it checks that no other model is loaded on the Ollama box. It waits 10 minutes while the box is busy and stops after 6 failed checks (exit code 4). It stops on any other exit code and when `out/widen.STOP` exists.
4. After each chunk, look at `out/widen.log` and the regenerated `out/real/dashboard.html`. Record the chunk in `WORKLOG.md` with time, step, classified count and anything unusual.
5. Suspect the harness first. Explain a sudden jump in a figure before you start the next chunk.
6. Never commit real data. `out/` is git-ignored. Public documents get aggregate numbers only, with no project or person names.
