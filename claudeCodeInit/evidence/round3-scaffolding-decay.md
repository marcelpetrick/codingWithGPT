# Round 3: scaffolding decay, and the principle that explains this dossier

**Claim tested:** techniques that give large gains on weaker models give smaller
gains — or none, or harm — on stronger ones. If true, a practice validated in 2025
may be worthless in 2026.

**Verdict: real, measured at the edges, but not one law with one number.** It is a
family of independently-confirmed instances governed by a single principle.

## The principle (the intellectual payload of this project)

> **Scaffolding decays when it substitutes for a capability the model now has
> natively. It persists — or grows — when it supplies information the model
> structurally cannot derive, or enforces a constraint it cannot infer.**

This maps exactly onto the split the evidence found inside a context file:

| Half of a CLAUDE.md | Which kind | Predicted fate | What was measured |
|---|---|---|---|
| **Repository overview / architecture tour** | *Substitutes* for a capability — navigating and reading the codebase | **Decays.** The agent can grep now. | No faster file-finding (Gloaguen); prose answers 4/45 behavioural questions vs source 27/45 (Sam-Bodden) |
| **Commands, gotchas, conventions, prohibitions** | *Supplies* non-derivable information and *enforces* constraints | **Persists.** | Named tools used 1.6×/task vs <0.01× unmentioned (Gloaguen) |

The principle was derived independently, from CoT and prompting evidence, and then
found to predict the context-file result. That is the strongest thing in this
dossier: two unrelated literatures converging on one mechanism.

## Evidence that scaffolding decays

**Chain-of-thought — the best-measured case, at both ends.**
- Emergence at the bottom: Wei et al. ([arXiv:2201.11903](https://arxiv.org/abs/2201.11903)) — *"chain of thought prompting does not positively impact performance for small models, and only yields performance gains when used with models of ∼100B parameters."*
- Restriction at the top: Sprague et al. ([arXiv:2409.12183](https://arxiv.org/abs/2409.12183), ICLR 2025), 20 datasets × 14 models. Symbolic +14.2pp, math +12.3pp, logic +6.9pp — but **all other categories: 56.8 with CoT vs 56.1 direct.** Authors: *"We do not consider this small improvement a victory for CoT."*
- Redundancy declared by the vendor: OpenAI's reasoning best-practices — *"Avoid chain-of-thought prompts: Since these models perform reasoning internally, prompting them to 'think step by step' or 'explain your reasoning' is unnecessary."*

**Simple scaffolds beating elaborate ones.** Agentless ([arXiv:2407.01489](https://arxiv.org/abs/2407.01489)) on SWE-bench Lite, same model class:

| Approach | Model | Score | Cost/issue |
|---|---|---|---|
| **Agentless** (3 phases, no agent loop) | Claude 3.5 Sonnet | **32.00%** | **$0.70** |
| SWE-agent (custom agent-computer interface) | Claude 3.5 Sonnet | 23.00% | $1.62 |
| SWE-agent | GPT-4o | 18.33% | $2.53 |

Anthropic's own SWE-bench work reached 49% with **two tools** (bash + string-replace):
*"our design philosophy… was to give as much control as possible to the language
model itself, and keep the scaffolding minimal."*

**Scaffolding that hurts a strong model.** Reflexion ([arXiv:2303.11366](https://arxiv.org/abs/2303.11366)):
GPT-4 + Reflexion = 91.0% on HumanEval (vs 80.1% baseline) — but on **MBPP it
underperforms plain GPT-4, 77.1% vs 80.1%.** Same model, same paper.

**Anthropic telling developers to delete scaffolding, in current docs.** On Claude
Opus 5 vs earlier models:
- *"If your prompt contains explicit verification instructions… remove them: instructions like these cause over-verification on Claude Opus 5, and removing them reduces wasted tokens with no loss in quality. The same applies to legacy harness scaffolding that adds separate verification steps."*
- *"Avoid instructing re-checks it already performs… these compound with the model's own behavior and add cost without improving results."*
- Prefill discontinued: *"Model intelligence and instruction following have advanced such that most use cases of prefill no longer require it."*
- *"Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality."*
- General framing: *"smarter models require less prescriptive engineering, allowing agents to operate with more autonomy."*

Independent corroboration: system-prompt diffing (dbreunig.com, 2025-06-03) shows
Anthropic's own system prompt **shedding hot-fixes** between Claude 3.7 and 4.0 —
*"When the new model is trained to avoid 'hackneyed imagery'… there's no need for a
system prompt fix."*

## Evidence against a universal law (kept, because it is disconfirming)

- **Few-shot went the *other* way at GPT-3 scale.** Brown et al.: *"larger models are more proficient at in-context learning"* — the few-shot advantage **widened** with scale. The "few-shot matters less now" claim rests on OpenAI practitioner guidance for reasoning models, **not** a measured cross-generation curve.
- **Prompting still pays, hugely, on a non-reasoning frontier model.** OpenAI's GPT-4.1 guide: prompted persistence + tool-calling encouragement + explicit planning *"increased our internal SWE-bench Verified score by close to 20%"*; induced planning alone **+4%**. GPT-4.1 is not RL-trained for agentic persistence — so the scaffolding still substitutes for a missing capability. **This fits the principle rather than breaking it.**
- **Retrieval scaffolding did not die, it found its threshold.** Anthropic's Contextual Retrieval: failure rate 5.7%→3.7% (−35%), →2.9% with BM25 (−49%), →1.9% with reranking (−67%). Guidance: below ~200K tokens just put it in context; above that, retrieval still pays. A **capacity threshold**, not decay.
- **Scaffolding that is growing:** memory/note-taking for long-horizon runs; fresh-context verifier subagents (*"separate, fresh-context verifier subagents tend to outperform self-critique"*); subagent delegation caps. All supply-or-enforce, not substitute.
- **Aider's repo-map decay is unconfirmed.** No Aider post quantifies whether the repo map's value shrank as agentic search improved. Round 1 implied this; it is **not** substantiated.

## Corrections this round forces on earlier rounds

| Claim | Status |
|---|---|
| Anthropic's "Writing tools for agents" reports a **40% task-time reduction** from rewriting a tool description | **Unconfirmed.** The figure does not appear in the article prose; it may exist only in an unlabelled chart image. **Removed from the dossier.** |
| Aider's repo map is a case of measured scaffolding decay | **Unconfirmed.** Its 70.3% file-localisation and 26.3% SWE-bench Lite figures are real (May 2024), but no measurement of its *decline* exists. Restated as "the strongest 2024-era context result", not as decay evidence. |
| "Scaffolding decay" is a general law | **Overstated.** It is a family of instances governed by the substitution-vs-supply principle. Stated that way. |
