# Does `/init` Help? What the Evidence Says About CLAUDE.md and AGENTS.md

**Marcel Petrick** · **Claude** (Opus 5; revised with Opus 5.5)
First published 19 September 2026 · this version 24 September 2026

Repository: [github.com/marcelpetrick/codingWithGPT/tree/master/claudeCodeInit](https://github.com/marcelpetrick/codingWithGPT/tree/master/claudeCodeInit)

---

## The answer in five points

Claude Code's `/init` command reads your repository and writes a `CLAUDE.md`
file. From then on, the agent loads that file at the start of every session.
Codex, Copilot, Cursor and most other coding agents have the same idea under
another name, usually `AGENTS.md`. We read every controlled study we could find
on whether these files work. Here is what they show.

1. **It does not reliably make a frontier agent solve more tasks.** No controlled
   study has shown Claude Code, Codex or a similar agent reliably solving more
   tasks with a context file. On full benchmarks the effects run from −5.9 to +4
   percentage points, all within chance. The one hint of a gain is odd: random
   rules helped exactly as much as expert-written ones. So whatever helps, it is
   not what the file says.

2. **It does cost more.** In the ETH Zürich study, a context file made each task
   20–23% more expensive, because the agent took extra steps. In money this is
   small: a large file costs about 12 cents over a long session.

3. **The file is really two files, and only one of them works.** Agents follow
   **rules**: name a tool in the file and the agent uses it 1.6 times per task,
   against almost never when you leave it out. Agents gain nothing from a
   **tour of the codebase**. A written summary of code answers 4 of 45 questions
   about what the code does; the code itself answers 27.

4. **One thing did measurably help: writing down the agent's mistakes.** When
   researchers tuned the file against the agent's own failures, tasks solved
   rose from 25.5% to 33.0%, in four repeated trials. But it helped the agent find
   the right file, not write a better fix. And it was an open 35B model, not a
   frontier agent.

5. **These files only grow, and a stale file is worse than none.** Across 1,867
   repositories, context files grow by 226% over their life, and old lines are
   almost never deleted. When the file and the code disagree, agents follow the
   file, even when it describes the worse code.

> **What to do:** run `/init` once as a draft. Delete the architecture tour. Keep
> only what the repository cannot tell the agent itself, and add a line each time
> the agent makes the same mistake twice.

---

## What to do on Monday

1. **Run `/init` once, and treat the result as a draft.**
2. **Delete the architecture tour.** It is the half that was measured not to help,
   and rewriting it will not fix it (Finding 3).
3. **Keep only what the repository cannot tell the agent:** commands that are not
   obvious, required setup, gotchas, conventions that differ from the defaults,
   and things the agent must never do.
4. **Write down what the agent got wrong, not what the repository contains.** This
   is the only change with a tested gain behind it (Finding 4). A line earns its
   place by having prevented a real mistake. Anthropic's own new `/init` uses the
   same test: *"only include what Claude would get wrong without it."*
5. **Write rules as "do not".** In the largest study (over 5,000 runs), the only rules that
   helped on their own were prohibitions, such as *"do not refactor unrelated
   code"*. Every rule that hurt was a positive instruction, such as *"follow code
   style"*. This is a pattern, not yet proof.
6. **Count rules, not lines.** Agents follow fewer rules as the rules pile up and
   as sessions get longer. File length on its own made no measurable difference.
7. **Move rules the agent keeps ignoring into hooks.** A hook runs outside the
   model, so it cannot be forgotten. Move step-by-step procedures into skills, and
   details about one module into a file in that module's folder or a
   `paths:`-scoped rule. These load only when needed.
8. **Prune on a schedule.** Nothing else will. A stale line is worse than a
   missing one (Finding 5). `/doctor` will propose cuts.
9. **Do not expect higher success rates on a frontier agent.** The realistic
   gains are fewer repeated mistakes, rules that get followed, and less time spent
   rediscovering the same facts.
10. **If you use a smaller or local model, the file matters more.** The only
   measured success gain comes from an open 35B model. The advice to prune hard is
   advice for frontier agents.

---

## Finding 1 — No measurable gain on frontier agents

### The studies

Six controlled studies test this question directly. All six are from 2026. All
are preprints or workshop papers. None has been repeated by another team, and
none has been rebutted.

| Study | What they did | What they found |
|---|---|---|
| **Gloaguen et al.**, ETH Zürich (ICLR 2026 workshop) | 4 agent/model pairs, 438 tasks, with and without a context file. **Each task ran once**, with no significance test. | No general gain in success. Files written by an LLM: −0.5 to −2 points. Files written by developers: about +4 points, but **not for Claude Code**. Cost **+20–23%**. |
| **Khatri** | 2 agents, 17 tasks, **each run 3 times**, with a formal test for "no effect" | No measurable effect. But the study could only have detected an effect of about 30 points or more. |
| **Lulla et al.** (ICSE 2026 workshop) | 124 small pull requests, with and without the file | 28.6% faster and 16.6% fewer output tokens. Correctness was checked on only 50 of the 124. |
| **McMillan** | 1,650 sessions, varying file size, position, structure and contradictions | None of these mattered to whether the agent followed the rules. Longer sessions did: **5.6% lower odds** of compliance per function written. |
| **Shepard & Albrecht** | 4 repeated trials on an open 35B model, SWE-bench Verified | **The only significant gain in success: 25.5% → 33.0%**, but only for a file tuned against the agent's failures (Finding 4). |
| **Zhang et al.** | Claude Code with Opus 4.6, 679 real rule files, over 5,000 runs. Success measured only on the **58 of 500** tasks the agent solves some of the time, one run each. | Every rule file beat no file, by 6.9–13.8 points. **Random rules did exactly as well as curated ones** (both 63.8% against 50.0%). No single comparison is significant. |

A seventh, related study tests a slightly different kind of file. Kozyrev et al.
([arXiv:2609.12742](https://arxiv.org/abs/2609.12742)) ran Claude Code with
optimised repository skill documents on three Kotlin projects. The best documents
raised the score by 4.9 points, which the authors say *"cannot be separated from
the agent's run-to-run variance."*

### Why most of these numbers settle nothing

Sam-Bodden ([arXiv:2607.09691](https://arxiv.org/abs/2607.09691)) fixed his method
before collecting any data, then ran the same setup twice:

> *"temperature-0 API inference flips **~9% of per-instance outcomes between
> byte-identical runs**. That is a noise floor under every small effect reported on
> this benchmark, including ours."*

In plain terms: run the same agent on the same task twice, with nothing changed,
and about one result in eleven comes out differently. Every effect measured on a
full benchmark is smaller than that. And the ETH Zürich study ran each task only
once. Another team ran 60,000 agent attempts and found the same thing from a
different angle: *"reported improvements of 2–3 percentage points may reflect
evaluation noise rather than genuine algorithmic progress"*
([arXiv:2602.07150](https://arxiv.org/abs/2602.07150)).

This does not mean nothing can be measured. Run each task several times and
average, and the random flips cancel out. That is how Shepard & Albrecht could
show a real 7.5-point gain. The noise rules out **single-run** results, not the
question itself.

A small example shows how misleading one run can be. The Agentic AI Foundation
measured AGENTS.md on one task with a single run each. The file looked **44%
slower and 41% more expensive**. The author then ran every condition five times.
On that same task, the file came out **9–10% better**. One run pointed the wrong
way. (A second task in the same post showed a larger win.)

Other work agrees that single runs mislead. One run correlates only ρ=0.417 with
an agent's true reliability over many runs
([arXiv:2608.14711](https://arxiv.org/abs/2608.14711)). Single-run pass rates
overstate retry-free success by up to 17.8 points
([arXiv:2606.00920](https://arxiv.org/abs/2606.00920)).

### The one hint of a gain on a frontier agent

Zhang et al. ([arXiv:2604.11088](https://arxiv.org/abs/2604.11088)) ran the
largest study, on Claude Code with Opus 4.6. To save money they kept only the
tasks where the agent without rules succeeds some of the time. On those 58
tasks, all seven kinds of rule file beat having no file. The authors are careful:
no single comparison is significant, and the claim rests on all seven pointing
the same way (sign test, *p*=0.008). The other 442 tasks did not change, so over
the whole benchmark the gain shrinks to about 1.6 points (our calculation).

The striking part is **what** helped. Random rules, rules for the wrong kind of
project, and rules with their sentences shuffled all did as well as expert ones.
The authors call this *"context priming"*: having some rules seems to nudge the
agent, whatever they say. Adding more rules, from 0 up to 50, changed nothing.

> **So:** "context files help" and "context files hurt" are both too strong. Nobody
> has shown that what you write in the file makes a frontier agent solve more
> tasks.

## Finding 2 — It costs more, but not much money

Cost is the one effect that is large and consistent. In Gloaguen et al., a context
file raised the cost per task by **20% on SWE-bench and 23% on AGENTbench**, with
2–4 extra reasoning steps. The rise appeared for every model tested. Lulla et al.
found the opposite on small pull requests, but did not check whether the agents
simply did less work.

More tokens do not mean much more money. Claude Code caches `CLAUDE.md`, so after
the first turn it is billed at the cheap cache-read rate. With Sonnet 5 prices
($2 per million input tokens, $2.50 per million to write the cache, $0.20 per
million to read it):

| CLAUDE.md size | 50 turns, cached | 50 turns, not cached |
|---|---|---|
| 500 tokens | $0.0062 | $0.0500 |
| 2,000 tokens | $0.0246 | $0.2000 |
| 10,000 tokens | **$0.123** | $1.00 |

Caching makes the file about 8 times cheaper, whatever its size.

> **So:** do not shrink your CLAUDE.md to save money. Shrink it so the agent keeps
> following it.

## Finding 3 — The file is two files: rules work, the tour does not

Gloaguen et al. put it in one sentence:

> *"while **instructions** in the context files are **well followed** by coding
> agents, **repository overviews**, although popular and recommended by model
> providers, **are not helpful**."*

**Rules are followed.** When the file names the `uv` tool, the agent uses it 1.6
times per task. When it does not, the agent uses it less than 0.01 times.
Repository-specific tools: 2.5 times against under 0.05.

**The tour does not help.** Most files contain an overview of the codebase: 8 of
12 files written by developers, and every file written by the LLM. Yet the
overview *"does not meaningfully reduce"* the steps the agent needs to find the
first relevant file.

**And a better tour will not help either.** Sam-Bodden tested why. He gave the
agent the right file and changed only how its code was shown:

> *"natural-language summaries of it answer almost none of the behavioral questions
> that the source answers (**4/45 vs. 27/45**)… and **the gap belongs to the
> representation, not the summarizer — a frontier model's summaries score exactly
> as poorly as a 3B model's**."*

A description of code throws away most of what the code says. No writer, human or
model, can put it back. Structured outlines did no better: they solved *"no more
issues than deleting that remainder outright."*

**Rules that go against habit need more care.** A new benchmark tested 12
frontier models on 256 rules placed in project files, system prompts and other
places the agent reads ([arXiv:2608.11727](https://arxiv.org/abs/2608.11727)).
Agents followed 72–86% of rules. Every model did worse, by 3.6 to 7.4 points, on
rules that ask for something the agent would not do by default. Those are exactly
the rules worth writing down.

> **Nobody has yet tested the two halves separately against task success.** That
> experiment is cheap and obvious. It is the most useful gap in this field.

## Finding 4 — What did help: writing down the agent's mistakes

One study found a clear, significant gain in success, and it is the most careful
of the six.
Shepard & Albrecht ([arXiv:2606.20512](https://arxiv.org/abs/2606.20512)) did not
use a generated description. They started from one and **tuned it**: small
synthetic bug-fix tasks showed where the agent failed, and the file was patched
to prevent those failures. On SWE-bench Verified, with the open model
Qwen3.5-35B-A3B, over four independent trials:

| Guidance file | Tasks solved |
|---|---|
| None | 25.5% |
| A plain knowledge base (closest to what `/init` writes) | 28.3% (not tested for significance) |
| **The same file, tuned against the agent's failures** | **33.0%** (*p*<0.001 against both) |

The authors conclude: *"how the guidance is produced is the decisive variable."*

Three limits matter:

1. **It helped the agent find the right place, not write better code.** The tuned
   file produced a usable patch for 14.5 more tasks in every 100. But the share of
   those patches that were correct stayed at about 59%.
2. **It was a mid-size open model.** Not Claude Code or Codex. On an even weaker
   model the tuning failed, because that model could not describe its own
   mistakes well enough.
3. **The file that worked was a record of failures, not a tour of the repository.**

A second study points the same way. Cai et al.
([arXiv:2606.12231](https://arxiv.org/abs/2606.12231)) looked at 160 rule updates
in real projects. After an update, the share of code that followed the rules rose
from 49% to 72%. That measures rule-following, not task success, but it shows that
writing down a mistake changes what the agent does.

> **So:** a description of your repository does not raise a frontier agent's
> success rate. A file that records what the agent got wrong can raise a weaker
> agent's, by helping it find its way.

## Finding 5 — These files only grow, and stale files do harm

Chakrabarti ([arXiv:2608.11095](https://arxiv.org/abs/2608.11095)) followed
247,694 instructions across 1,867 repositories:

- Context files grow by **226%** over their life, a net **+4.9 instructions per
  commit**.
- The **older a line gets, the less likely anyone deletes it.**

The reason is simple. Adding a line is cheap. Proving that removing one is safe is
hard. So nobody removes anything. Cai et al. see the same pattern: developers fix
agent mistakes *"typically by adding new negative constraints rather than editing
existing ones."*

Growth would matter less if old lines stayed true. They do not. 23.0% of AI
configuration files already point to code that no longer exists
([arXiv:2606.09090](https://arxiv.org/abs/2606.09090)). And a stale line is worse
than no line. Mohammadi et al. ([arXiv:2608.16630](https://arxiv.org/abs/2608.16630))
tested seven models in five agent harnesses and found:

> *"where standard and code disagree, agents follow the standard even when it
> prescribes the worse code, so a stale convention file costs more than no file."*

> **So:** a context file needs pruning like any other code. Nothing in the tooling
> does it for you.

---

## Why `/init` exists anyway

If the file does not raise success rates, why ship the command? There are three
honest answers.

**It was there from the start.** `/init` and `CLAUDE.md` shipped in Claude Code's
first public release on 24 February 2025. It was not a fix added after watching
the agent fail.

**The case for a big file has shrunk, and Anthropic's own advice shows it.**

| Date | What Anthropic said about CLAUDE.md |
|---|---|
| April 2025 | *"an ideal place"* for commands, files, style and testing. No size limit. |
| September 2025 | one half of a mix: loaded up front, alongside searching for files when needed |
| September 2026 | *"target under 200 lines"* and *"Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"* |

The advice changed as Claude Code gained cheaper places for the same content:
**hooks** (June 2025), **subagents** (July 2025), **skills** (October 2025),
**path-scoped rules** (December 2025) and **auto-memory** (February 2026). Each one
keeps something out of the file that loads every time.

Anthropic has also built a new `/init`. You can switch it on with
`CLAUDE_CODE_NEW_INIT=1`; it is still off by default in v2.1.282. It asks whether
to set up CLAUDE.md files, skills and hooks, and its prompt says: *"CLAUDE.md is
loaded into every Claude Code session, so it must be concise — only include what
Claude would get wrong without it."* Since v2.1.277 (18 September 2026) Claude
Code also reads `AGENTS.md` directly when a project has no `CLAUDE.md`.

**It has uses that were never about success rates.** `/init` imports rules from
Cursor, Copilot and other tools. It helps new users start. And it produces a
readable file that the team can review in git. A rough draft also beats a blank
page. None of this goes away.

## One rule that explains all of it

Other kinds of prompt scaffolding follow the same pattern. "Think step by step"
helped older models and is now unnecessary on reasoning models: OpenAI's own
guide says *"Avoid chain-of-thought prompts."* The pattern is this:

> **Help that does a job the model can now do itself fades away. Help that gives
> the model facts it cannot find, or rules it cannot guess, keeps its value.**

| Part of the file | What it does | What happens to it | Evidence |
|---|---|---|---|
| Codebase tour | Does a job the agent can do: it can read and search the code | **Fades** | no faster file-finding; 4/45 vs 27/45 |
| Commands, gotchas, prohibitions | Gives facts the agent cannot find, and rules it cannot guess | **Keeps its value** | 1.6× vs <0.01× tool use |

The rule also explains Finding 4. The same kind of file was worth 7.5 points to a
35B model that struggles to find the right file, and nothing measurable to
frontier agents that do not. It even failed on a model too weak to learn from it.
Help pays only inside a window of ability.

## What nobody has measured

1. **The two halves separately**, against task success. Cheap, obvious, not done.
2. **Success, cost and speed together, with repeated runs.** No study does all three.
3. **What stale lines cost in practice.** We know how common they are (23%), and
   that they can hurt, but not how much.
4. **Whether rules survive when a long session is compacted.**
5. **How often `/init` gets facts wrong** about the repository it describes.
6. **Most other agents at all:** Copilot, Windsurf, Cline, Amp, Devin, Junie,
   OpenHands.
7. **Languages other than Python and TypeScript.** Gloaguen et al. warn that
   Python's large share of training data *"might… nullify the effect of context
   files."*
8. **One design across weak and strong models.** Until someone does this, "does it
   help?" is missing a key part: *help whom?*
9. **Failure-tuned guidance on a frontier agent.** The one method that produced a
   significant gain has never been tried on Claude Code or Codex.

---

## How we did this, and how sure we are

**Method.** We ran seven rounds of research between 19 and 24 September 2026, most
of them with several AI research agents working in parallel. We searched academic
papers, vendor documentation and practitioner reports. We read the full text of
every controlled study, not just its abstract. We also produced two sources
ourselves: we read the prompt text inside the shipped Claude Code program, and we
measured the 35 instruction files in our own repositories (median about 1,590
tokens).

**Checking.** We did not trust the research agents. We fetched every important
number again from the original paper. This caught real errors: two agents gave
conflicting numbers from the same paper; one invented p-values that the paper does
not contain; one dismissed a real paper as a fake citation; two statistics that
circulate widely turned out to be made up. The last round caught one of our own
mistakes: we had paired two numbers from **different** tasks in the Agentic AI
Foundation example. `evidence/verification-log.md` records every case.

**Limits.**

- **The evidence is six unrepeated 2026 preprints.** Most are too small to detect
  the effects they report.
- **We ran no experiment of our own.** This is a review of other people's work.
- **The cost tables are calculations**, not measured bills.
- **The literature moves fast.** On 20 September a new search found a study that
  three earlier rounds had missed, and it changed a headline claim. On 24 September
  another search found the largest study of all, public since April and missed by
  every earlier round. Assume this version is also incomplete.

## Sources

**Controlled studies.** Gloaguen et al., [arXiv:2602.11988](https://arxiv.org/abs/2602.11988) ·
Khatri, [arXiv:2607.27250](https://arxiv.org/abs/2607.27250) ·
Lulla et al., [arXiv:2601.20404](https://arxiv.org/abs/2601.20404) ·
McMillan, [arXiv:2605.10039](https://arxiv.org/abs/2605.10039) ·
Shepard & Albrecht, [arXiv:2606.20512](https://arxiv.org/abs/2606.20512) ·
Zhang et al., [arXiv:2604.11088](https://arxiv.org/abs/2604.11088) ·
related: Kozyrev et al., [arXiv:2609.12742](https://arxiv.org/abs/2609.12742)

**Why it works or fails.** Sam-Bodden, [arXiv:2607.09691](https://arxiv.org/abs/2607.09691) ·
Mohammadi et al., [arXiv:2608.16630](https://arxiv.org/abs/2608.16630) ·
Huang et al. (Harness-IF), [arXiv:2608.11727](https://arxiv.org/abs/2608.11727) ·
Chakrabarti, [arXiv:2608.11095](https://arxiv.org/abs/2608.11095) ·
Treude & Baltes, [arXiv:2606.09090](https://arxiv.org/abs/2606.09090)

**Observational.** Arabat & Sayagh, [arXiv:2606.13449](https://arxiv.org/abs/2606.13449) ·
Cai et al., [arXiv:2606.12231](https://arxiv.org/abs/2606.12231) ·
Jiang & Nam, [arXiv:2512.18925](https://arxiv.org/abs/2512.18925) ·
Chatlatanagulchai et al., [arXiv:2511.12884](https://arxiv.org/abs/2511.12884) ·
Yang et al., [arXiv:2607.26819](https://arxiv.org/abs/2607.26819)

**Reliability of measurements.** [arXiv:2608.14711](https://arxiv.org/abs/2608.14711) ·
[arXiv:2606.00920](https://arxiv.org/abs/2606.00920) ·
Bjarnason et al., [arXiv:2602.07150](https://arxiv.org/abs/2602.07150) ·
[arXiv:2609.08149](https://arxiv.org/abs/2609.08149) ·
Griffiths (Agentic AI Foundation), [*Measuring AGENTS.md*](https://aaif.io/blog/measuring-agents-md-what-five-runs-show-that-one-doesn-t), 22 July 2026

**Vendor.** [Claude Code memory](https://code.claude.com/docs/en/memory) ·
[best practices](https://code.claude.com/docs/en/best-practices) ·
[changelog](https://code.claude.com/docs/en/changelog) ·
[pricing](https://platform.claude.com/docs/en/about-claude/pricing) ·
[Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (29 September 2025)

**This repository.** `results.md` (full dossier) · `paper.pdf` (3-page paper) ·
`evidence/` (binary extracts, verification log, self-review)
