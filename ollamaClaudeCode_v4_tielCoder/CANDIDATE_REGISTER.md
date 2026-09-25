# Candidate register: every model found, and what was decided

One list of every model this project has found for local agentic coding, with a decision and
its reason. **Check here before pulling anything**: a model listed under *known, not fitting*
has already been decided, and needs new evidence (not a new headline) to come back.

## The use case a model must fit

- **Ollama 0.33.3** on `.67`, driven by **Claude Code** (Anthropic-format tool calls)
- **~35.5 GB usable VRAM**, model **100% resident**, since a spill cost 5× in v1
- **≤ ~26 GiB of weights**, so the 256k KV cache fits beside them. In practice Q4_K_M/Q5_K_M, never below 4-bit
- **MoE with ~3B active** preferred. Dense 27B has been measured 4× too slow here
- **Reliable tool calls**: a gate failure disqualifies, whatever the speed

## How a model is decided

*Note (2026-09-25): reddit.com is blocked for every web tool in this environment, so web search
returns no Reddit results and Reddit pages cannot be fetched. Reddit evidence enters only as threads
the owner pastes.*


1. **Pre-evaluation on the web**: model card, HF community tab, independent measurements,
   Ollama/llama.cpp issues, r/LocalLLaMA. Vendor numbers are recorded as claims.
2. **Testable** only if it fits the box *and* the evidence gives it a real chance to beat the
   field. Merges without evaluation, prunes whose own authors measure them weaker, and models
   already failed here do not qualify.
3. **Testable → screen** (`s10-one.sh`): fit, tool gates, ledger session. Then Terminal-Bench if
   it is screened in. The results go into the round document and `dashboard.html`.

---

## Standing field (measured, in use)

| model | role | decided |
|---|---|---|
| `tiel-coder:35b-q5-ctx256k-agentic` | **the pick** (2026-09-24): 18/18 held-out ×3, visible overflow error | ROUND_2026-09-24.md |
| `qwen3.6:35b-a3b-q4_K_M-agentic` | incumbent: fastest session (60 s), but 15–17/18 held-out | ROUND_2026-09-24.md |
| `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | vision, smallest footprint, 18/18 ×3 | ROUND_2026-09-24.md |
| `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | fastest generation (136 tok/s) | README §field |

## Testable: queued, best first

| # | model | fits? | why testable | state |
|---|---|---|---|---|
| 1 | **occamy-1.0** (Accio-Lab), official GGUF Q5_K_M | 23.9 GiB with projector | trained for agentic work with RL on 15k trajectories. Claims Terminal-Bench 2.1 59.0 vs 49.5 for its base | **done**: 41% [25, 59], 18/18 ×3, 113 s. Does not take the pick |
| 2 | **KAT-Coder-V2.5-Dev** (Kwaipilot), bartowski Q5_K_M | 23.3 GiB | trained with Claude Code as the harness. Claims Terminal-Bench 2.1 41.0 vs 32.0 for its base | screened in 09-25 08:42, Terminal-Bench running |
| 3 | **Ornith-1.5-35B-A3B** (ornith-ai, official GGUF Q5_K_M), added 2026-09-25 | 24.5 GiB with projector | the full model, not the 27B prunes ruled out below. 3.9M GGUF downloads. One **independent** agent eval (Pi Coding Agent, 3 tasks, 1 run each, CPU-only): faster than Qwen3.6-MTP on all three (125 vs 193 s, 32 vs 104 s) and passed a 16k-context log task that Qwen failed. Vendor claims Terminal-Bench 2.1 67.8 (implausible for A3B). **Against it:** the original repo's tab reports broken basic tool calls and looping (#8, #18), and it self-identifies as Claude (#18). Our G2 settles the tool-call question in 10 min. Sampler t 0.6 / top_p 0.95 / top_k 20 | queued after KAT, before ByteShape |
| 4 | **ByteShape Qwen3.6-35B-A3B** Q4_K_S-4.22bpw | 17.9 GiB with projector | control: the incumbent's weights 4 GB lighter. Tests whether VRAM can be freed at no cost | queued |

## Known, not fitting: decided, not pulled

| model | fits? | decision and evidence | decided |
|---|---|---|---|
| **Laguna XS 2.1** (Poolside 33B-A3B) | yes, 18.9 GiB | **failed our tool gate**: 8/10 in v3, the same defect class that disqualified nemotron-cascade-2. No Laguna fix in Ollama 0.33.0–0.34.4, and every fix predates our test. No independent report found, only SEO blogs. Its claimed Terminal-Bench 2.0 of 37.5 is modest. Back only with a changelog that fixes its tool calls | 2026-09-24 |
| **Xing4.0-29B-A4B** (China Telecom XingChen, official, HF 2026-09-16) | yes, 17.6 GiB Q4_K_M | **blocked on runtime support, not on merit.** Its architecture `xing4_0` (mHC + MLA + MTP) is new, and its own tab says "All 5 inference framework PRs are still pending". Ollama 0.33.3's llama.cpp cannot load it. On merit it would be testable: claims SWE-V 75.0 and Terminal-Bench 2.1 57.5 against Qwen3.6-35B-A3B and gemma4, is tuned for Claude Code/OpenCode, and one user reports "on par with Qwen3.6 35B in thinking mode". **Recheck when llama.cpp merges `xing4_0` and an Ollama release bundles it** | 2026-09-25 |
| K2-Horizon-MoVA-36B-A4B (IFM/MBZUAI) | Q4 20.8 GiB | **blocked on runtime**: its card says upstream llama.cpp cannot load the MoVA architecture and needs the IFM fork. Claims Terminal-Bench 2.1 58.6. Recheck when upstream support lands | 2026-09-25 |
| Agnes-3.0-Flash (09-11) | yes, dense | 33B **dense** (72 layers, custom `agnes` architecture). Dense has been 4× too slow here, and llama.cpp support is unclear | 2026-09-25 |
| HF sweep 2026-08-15 → 09-25, the rest | — | ISOM-R1-Coder-16B (no GGUF, NC-ND licence), AMD Instella-MoE (non-GGUF quants), Tev1-4B (dense 4B router), needle3 (edge tool-router), Edge0-35B-A3B (LoRA plus offload trick on qwen3.6), APUS-OpenJev (decision model), AliceAI-80B-A3B (~45 GB), MiMo-V2.6-Flash (multimodal, oversized). Plus dozens of repacks and abliterations of known bases | 2026-09-25 |
| **Agents-A1** (InternScience 35B MoE), suggested 2026-09-25 | yes, 19.7 GiB Q4_K_M | built on **Qwen3.5**-35B-A3B (older than our qwen3.6), June 2026. A general research/science agent, not a coder: its card has GAIA 96.0 and IFEval 94.8 but **no SWE-bench or Terminal-Bench**. Its own tab: "tool calling fail is an artifact of post training" (#13), "Model broken" (#7), chat-template problems (#31), and benchmark skepticism (#9, #15). Recommends presence_penalty 1.1, which costs 41–52% of generation here. The "#2 on a 45-task agent board" claim was not found at any source | 2026-09-25 |
| Agents-A1-vision ("AI-TAVS") | ? | **does not exist** on Hugging Face under that name | 2026-09-25 |
| Laguna XS.2 | yes | the **predecessor** of Laguna XS 2.1, which failed our tool gate (above) | 2026-09-25 |
| Ornith-1.5-27B-A3B-Coder / CoderX | yes | expert prune of Ornith-1.5 without retraining. The source's own tab: "fails the most basic tool calls", "constant looping". The pruner's own evals rank it weakest at planning | 2026-09-24 |
| Qwen3.6-27B-A3B-Coder | yes | a community prune, **not an official Qwen release**. Lowest tool-eval score (123/176) in its own author's table | 2026-09-24 |
| KAT-Ornith-Coder-35B-A3B | yes | quant-only. The source repo is deleted, with no card and no numbers | 2026-09-24 |
| Qwen-35B-A3B-SignOfFour-Coder | yes | unevaluated four-way merge with a custom chat template, so it is a tool-parse risk | 2026-09-24 |
| Qwen3.6-27B-Omnimerge-v4, Qwen3.8-27B-Omnimerge-v6 | yes, dense | dense merges. v4 leaks unclosed think tags by its author's account | 2026-09-24 |
| glm-4.7-flash (Z.ai 30B-A3B) | yes | January 2026. Behind qwen3.6 on Artificial Analysis (index 15 vs 18–19, 78 vs 120 tok/s). A long run of Ollama tool-call bugs | 2026-09-24 |
| qwen3-coder:30b | yes | July 2025, no thinking mode, ~50 SWE-V. Superseded by qwen3.6 | 2026-09-24 |
| Qwen3.6-27B dense | yes, dense | owner's call: the dense shape does not earn a slot | 2026-09-21 |
| **"Qwen3.8-35B-A3B"** (suggested 2026-09-24 as "best speed-oriented Qwen3.8 MoE") | yes | **there is no official one**: no Qwen repo, no Ollama tag. What exists is `empero-ai/Qwen3.8-35B-A3B-Distill` (Sep 16, 133k GGUF downloads), a **community distill onto Qwen3.6-35B-A3B** claiming "internal Qwen3.8 teacher traces", which a third party cannot have. It reports MMLU/ARC only and no agentic numbers. Trained on **8,192-token examples**, and its own card says long context may be degraded, which is fatal at 256k agentic. Its HF tab: flagged as spam (6 upvotes), and "core reasoning is still heavily qwen3.6". Mirrors are abliterated/APEX variants of the same | 2026-09-24 |
| qwen3.8:27b (official, dense), suggested 2026-09-24 as "best quality, Q5_K_M" | yes, dense | **measured**: 18/18 but 787 s ledger median, 4× the field. The suggestion's Terminal-Bench 2.1 73.0 is Qwen's own number on a "corrected" task set. A Q5_K_M quant makes a dense model **slower**, not faster, since decode is bandwidth-bound. Reopens only after the Ollama 0.34.4 upgrade (Qwen3.8 prefill acceleration), with one ledger run to check speed | v4, re-checked 2026-09-24 |
| Qwen3.8-Flash-Next (125B-A6B), suggested 2026-09-24 | **no** | ~120 GB at Q4. Active parameters are small, but all the weights must be resident | 2026-09-24 |
| nemotron-cascade-2:30b | yes | **measured**: fastest on the box, but drops one of two parallel tool calls 50% of the time, and ledger 0/3 | v3/v4 |
| nemotron-3.5-lightning:30b | yes | **measured**: 13–14/18 held-out | v4 |
| ornith:35b (1.0) | yes | **measured**: fast (47 s) but 16–18/18. Its 1.5 successor carries the tool-call reports above | v4 |
| cyber-tiel:35b | yes | **measured**: abliterated Tiel, worse on Terminal-Bench (30%), sandbox required. Not for daily use | v4 |
| muse-glimmer:30b, qwen3.6:27b-q8_0, granite4.2:30b, gemma4:31b-it | yes, dense | **measured**: 19–29 tok/s, the dense shape. Muse Glimmer re-suggested 2026-09-25 (SWE-Pro 51.2, DFlash drafter). Its speed was measured here at 28.5 tok/s, so the decision stands | v2/v3 |
| Devstral Small 2 (24B dense) | yes, dense | dense. Four dense models here all ran 19–31 tok/s | v3 |
| Kimi K2.x, GLM-5.x, Laguna S 2.1, DeepSeek V4, Qwen3-Coder-480B | **no** | 118B–1T total. Does not fit 35.5 GB | v3/v4 |

Sources for the 2026-09-24 decisions are listed in `ROUND_2026-09-24.md` § Sources.
