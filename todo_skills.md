# TODO: make all own skills available in all agent tools

Goal (owner, 2026-09-30): every own skill is available in **claude, claude-dmo, codex and codex-dmo**,
with **one source**: `~/.claude/skills/<name>/SKILL.md`. The other tools only hold symlinks to it.

## State as of 2026-09-30

| Tool | Folder | State |
|---|---|---|
| claude | `~/.claude/skills/` | source, 6 skill folders |
| claude-dmo | `~/.claude-dmo/skills/` | 6 symlinks → `~/.claude/skills/<name>` ✅ |
| codex-dmo | `~/.codex-dmo/skills/` | 6 symlinks ✅ (added 2026-09-30) |
| codex | `~/.codex/skills/` | 5 symlinks ✅, `prepareMilestoneReleaseMPTEA` still an old copy ❌ |

Skills: `currentStatus`, `githubAbout`, `prepareMeeting`, `prepareMilestoneReleaseMPTEA`,
`reviewBranch`, `updateDependencies`.
Not in scope: tool-bundled skills (`synced/` Anthropic skills, Codex `.system/`); they stay per tool.

## Tasks

- [ ] **Replace the old Codex copy with a link.** `~/.codex/skills/prepare-milestone-release-mpt-ea/`
      differs from the Claude version only in `name: prepare-milestone-release-mpt-ea`. A backup is not
      needed beyond that, but keep one anyway:
      ```bash
      mv ~/.codex/skills/prepare-milestone-release-mpt-ea ~/prepare-milestone-release-mpt-ea.bak
      ln -s ~/.claude/skills/prepareMilestoneReleaseMPTEA ~/.codex/skills/prepareMilestoneReleaseMPTEA
      ```
- [ ] **Install the `currentStatus` rewrite** (section below) into `~/.claude/skills/currentStatus/SKILL.md`.
      Reason: the old version only looks for checkbox plans in the repo root and finds nothing in repos
      that use a living document (`ROUND_*.md` with a "Resume here" section, see `AGENTS.md`).
- [ ] **Verify Codex loads the camelCase skills.** Codex's skill-creator asks for lowercase-hyphen names
      (a guideline; not believed to be enforced). Start `codex` and `codex` with the dmo home, list skills
      (`/skills` or ask "which skills do you have"), and confirm all 6 appear once. If they do not:
      rename the skills to kebab-case in `~/.claude/skills/` (folder and `name:`), re-link everywhere,
      and accept that the Claude slash commands change (e.g. `/current-status`).
- [ ] **Verify Claude and claude-dmo** still list all 6 skills (`/skills`) and that `/currentStatus` runs
      the new text.
- [ ] **Keep it that way:** new skills are created in `~/.claude/skills/` only, then linked:
      ```bash
      n=<skillName>; for h in ~/.claude-dmo ~/.codex ~/.codex-dmo; do ln -s ~/.claude/skills/$n $h/skills/$n; done
      ```

## Check commands

```bash
ls -la ~/.claude/skills ~/.claude-dmo/skills ~/.codex/skills ~/.codex-dmo/skills
for h in ~/.claude-dmo ~/.codex ~/.codex-dmo; do for d in $h/skills/*/; do
  [ -L "${d%/}" ] || echo "not a link: $d"; done; done   # only .system/synced should be listed
md5sum ~/.claude/skills/currentStatus/SKILL.md ~/.codex/skills/currentStatus/SKILL.md
```

## Why the claude-dmo session could not finish it

- Its sandbox write-protects `~/.claude/skills` (copy refused as "unwritable").
- Auto mode refused deleting the old Codex copy (local deletion).

## `currentStatus` rewrite (install verbatim)

```markdown
---
name: currentStatus
description: Tiny intermediate status report of the current project (plan done/open, running work, what is next, what waits for others, wall-clock estimate) while the real work continues. Use when the user asks for the current status, a short overview, progress, or what is left.
---

# currentStatus

An immediate, short status report. Do **not** stop, pause or restart running work, subagents
or checks; resume them right after the report.

1. Find the plan, first match wins:
   a. the living document named earlier in this session;
   b. `docs/plan.md`, `plan.md`, `PLAN.md`, `TODO.md` in the current directory, then the repo root;
   c. the newest `ROUND_*.md` / `STATUS*.md` / doc with a "Resume here" section in the current
      project directory.
   Say which file was used. If none is found, say so in one line and skip to step 3.
2. Read progress from it:
   - checkboxes: done `grep -c '^- \[x\]'`, open `grep -c '^- \[ \]'`;
   - otherwise the status table (rows marked done / running / left / open) and the
     "Resume here" section.
3. Check for running work: subagents and checks of this session, plus detached jobs named in the
   plan's check commands (e.g. `pgrep -af` with anchored patterns). Give the newest result/log file
   and its age.
4. Report as a table, at most ~12 rows: done / running / left, with times where the plan has them;
   next (agent-doable); waiting (items marked "maintainer", "waiting", "IT", "owner");
   wall-clock estimate as a range, with long compute runs listed separately;
   uncommitted changes (one line, counts); latest tag / `VERSION` and ahead/behind vs. upstream.
5. No new analysis, no file edits, no questions. Then continue the ongoing work immediately.
```
