# LinkedIn post text

Post text for [`LI.pdf`](LI.pdf). Paste everything between the two rules as plain
text: LinkedIn does not render Markdown. Upload `LI.pdf` as a document, and give it
the title "Does /init make your AI coding agent better?". The link sits in the post
body because links inside a PDF are not reliably clickable on LinkedIn.

Before tagging anyone, read [`whitepaper_authors.md`](whitepaper_authors.md). It
grades every author, and several must not be tagged.

---

Does /init make your AI coding agent better?

I read every controlled study I could find on CLAUDE.md, AGENTS.md and similar context files. There are six. Short answer: not reliably.

What the evidence shows:

→ No reliable gain on frontier agents. On full benchmarks, the effects on Claude Code, Codex and similar agents all sit within run-to-run noise.

→ The surprise: in the largest study, over 5,000 Claude Code runs, random rules scored exactly as well as expert-written ones.

→ Your file is really two files. The rules get followed. The codebase tour does not help: a summary of code answers 4 of 45 questions about what it does, and the code itself answers 27.

→ What did help: tuning the file against the agent's own mistakes. Tasks solved rose from 25.5% to 33%, on an open 35B model.

→ Stale lines do harm. When file and code disagree, agents follow the file.

What I would do on Monday:
1. Run /init once, as a draft.
2. Delete the architecture tour.
3. Keep only what the repo can't tell the agent: commands, gotchas, "do not" rules.
4. Each time the agent repeats a mistake, add one line.
5. Prune.

The full review is on GitHub, with every source and the verification log. That log includes the mistakes we caught in our own drafts:
https://github.com/marcelpetrick/codingWithGPT/tree/master/claudeCodeInit

Written with Claude. Every number was checked against the original paper.

#ClaudeCode #AIAgents #SoftwareEngineering #DeveloperProductivity

---

## Optional credit line (first comment)

This review rests on open work by Thibaud Gloaguen, Niels Mündler-Sasahara and
colleagues at ETH Zürich; Prakhar Khatri; Brian Sam-Bodden; Asa Shepard and
Jeannie Albrecht at Williams College; Xing Zhang and colleagues; Kushal
Chakrabarti; Damon McMillan at HxAI; and Jai Lal Lulla, Sebastian Baltes,
Christoph Treude and co-authors. Any errors in the synthesis are mine.
