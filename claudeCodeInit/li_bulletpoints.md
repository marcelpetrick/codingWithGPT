# Ten findings for a LinkedIn post

Paste the block between the two rules as plain text: LinkedIn does not render
Markdown. Every number comes from `whitepaper.md`, and each was checked against the
original paper (see `evidence/verification-log.md`). The sources for each point are
listed below the block.

---

10 things the research says about CLAUDE.md and AGENTS.md

1. No reliable gain. Six controlled studies exist. On full benchmarks, the effect of a context file on Claude Code, Codex and similar agents runs from −5.9 to +4 points, all within chance.

2. But it costs more. In the ETH Zürich study, a context file made each task 20–23% more expensive, because the agent takes extra steps.

3. Random rules scored as well as expert ones. In the largest study (over 5,000 Claude Code runs), random rules and curated rules both solved 63.8% of borderline tasks, against 50.0% with no file.

4. Rules get followed. Name a tool in the file and the agent uses it 1.6 times per task. Leave it out: under 0.01.

5. The codebase tour does not help. A written summary of code answers 4 of 45 questions about what the code does. The code itself answers 27.

6. Better writing won't fix it. A frontier model's summaries scored exactly as poorly as a small 3B model's. The loss is in the format, not the writer.

7. Writing down the agent's mistakes worked. Tuned against the agent's own failures, a guidance file raised tasks solved from 25.5% to 33% (four trials, p < 0.001). The catch: an open 35B model, and it helped the agent find the right file, not write better fixes.

8. A stale file is worse than none. When file and code disagree, agents follow the file, even when it describes the worse code.

9. These files only grow. Across 1,867 repositories they grow 226% over their life, and the older a line is, the less likely anyone deletes it.

10. One run proves nothing. About 9% of results flip between two identical runs. In one practitioner test, a single run made AGENTS.md look 44% slower; over five runs, the same task came out 9–10% better.

What to do: run /init once, delete the architecture tour, keep only what the repo can't tell the agent, and add a line each time it repeats a mistake.

Full review, sources and verification log:
https://github.com/marcelpetrick/codingWithGPT/tree/master/claudeCodeInit

#ClaudeCode #AIAgents #SoftwareEngineering #DeveloperProductivity

---

## Sources, per point

1. Gloaguen et al. [arXiv:2602.11988](https://arxiv.org/abs/2602.11988); Khatri [arXiv:2607.27250](https://arxiv.org/abs/2607.27250); Zhang et al. [arXiv:2604.11088](https://arxiv.org/abs/2604.11088). The six studies are listed in `whitepaper.md`, Finding 1.
2. Gloaguen et al., Table 2.
3. Zhang et al. The result holds only on the 58 of 500 tasks the agent solves some of the time. No single contrast is significant (random vs none: *p*=0.077).
4. Gloaguen et al.
5. Sam-Bodden [arXiv:2607.09691](https://arxiv.org/abs/2607.09691).
6. Sam-Bodden.
7. Shepard & Albrecht [arXiv:2606.20512](https://arxiv.org/abs/2606.20512).
8. Mohammadi et al. [arXiv:2608.16630](https://arxiv.org/abs/2608.16630): *"a stale convention file costs more than no file."*
9. Chakrabarti [arXiv:2608.11095](https://arxiv.org/abs/2608.11095).
10. Sam-Bodden (the ~9% flip rate); Griffiths, Agentic AI Foundation, [*Measuring AGENTS.md*](https://aaif.io/blog/measuring-agents-md-what-five-runs-show-that-one-doesn-t) (the 44% vs 9–10% on the same task).
