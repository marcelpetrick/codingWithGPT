# Primary source: strings extracted from the Claude Code binary

Extracted 2026-09-19 from `/home/mpetrick/.local/share/claude/versions/2.1.278`
(ELF, 224 MiB, not stripped) with `strings -n 20` and byte-offset `dd` reads.

This matters because it is **not** documentation about the product, and not a blog
post. It is the shipped artefact: the literal prompt text the tool sends to the
model. Where the docs paraphrase, this is the thing itself.

Reproduce with:

```bash
BIN=~/.local/share/claude/versions/<version>
strings -n 20 "$BIN" > strings.txt
grep -n "Please analyze this codebase and create a CLAUDE.md" strings.txt
off=$(grep -aob 'function NAo()' "$BIN" | head -1 | cut -d: -f1)
dd if="$BIN" bs=1 skip=$off count=20000 2>/dev/null | tr -d '\000'
```

(The minified symbol `NAo` is a build-specific name and will differ between
versions; grep for the prompt text instead and walk backwards.)

---

## 1. The current, shipped `/init` prompt (verbatim)

> Please analyze this codebase and create a CLAUDE.md file, which will be given to future instances of Claude Code to operate in this repository.
>
> What to add:
> 1. Commands that will be commonly used, such as how to build, lint, and run tests. Include the necessary commands to develop in this codebase, such as how to run a single test.
> 2. High-level code architecture and structure so that future instances can be productive more quickly. Focus on the "big picture" architecture that requires reading multiple files to understand.
>
> Usage notes:
> - If there's already a CLAUDE.md, suggest improvements to it.
> - When you make the initial CLAUDE.md, do not repeat yourself and do not include obvious instructions like "Provide helpful error messages to users", "Write unit tests for all new utilities", "Never include sensitive information (API keys, tokens) in code or commits".
> - Avoid listing every component or file structure that can be easily discovered.
> - Don't include generic development practices.
> - If there are Cursor rules (in .cursor/rules/ or .cursorrules) or Copilot rules (in .github/copilot-instructions.md), make sure to include the important parts.
> - If there is a README.md, make sure to include the important parts.
> - Do not make up information such as "Common Development Tasks", "Tips for Development", "Support and Documentation" unless this is expressly included in other files that you read.
> - Be sure to prefix the file with the following text: [# CLAUDE.md / This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.]

**Reading:** four of the eight usage notes are *negative* constraints whose only
purpose is to stop the model padding the file. The design intent of `/init` was
never "write down everything you found". It was "write down the two things that
are expensive to rediscover". Most complaints about `/init` output being bloated
are complaints about the model under-complying with this prompt, not about the
prompt asking for bloat.

## 2. The unreleased second `/init` (gated)

Gate: `CLAUDE_CODE_NEW_INIT` env var, or the `tengu_slate_harbor_experiment`
feature flag. Both must be off by default, since neither is set on this machine.

Its opening sentence states the entire thesis of the sceptical camp:

> Set up a minimal CLAUDE.md (and optionally skills and hooks) for this repo. CLAUDE.md is loaded into every Claude Code session, so it must be concise — only include what Claude would get wrong without it.

Structure: 8 phases (0 check existing, 1 ask via AskUserQuestion, 2 explore via
subagent, 3 gap-fill interview + proposal, 4 write CLAUDE.md, 5 write
CLAUDE.local.md, 6 skills, 7 hooks/optimisations, 8 wrap-up).

The acceptance test it gives for every line:

> Every line must pass this test: "Would removing this cause Claude to make mistakes?" If no, cut it.

Its explicit **Exclude** list:

> - File-by-file structure or component lists (Claude can discover these by reading the codebase)
> - Standard language conventions Claude already knows
> - Generic advice ("write clean code", "handle errors")
> - Detailed API docs or long references — use `@path/to/import` syntax instead
> - Information that changes frequently — reference the source with `@path/to/import`
> - Long tutorials or walkthroughs (move to a separate file and reference with `@path/to/import`, or put in a skill)
> - Commands obvious from manifest files (e.g. standard "npm test", "cargo test", "pytest")

And it routes content **out** of the always-loaded file by artefact type:

> - **Hook** — deterministic, fast, per-edit shell command (formatting, linting a changed file).
> - **Skill** — on-demand multi-step workflow (`/verify`, `/deploy-staging`, session reports).
> - **CLAUDE.md note** — guidance that shapes behavior but isn't enforced (conventions, communication style).

**Reading:** Anthropic is actively A/B testing a replacement for `/init` whose
whole design premise is that the old one produces files that are too big. That is
the strongest available evidence on the "clutter" question, and it comes from the
vendor's own build rather than from a critic.

## 3. The shipped CLAUDE.md audit doctrine (`/doctor`-adjacent checks)

Check 3 — trim derivable content from checked-in CLAUDE.md files:

> A line of a checked-in CLAUDE.md that a fresh session could reconstruct with a few tool calls (`ls`, `cat`, reading the manifest, `--help`) is dead weight every session it loads into pays for.
>
> The derivability test, per section: could a session working in this repo reconstruct this by reading the code? If yes, cut it. If no, keep it.

**Cut — derivable from the codebase:** directory and file layouts; tech-stack and
dependency lists; build/test/lint commands that are the standard invocation or are
listed in the manifest's scripts; API signatures, type definitions and schemas
copied from source; architecture overviews and repo tours that read like a README
("the codebase is the README"); generic best practices; rules a pre-commit hook,
lint config or CI check already enforces mechanically.

**Keep — not derivable from the codebase:** gotchas and failure contracts ("X looks
safe but does Y"); design rationale; non-standard conventions that DIFFER from
language or tool defaults; agent directives and safety-critical prohibitions
("never push to main"); repo etiquette; domain glossaries; build/test commands that
are NOT guessable; pointers to context that lives elsewhere.

Stated bloat threshold:

> Claude Code warns when a single loaded memory file exceeds roughly 5% of the model's context window in characters, with a floor of ~40,000 chars (`getMaxMemoryCharacterCount` in `src/utils/claudemd.ts`).

Check 4 — migrate always-loaded content to lazy loading: subdirectory-only guidance
→ `<subdir>/CLAUDE.md`; task-specific workflows → a skill (only the one-line
description stays resident); keep universal constraints and safety prohibitions in
the root file, and **never** move a "never do X" rule into a lazy skill.

## 4. Exact load semantics (from the `InstructionsLoaded` hook contract)

> Input to command is JSON with file_path, memory_type (User, Project, Local, Managed), load_reason (session_start, nested_traversal, path_glob_match, include, compact), globs (optional — the paths: frontmatter patterns that matched), trigger_file_path (optional — the file Claude touched that caused the load), and parent_file_path (optional — the file that @-included this one).

The five `load_reason` values are the whole cost model in one enum:

| load_reason | When | Cost profile |
|---|---|---|
| `session_start` | root CLAUDE.md, user CLAUDE.md, unscoped rules | resident for the whole session |
| `compact` | re-injected after compaction | paid again each compaction |
| `nested_traversal` | subdirectory CLAUDE.md, when Claude touches that dir | paid only if you go there |
| `path_glob_match` | `.claude/rules/*.md` with `paths:` frontmatter | paid only for matching files |
| `include` | `@path` imports | resolved at load of the parent — **not** lazy |

`session_start` + `compact` are the expensive ones. `nested_traversal` and
`path_glob_match` are the escape hatch, and are exactly what audit check 4 pushes
content towards.

## 5. Other relevant shipped strings

- Safe mode disables CLAUDE.md entirely: *"Safe mode: all customizations are disabled (CLAUDE.md, skills, plugins, hooks, MCP, agents, and more)"* — so an A/B test against "no CLAUDE.md" is runnable today with `--safe` style flags / minimal mode.
- Minimal mode (`CLAUDE_CODE_SIMPLE=1`) skips *"CLAUDE.md auto-discovery"* among other things — another clean control condition for an experiment.
- `excludedMemoryPaths`-style setting: *"Glob patterns or absolute paths of CLAUDE.md files to exclude from loading... Only applies to User, Project, and Local memory types"* — allows per-file ablation.
- AGENTS.md interop modes: `claude-md` (CLAUDE.md only), `claude-md-or-agents-md` (default; AGENTS.md used where there is no CLAUDE.md), `claude-md-and-agents-md` (both, de-duplicated against what CLAUDE.md already imports), `managed-only`.
- Subagent opt-out: agents can be configured to *"run without the user, project and local CLAUDE.md instruction files when spawned as a subagent; managed policy files are kept. For agents that take everything they need from the delegation prompt."* — i.e. Anthropic ships a switch to turn CLAUDE.md **off** for delegated work, implying they consider it net-negative in that setting.
