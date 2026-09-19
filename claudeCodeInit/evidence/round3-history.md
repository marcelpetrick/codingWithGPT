# Round 3: why does `/init` exist?

The question behind this round: if the controlled evidence says a context file
does not reliably raise task success, why does Anthropic ship `/init` and
recommend it? Hypothesis tested: **`/init` was designed for a materially weaker
agent than the one running it today, and its value has decayed.**

**Verdict: partly supported.** The *performance* case for a large always-loaded
file has genuinely eroded, and the erosion is traceable in Anthropic's own dated
wording. The stronger claim — that `/init` was a crutch for a bad agent and is now
obsolete — is **not** supported: it shipped fully formed on day one and has
durable non-performance reasons to exist.

## Timeline

| Date | Event |
|---|---|
| 2025-02-24 | **Claude Code launches** (research preview) alongside **Claude 3.7 Sonnet**. `/init` and CLAUDE.md are present in the **first public build** — reported as v0.2.9 with the description string *"Initialize a new CLAUDE.md file with codebase documentation"* (that exact string is still in v2.1.278 today; see `primary-binary-extracts.md`). |
| 2025-03 | Auto-compaction and MCP arrive within weeks — the harness is already under context pressure. |
| **2025-04-18** | **"Claude Code: Best practices for agentic coding."** CLAUDE.md framed **expansively**: "an ideal place" for commands, files, style, testing, environment quirks. **No size limit given.** |
| 2025-05-22 | GA (v1.0.0) with Claude Opus 4 / Sonnet 4. |
| 2025-06-30 | **Hooks** ship — deterministic automation leaves prose. |
| 2025-07-24 | **Subagents** ship — isolated delegated context. |
| 2025-08-12 | Sonnet 4 gets a 1M-token context window (beta). |
| **2025-09-29** | **"Effective context engineering for AI agents"** — CLAUDE.md is now the *eager* half of a hybrid, contrasted with just-in-time glob/grep. Same day: Sonnet 4.5 and Claude Code v2.0.0. |
| 2025-10 | **`/doctor`**, the **Explore subagent** (*"Powered by Haiku it'll search through your codebase efficiently to save context!"*), and **Skills** all ship within one week. |
| 2025-12-10 | **`.claude/rules/` with `paths:` scoping** — the first *conditional* loading mechanism. |
| 2026-02-12 | Gloaguen et al. submit the AGENTS.md ablation. |
| 2026-02-25 | **Auto-memory** ships — the system now writes its own memory. |
| ~2026-09 | Current docs give a **numeric ceiling for the first time**: *"target under 200 lines… Bloated CLAUDE.md files cause Claude to ignore your actual instructions."* Guidance is explicitly **subtractive**. |

## The documented retreat

Anthropic's framing of the same mechanism, in its own words, over 17 months:

1. **April 2025** — "an ideal place" for documentation, no limit.
2. **September 2025** — the "naively dropped into context up front" half of a hybrid.
3. **September 2026** — hard 200-line target, warning that excess causes the model
   to *ignore* instructions, plus instructions to offload to Skills and rules.

**Important correction to round 1's reading of "naively".** The verbatim sentence,
re-fetched and confirmed by the lead session, is:

> *"Claude Code is an agent that employs this hybrid model: CLAUDE.md files are
> naively dropped into context up front, while primitives like glob and grep allow
> it to navigate its environment and retrieve files just-in-time, **effectively
> bypassing the issues of stale indexing and complex syntax trees**."*

Round 1 characterised this as "Anthropic's own engineers calling CLAUDE.md naive"
— a mild self-critique. In full context that is an **over-reading**. "Naively"
describes the *loading strategy* (eager and unconditional) as opposed to
just-in-time, and the paragraph presents the hybrid **favourably**. It is evidence
of a design taxonomy, not a confession. Cited that way from here on.

## What actually changed: substitutes, not a reversal

Every major Claude Code feature shipped after launch is architecturally a way to
**stop putting things in the always-loaded file**:

| Feature | Date | What it removes from CLAUDE.md |
|---|---|---|
| Hooks | 2025-06 | anything you wanted *enforced* |
| Subagents | 2025-07 | research context |
| Explore subagent | 2025-10 | exploration cost — explicitly justified "to save context" |
| Skills | 2025-10 | occasional domain procedures |
| `paths:`-scoped rules | 2025-12 | guidance needed only for some files |
| Auto-memory | 2026-02 | the need to hand-author memory at all |

This is the strongest form of the argument, and it does not depend on reading any
tea leaves: the product grew cheaper homes for content that once had only one home.

## Evidence for decay

- The documented retreat above, timed to the arrival of those substitutes.
- Gloaguen et al. find no reliable success benefit on frontier-model Claude Code.
- **Weakest-model signal:** the research pass reports that Qwen3-30B-Coder — the
  weakest model in Gloaguen's study — shows the *largest* visible gain from context
  files, while Sonnet-4.5 is flat-to-negative. **Caveat: this is a visual read of
  a bar chart (Figure 3), not an author-stated finding, and the pass that reported
  it also reported p-values that do not exist in the paper.** Treat as suggestive
  only.
- General precedent: Li et al. ([arXiv:2407.16833](https://arxiv.org/abs/2407.16833))
  show long context overtakes RAG as models strengthen — a scaffolding technique
  whose edge shrank with capability.

## Evidence against

- **`/init` shipped on day one, fully formed.** Not a patch added after watching
  the agent struggle. That weakens "designed as a crutch".
- **Aider inverts the weak-model story:** Aider's FAQ says it may *disable* the
  repo map for weaker models because they "get easily overwhelmed and confused by
  the content of the repo map." The ability to *exploit* structured upfront context
  may itself scale with capability — so weak models do not automatically benefit
  more.
- **No study tracks one scaffolding technique across successive model generations**
  and shows the benefit shrinking. The cleanest analog (RAG vs long context) is a
  different technique.
- **Durable non-performance reasons** that cannot decay:
  - **Migration.** `/init` ingests `.cursor/rules/`, `.cursorrules`,
    `.github/copilot-instructions.md`, and behind a flag AGENTS.md, Windsurf,
    Devin and Cline rules. This is ecosystem capture, not model assistance.
  - **Onboarding/activation.** A first successful interaction that also teaches the
    memory system exists.
  - **Team documentation.** A human-readable artefact checked into git.
  - **A bad draft beats a blank page** — editing is easier than authoring.

## Reliability note on this round

The history pass re-reported significance figures for Gloaguen (p<0.001, p=0.21)
and called the benchmark "CTXBench". The **full-text read in round 2 found no
significance testing anywhere in that paper**, and the benchmark is **AGENTbench**.
Where this round conflicts with the full-text read, **the full-text read wins**.
This round's timeline and documentation-evolution claims are retained; its
paper-internal statistics are discarded.
