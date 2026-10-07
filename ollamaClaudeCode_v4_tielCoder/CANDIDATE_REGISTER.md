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
the owner pastes.* *Update 2026-10-07: the JSON API and HTML are still blocked (403 "blocked by network
security"), but Reddit's **RSS feeds** load (`/r/<sub>/search.rss?q=…&restrict_sr=1&sort=new&t=month`, and
`/comments/<id>/.rss` for a thread with its comments), rate-limited to roughly one request per 2 min. See §
Reddit sweep 2026-10-07.*


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
| `kat-coder-v2.5:q5km-ctx256k-agentic` | **ties the default** (same-version re-baseline 09-25): 45 s, quality PASS, T5 8/8. The equal alternative | ROUND_2026-09-24.md |
| `tiel-coder:35b-q5-ctx256k-agentic` | the pick when overflow safety matters: 18/18 ×5, visible overflow error. 79 s, T5 6/8 | ROUND_2026-09-24.md |
| `qwen3.6:35b-a3b-q4_K_M-agentic` | **the default, confirmed 09-25** on one client version: 48 s, 18,18,18,17,17 (quality PASS), Terminal-Bench 50% | ROUND_2026-09-24.md |
| `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | vision, smallest footprint, 18/18 ×3 | ROUND_2026-09-24.md |
| `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | fastest generation (136 tok/s) | README §field |

## Testable: queued, best first

*09-25: Laguna XS 2.1 moved back here: re-gated under the current setup at Poolside's sampler, 9/10
(T4 partial). The earlier cut rested on v3 data at the GGUF-default sampler (review #10). Screen
queued after the extended round.*

| # | model | fits? | why testable | state |
|---|---|---|---|---|
| 1 | **occamy-1.0** (Accio-Lab), official GGUF Q5_K_M | 23.9 GiB with projector | trained for agentic work with RL on 15k trajectories. Claims Terminal-Bench 2.1 59.0 vs 49.5 for its base | **done**: 41% [25, 59], 18/18 ×3, 113 s. Does not take the pick |
| 2 | **KAT-Coder-V2.5-Dev** (Kwaipilot), bartowski Q5_K_M | 23.3 GiB | trained with Claude Code as the harness. Claims Terminal-Bench 2.1 41.0 vs 32.0 for its base | **done: the new pick** (09-25). 46 s, 18/18 ×3, 10/10, Terminal-Bench 33% [19, 52] |
| 3 | **Ornith-1.5-35B-A3B** (ornith-ai, official GGUF Q5_K_M), added 2026-09-25 | 24.5 GiB with projector | the full model, not the 27B prunes ruled out below. 3.9M GGUF downloads. One **independent** agent eval (Pi Coding Agent, 3 tasks, 1 run each, CPU-only): faster than Qwen3.6-MTP on all three (125 vs 193 s, 32 vs 104 s) and passed a 16k-context log task that Qwen failed. Vendor claims Terminal-Bench 2.1 67.8 (implausible for A3B). **Against it:** the original repo's tab reports broken basic tool calls and looping (#8, #18), and it self-identifies as Claude (#18). Our G2 settles the tool-call question in 10 min. Sampler t 0.6 / top_p 0.95 / top_k 20 | **done**: 41% [25, 59], 18/18 ×3, but 119 s sessions and T5 failed. Does not take the pick |
| 4 | **ByteShape Qwen3.6-35B-A3B** Q4_K_S-4.22bpw | 17.9 GiB with projector | control: the incumbent's weights 4 GB lighter. Tests whether VRAM can be freed at no cost | **done**: Terminal-Bench 52% [34, 69] (top), 35 s, but 16/18 held-out. Not the pick. Confounded with the vendor sampler |

## Sweep 2026-10-07: nothing new to test; K2-Horizon unblocked upstream but does not fit 256k

*Web-only, 2026-10-07. Sources: HF API (trending text-generation, `search=` A3B/A4B/A2B/A5B/A6B/Coder/agentic/SWE by
creation date since 09-20, and the newest repos of ~45 model orgs), llama.cpp PRs created 09-15 → 10-07 (new
architectures), Ollama tags/releases and `LLAMA_CPP_VERSION`, ollama.com newest, the Kilo open-weight catalogue.*

- **Ollama after 0.35.1:** [v0.40.0](https://github.com/ollama/ollama/releases/tag/v0.40.0), tagged 2026-10-06
  (rc1 10-04). Its notes are MLX/Apple Silicon only (MLX by default on Macs, decision models and embeddinggemma-2 on
  MLX); the bundled llama.cpp moves b11232 → **b11351** (10-02). Nothing in it loads `xing4_0`, `k2-horizon` or
  `kolibri1`, and nothing in it is a tool-call fix for the CUDA path. **No reason to upgrade `.67` for the field.**
  Ollama bumps llama.cpp about weekly (09-10, 09-15, 09-22, 09-29, 10-06), so the first release with b11454+ (K2
  Horizon) is likely 0.40.1, about a week out.
- **Blocked entries:** K2-Horizon merged upstream 10-06 but waits for Ollama, and at f16 KV it fits only a ~64k
  window (row below). Xing4.0 and Kolibri-1 are unchanged (rows below).
- **New models since 09-20:** no first-party coder/agentic MoE in the ≤ 26 GiB-at-4-bit class with upstream
  llama.cpp support. The new ones are oversized (Naive-N0.5-Flash 309B, MiMo-V2.6 Flash/Pro, Victoria 49 GiB,
  Ling 3.1 Flash, GLM-5.3 FlashX/Prime, Mistral Large 4, all cloud-class), on a custom runtime (Agens-Volundr-32B),
  dense 27B fine-tunes, sub-4-bit quants, abliterations, or drafters. The rows are in the next table, marked *10-07*.
- **Testable list: unchanged.** No new entry.

## Reddit sweep 2026-10-07: nothing new to test; one blocked entry, field evidence from two independent benchmarks

*Web-only, 2026-10-07. Reddit RSS search (sort=new, t=month) over r/LocalLLaMA (25 queries: coding/agentic/tool
calling/Claude Code/A3B/24–32 GB, and every field and register model by name), r/ollama (3), r/LocalLLM (2),
r/ClaudeCode (2), r/ClaudeAI (1); 263 unique threads, 21 read in full with comments. Claims below are Reddit
claims; new models were cross-checked on HF and llama.cpp.*

- **New testable candidates: none.** Every new name in the 24–36 GB class is a fine-tune of a measured base, dense,
  below 4-bit, or not yet public (rows marked *R 10-07* below). Community consensus in the period: no Qwen3.8 small
  MoE exists or is announced ([1wn4c4e](https://www.reddit.com/r/LocalLLaMA/comments/1wn4c4e/), 09-22), so the
  A3B class is fine-tunes of qwen3.6/Ornith.
- **Independent field benchmark** ([1wss436](https://www.reddit.com/r/LocalLLaMA/comments/1wss436/), u/returnity,
  09-28): Aider Polyglot at Q8, one template for all. Pass@2: **base qwen3.6 71.0%**, occamy 70.1%, Ornith-1.5 63.6%,
  **KAT-Coder-V2.5-Dev 58.9% but 84 s/case vs 285 s for base** (fewest tokens by far), **Tiel 53.3%**, Nex-N2.5-mini
  30.8%. tau2-bench: base 86.0% vs occamy 79.8% (retail), 78% vs 80% (airline). **Agrees with our pick of the base
  as default and with KAT as the fast alternative.** Caveats in-thread: Aider's edit-diff format does not suit the
  tool-call-trained Ornith/Tiel; the Tiel author says Tiel's edge is its Q4 imatrix and does not show at Q8 (we run
  Tiel at Q5); one user reports KAT "caught in loops that seem to go forever" on large or ambiguous tasks. Several
  users report the opposite ranking in agentic harnesses (Tiel > base, [1wnkrt8](https://www.reddit.com/r/LocalLLaMA/comments/1wnkrt8/),
  09-22/24). Net: a tie in our sense, no change.
- **Independent Ollama screen** ([1wy2m03](https://www.reddit.com/r/LocalLLaMA/comments/1wy2m03/), 10-05, Ollama
  library `ornith-1.5:35b` Q4_K_M, pi harness, 9-step session + 10 coding tasks): Ornith-1.5 9/9 + 10/10, **Laguna XS
  2.1 passed both**, **North Mini Code 1.0 only 4/9**. A second user: Ornith loops in thinking and overruns 262k on
  long multi-requirement tasks (matches our 119 s sessions / T5 fail).
- **Laguna XS 2.1 (queued)** ([1wro594](https://www.reddit.com/r/LocalLLaMA/comments/1wro594/), 09-27): the stock
  template lets XS skip thinking "right when it needs it most" and forces `preserve_thinking` on; a community
  template adds `force_thinking`/`reasoning_effort`. "Quite glitchy". **For the screen: record which template the
  GGUF carries, and keep the stock one** (template changes are an A/B arm, not the main row).
- **gemma4:** Google fixed the chat template end of July (looping every few turns before), and quantizers re-uploaded
  ([1wnhji0](https://www.reddit.com/r/LocalLLaMA/comments/1wnhji0/), 09-22). Our 3× 18/18 is consistent with the fixed
  one; the tag's template date is not recorded. One 10-02 tool-call tier list puts Gemma-4-26B top
  ([1ww528l](https://www.reddit.com/r/LocalLLaMA/comments/1ww528l/), 16k context, custom tools, n=1 setup).
- **Runtime warnings (claims, after-the-round items):** llama.cpp builds from ~10-04 reportedly loop Gemma 4 31B and
  crash Qwen3.8-27B; one user rolled back to 09-24/09-28 builds ([1wzg1t1](https://www.reddit.com/r/LocalLLaMA/comments/1wzg1t1/),
  10-06). Ollama 0.40.0 pins b11351 (10-02), so this is one more reason not to upgrade `.67` now. Ollama silent
  truncation (HTTP 200, prompt cut to the window, no error) reproduced on 0.34.4 by a probe tool
  ([1wu3717](https://www.reddit.com/r/ollama/comments/1wu3717/), 09-30), the same class as our known silent-truncation bugs.
- **Blocked entries:** K2-Horizon AMA ([1wv8zww](https://www.reddit.com/r/LocalLLaMA/comments/1wv8zww/), IFM, 10-06):
  vendor confirms ~1.5 GB KV per 8k tokens (matches our ~192 KiB/token, so ~48 GiB at 256k), says 4-bit KV quant
  "only minimally" hurts, and that smaller-KV architectures are future work; users: "36B A4B currently has no use
  case, strictly because of KV". Xing4.0 ([1wimf5p](https://www.reddit.com/r/LocalLLaMA/comments/1wimf5p/), 09-17):
  one user on the vendor fork found it **worse than qwen3.6-35B-A3B** on one-shot prompts. Notes added to both rows.

## Sweep 2026-10-07 (non-HF sources): no new testable model; abliteration decided as a class

*Web-only, 2026-10-07. Covers the sources the HF/llama.cpp sweep above did not: Hacker News (Algolia API, stories since
09-15, ~20 queries), blogs/newsletters (Simon Willison `local-llms` feed, Interconnects and Latent Space RSS), HF Papers
search, Ollama library "newest" + blog, independent leaderboards (Terminal-Bench, SWE-bench, Aider polyglot, BFCL,
LiveCodeBench, pi-agent board), web search for LinkedIn/X posts. Reddit is covered separately.*

- **New models found:** one model the register had not decided fits the box: **Nex-N2.5-mini** (35B-A3B, released
  09-08, so it predates this window but never got a row). The evidence is against it (row below). Everything else in
  these sources since 09-15 is oversized or not a coder: Tinfield-1 (177B), T1 (122B, paper only), Aikido Altar (GLM-5.3
  prune, 328 GB), Reflection Beam (501B), Mistral Large 4 (1T), StepFun Step 5 (600B, weights promised 10-15). Also too
  big: Motif-3, Hy4-preview, dots3-note-prev and Inkling-Small (265–780B, all from July/August).
- **Leaderboards do not help in this size class.** SWE-bench (data last committed 09-01, newest result 2026-02), Aider
  polyglot (last updated 2025-10), BFCL (2026-03) and LiveCodeBench (2025-07) are stale. The tbench.ai pages render
  client-side, so no rows can be read. The pi-agent board (ibragim.dev, 09-30) lists only one open model under 40B,
  Qwen3.8-27B (dense, already decided).
- **Abliteration:** decided as a class below. **Do not test**, with one conditional exception.
- **Testable list: unchanged.**

### Abliterated / uncensored / "heretic" variants: class decision (2026-10-07)

**Verdict: do not test.** There is one condition under which a single variant may be screened (below).

**What we measured ourselves.** CyberTiel (huihui's crude abliteration of Ornith-1.5 plus a cyber imatrix) against Tiel:
Terminal-Bench **29.6% [16, 48] vs 40.7% [25, 59]** (BENCHMARK_HARNESS §9d). The intervals overlap, so by our own rule
this is a **tie, not a loss**. On every other axis the two are within noise. In `dualuse-probe.py`, abliteration changed
**exactly 1 of 9** grey-zone security tasks: an offline bcrypt dictionary attack (measurements.md §18). Both builds
complied on the PoC, port-scanner, fuzzer, priv-esc and CTF tasks.

**What others measured** (independent first, vendor claims marked):

| evidence | what it shows | source, date |
|---|---|---|
| Carleo et al., "Willing but Unable" (Qwen2.5-Coder 3B/7B/14B) | Abliteration takes refusal to ~0 and keeps code validity > 93%. Security-code success stays **capacity-bound** (3B: 25–48% even after abliteration). **Refusal and capability are separate**, so removing refusal adds no skill | [arXiv 2606.05396](https://arxiv.org/abs/2606.05396), 2026-06-03 |
| Young, "Comparative Analysis of LLM Abliteration Methods" (16 models, 7–14B) | GSM8K deltas from +1.5 to **−18.8 pp**. Heretic's KL varies 0.043–1.646 by model. "Not one-size-fits-all." No agentic or tool-call metric | [arXiv 2512.13655](https://arxiv.org/abs/2512.13655), 2026-01 ([summary](https://github.com/adybag14-cyber/Abliteration/blob/main/docs/comparative-abliteration-benchmarks.md)) |
| "How Fragile Is Safety Alignment at Frontier Scale?" (GLM-5.3-Flash MoE) | On an MoE, the usual module-name recipe reaches only **0.066 of 0.776** of the refusal effect, so it "fails silently on an MoE". Crude MoE abliterations (huihui's "crude, proof-of-concept" script) are therefore of unknown quality | [arXiv 2609.09793](https://arxiv.org/abs/2609.09793), 2026-09-09 |
| ProjectDiscovery, "Abliterated models can get you pwned" | Researchers fine-tuned a model with a trigger phrase that makes a coding agent exfiltrate `.env` credentials, for under $50. The model still scores 99–100% on clean evals. "Do not pull abliterated models off Hugging Face into production" on benchmark scores alone. Uncensored repos come from anonymous uploaders, which is the supply chain this attack uses | [projectdiscovery.io](https://projectdiscovery.io/research/how-abliterated-models-can-get-you-pwned), 2026-10-06 (HN 49990426) |
| Ornith-1.5-Heretic on the r/LocalLLaMA tool eval | 132.2 vs 144.2 for plain Ornith, so it **lost to its base** (already recorded in toTest.md) | owner-pasted thread, 09-2x |
| Bahushruth Qwen3.6-35B-A3B-abliterated, own version table | v1 (10-direction standard abliteration): quality "**Destroyed**". v4 (norm-preserving): "Intact", but tested only on 16 harmful prompts | [card](https://huggingface.co/Bahushruth/Qwen3.6-35B-A3B-abliterated-v4) |
| *Vendor claim:* CyberTiel card | SWE-bench-Live **13.7/25 vs 12/25** for Tiel (3-seed mean, 25 tasks, Pi harness, Q4_K_M). That is a ~1.7-task gap at n=25 and inside noise. Cybench 15/43 has no base comparison | [card](https://huggingface.co/peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF), 09-08 |
| *Vendor claims:* Heretic KL on our class | **llmfan46 Qwen3.6-35B-A3B heretic: KL 0.0015**, 83→10/100 refusals. Youssofal Qwen3.6 heretic: KL 0.0107, 22→1/25. SC117 Ornith-1.5 heretic: KL 0.0105. llmfan46 gemma-4-26B-A4B "ultra": **KL 0.1237** (high). These are first-token KL on harmless chat prompts, **not a measure of tool calls or long agentic sessions** | HF cards ([llmfan46 qwen3.6](https://huggingface.co/llmfan46/Qwen3.6-35B-A3B-uncensored-heretic-GGUF), [gemma4](https://huggingface.co/llmfan46/gemma-4-26B-A4B-it-ultra-uncensored-heretic-GGUF), [Youssofal](https://huggingface.co/Youssofal/Qwen3.6-35B-A3B-Abliterated-Heretic-GGUF), [SC117](https://huggingface.co/SC117/Ornith-1.5-35B-A3B-Heretic-MTP-APEX-GGUF)) |
| Anecdote | "huihui abliterated Qwen models have shown weaker performance on tool calls and MCP integrations" (no data) | [pocketanimus guide](https://pocketanimus.com/guides/best-abliterated-model/), undated |

**Why not, in one line:** no independent measurement shows abliteration *helping* coding or agentic scores. The best
evidence shows refusal and capability are separate, so there is nothing to gain. The measurable downside ranges from
nil (low-KL Heretic) to "destroyed" (crude MoE runs). There is real supply-chain and operational cost: anonymous
uploaders, sandbox mandatory (§6), no shell alias. Our own dual-use probe found the censored field refuses 1 task in 9.

**Exception, test only under all of these conditions:**
1. the owner has a **concrete workload the field refuses**, shown by running `dualuse-probe.py` on the *default*
   (qwen3.6 has never been probed; only the Tiel builds were);
2. the variant is of a **field model**, made with **Heretic/MPOA or norm-preserving** ablation, with a **published KL ≤ 0.02**;
3. it runs only in `cc-session-sandboxed.sh`, as a same-quant A/B arm labelled so it never pools with the main data.

Under those conditions the one candidate is **`llmfan46/Qwen3.6-35B-A3B-uncensored-heretic-GGUF`**: the default's own
weights, KL 0.0015, Q4_K_M 19.8 GiB / Q5_K_M 23.1 GiB + mmproj 0.84 GiB, the same `qwen35moe` architecture, so it
fits like the default. It dates from 04-20, so it is not new. Without condition 1 it is not pulled.

**Recheck the class** if an independent agentic benchmark (Terminal-Bench, SWE-bench-Live, BFCL multi-turn, or a tool
eval with CIs) shows an abliterated build beating its own base outside noise.

### Rows for "Known, not fitting"

| model | fits? | decision and evidence | decided |
|---|---|---|---|
| **ollama.com by popularity, 2026-10-07** (`/search` default order and `?o=newest`, first page each; pull counts as shown) (*10-07*) | — | **no undecided local contender.** Every local model in the coding/agentic size class is already decided: qwen3.6 7M pulls (the field), qwen3.8:27b 3.3M (measured v3, dense, rejected), nemotron3:33b 675K (Nano Omni, multimodal Q&A; the nemotron family failed our tool gates), ornith 585K and ornith-1.5 369K (measured, 41%, T5 5/8), muse-glimmer:30b 267K (measured, dense 19–29 tok/s), nemotron-3.5-lightning:30b 214K (measured, 13–14/18), qwen3.8-flash-next 178K (decided), granite4.2:30b 116K (measured, dense). The rest is cloud-only (deepseek-v4.1-flash, glm-5.3/-flash, glm-5.2, minimax-m3, mistral-large-4, kimi-k3) or decision/embedding models (clef, clef-flash, nimble, tev1, laya, embeddinggemma-2) | 2026-10-07 |
| **Abliterated / uncensored / heretic variants, as a class** (*10-07*) | yes, same size as their bases | **Do not test; one conditional exception.** Detail and sources are in § Abliterated, class decision. Own data: CyberTiel vs Tiel Terminal-Bench 29.6% [16, 48] vs 40.7% [25, 59] (a tie by our rule), and the dual-use probe changed 1 task in 9. Independent: abliteration removes refusal without adding capability ([arXiv 2606.05396](https://arxiv.org/abs/2606.05396)); damage varies by tool and model up to −18.8 pp GSM8K ([arXiv 2512.13655](https://arxiv.org/abs/2512.13655)); module-name recipes fail silently on MoE ([arXiv 2609.09793](https://arxiv.org/abs/2609.09793)); backdoored abliterations pass evals and steal credentials ([ProjectDiscovery, 10-06](https://projectdiscovery.io/research/how-abliterated-models-can-get-you-pwned)). **Exception:** `llmfan46/Qwen3.6-35B-A3B-uncensored-heretic-GGUF` (KL 0.0015), only if `dualuse-probe.py` shows the default refusing real work, and only sandboxed as a labelled A/B arm | 2026-10-07 |
| Huihui-/Bahushruth-/HauhauCS-/llmfan46-/Youssofal- **Qwen3.6-35B-A3B** abliterations (*10-07*) | yes, Q4_K_M ~19.8–21 GiB | covered by the class row. HauhauCS "Aggressive" (867k downloads) discloses **no method and no KL**, only "0/465 refusals". Huihui's is the self-described "crude, proof-of-concept" script. Only llmfan46 (KL 0.0015) meets the exception's KL bar | 2026-10-07 |
| **KAT-Coder-V2.5-Dev** abliterations (KridgeDookie "PHILADELPHIA CLASS", jakeroxs/mradermacher MTP-ABLITERATED, 08-07 → 09-05) (*10-07*) | yes | covered by the class row. **No KL and no benchmark** published. KridgeDookie reports only internal refusal counts (0/842) and "23/24 coherence checks", and its own card says it "does not guarantee better coding ability ... or tool use" | 2026-10-07 |
| **gemma-4-26B-A4B** heretic/abliterated (llmfan46 "ultra", huihui, mudler APEX) (*10-07*) | yes | covered by the class row. The best-documented build has **KL 0.1237**, 80× the qwen3.6 heretic, so it fails the exception's KL bar | 2026-10-07 |
| **Xing4.0-29B-A4B** abliterations (huihui 09-29, IsValorum APEX GGUFs 10-01) (*10-07*) | blocked | the base is still blocked on `xing4_0` runtime support (row above), and it is the crude huihui script. Decide the base first | 2026-10-07 |
| Qwen3.8-35B-A3B-Distill abliterations (IsValorum APEX, Lord-H4D3ZS "Coder-Abliterated") (*10-07*) | yes | an abliteration of a base already rejected 09-24 (community distill, 8k training length) | 2026-10-07 |
| fable-coder-35B-A3B (Achilles1089, 07-14) (*10-07*) | yes | an SFT on top of huihui's abliterated "Claude-4.7-Opus" Qwen3.6, with no independent numbers. Class row applies | 2026-10-07 |
| Qwen3.6-35B-A3B-Westernized (hirundo-io, 09-14) (*10-07*) | BF16 only, no GGUF | "behavioural unlearning" of **political/China-topic** censorship (CCPC-500 89.8→2.8%). It reports **no coding, tool-call or KL numbers**. Irrelevant to coding refusals ([card](https://huggingface.co/hirundo-io/Qwen3.6-35B-A3B-Westernized), HN 49984522) | 2026-10-07 |
| Qwopus3.6-35B-A3B-Coder (Jackrong, 06-21) (*10-07*) | yes (qwen3.6 MoE fine-tune) | a community LoRA/SFT ("Opus-distill") on Qwen3.6 for **thinking-off** agent loops. The only number is a third-party 300-case SWE-bench "submitted-patch" run at Q5_K_M: **62.4%**, with no base model on the same run. Below qwen3.6's own SWE-V claim, so it gives no sign of beating the field | 2026-10-07 |
| Tinfield-1 (Bad Theory Labs, 09-21) (*10-07*) | **no**: 180B total / 6.6B active, Q4_K_XL 111 GB | a Qwen3.8-Flash-Next fine-tune. Claims Terminal-Bench 4.0 33.0 vs 29.0 for its base. Its own GGUFs are 2-bit (61–72 GB) ([card](https://huggingface.co/badtheorylabs/Tinfield-1)) | 2026-10-07 |
| Aikido Altar-1 (09-21), T1 (paper 2609.11042), Reflection Beam (10-05), StepFun Step 5 (weights 10-15) (*10-07*) | **no** | 328 GB W4A16 GLM-5.3 prune / 122B / 501B-A23B / 600B-A27B | 2026-10-07 |
| Motif-3, Hy4-preview, dots3-note-prev, Inkling-Small (07–08/2026) (*10-07*) | **no** | 315B / 780B / 288B / 266B total (HF safetensors counts). Found via Interconnects #24 and HN; never in the register | 2026-10-07 |

### Sources not reachable or not usable (2026-10-07)

- **X/Twitter:** nitter.perennialte.ch 403, xcancel.com 451, nitter.net and nitter.poast.org time out, and twitter.com
  redirects to x.com, which needs a login. `site:x.com` web searches return no x.com hits.
- **LinkedIn:** `site:linkedin.com` searches return no linkedin.com posts (only re-hosted news), so there is no usable
  signal from it.
- **Ollama Discord:** needs a login, not reachable. The Ollama blog and library "newest" were reachable and show nothing
  new in the class (newest: mistral-large-4, embeddinggemma-2, decision models).
- **local-bench.ai:** HTTP 503 (Retry-After 86400). **tbench.ai** leaderboards: client-rendered, so no rows are in the
  HTML.
- **Stale leaderboards:** SWE-bench (newest result 2026-02), Aider polyglot (2025-10), BFCL (2026-03), LiveCodeBench
  (2025-07).

## Known, not fitting: decided, not pulled

| model | fits? | decision and evidence | decided |
|---|---|---|---|
| **Xing4.0-29B-A4B** (China Telecom XingChen, official, HF 2026-09-16) | yes, 17.6 GiB Q4_K_M | **blocked on runtime support, not on merit.** Its architecture `xing4_0` (mHC + MLA + MTP) is new, and its own tab says "All 5 inference framework PRs are still pending". Ollama 0.33.3's llama.cpp cannot load it. On merit it would be testable: claims SWE-V 75.0 and Terminal-Bench 2.1 57.5 against Qwen3.6-35B-A3B and gemma4, is tuned for Claude Code/OpenCode, and one user reports "on par with Qwen3.6 35B in thinking mode". **Recheck when llama.cpp merges `xing4_0` and an Ollama release bundles it.** Re-checked 09-25 13:30: llama.cpp [#29012](https://github.com/ggml-org/llama.cpp/pull/29012) and cleanup [#29141](https://github.com/ggml-org/llama.cpp/pull/29141) are both still open, so **not deployable today**. Re-checked 10-05: #29012 still open, #29141 closed unmerged; no Ollama release (latest 0.35.1) loads `xing4_0`. **Re-checked 10-07: still blocked.** #29012 open, last activity 10-04 (a reviewer asked for a rebase; the bot flags it as a large multi-backend PR awaiting code-owner review); Ollama 0.40.0 does not load it. **Reddit 10-07:** the only hands-on report on the vendor llama.cpp fork found it *worse* than qwen3.6-35B-A3B on one-shot prompts ([1wimf5p](https://www.reddit.com/r/LocalLLaMA/comments/1wimf5p/), 09-17), against the "on par" report above | 2026-09-25 |
| K2-Horizon-MoVA-36B-A4B (IFM/MBZUAI) | Q4 20.8 GiB | **blocked on runtime**: its card says upstream llama.cpp cannot load the MoVA architecture and needs the IFM fork. Claims Terminal-Bench 2.1 58.6. Recheck when upstream support lands. Re-checked 09-25 13:30: [llama.cpp#28361](https://github.com/ggml-org/llama.cpp/issues/28361) "K2-Horizon models fail to load" is open, so **not deployable today**. Re-checked 10-05: an upstream PR now exists, [llama.cpp#29535](https://github.com/ggml-org/llama.cpp/pull/29535) "add K2 Horizon dense and MoVA support", open (updated 10-04). **Recheck when it merges and an Ollama release bundles it**; it is the most promising blocked entry (claims Terminal-Bench 2.1 58.6). **Re-checked 10-07: upstream unblocked, Ollama not yet, and a new fit problem.** #29535 **merged 2026-10-06** (first build b11454), #28361 closed. Ollama 0.40.0 (tagged 10-06) pins llama.cpp b11351, which predates the merge; Ollama's maintainer says support comes "when ollama syncs to b11454+ ... perhaps 0.40.1" and showed `hf.co/IFM/K2-Horizon-3.7B-GGUF` running on a b11454 build ([ollama#18698](https://github.com/ollama/ollama/issues/18698)), so the official IFM GGUFs should load unchanged. **But the 256k rung does not fit**: every one of its 48 layers is full attention (upstream `k2-horizon.cpp` uses a plain KV input, no SWA; config: 8 KV heads × 128), so f16 KV costs ~192 KiB/token = **~48 GiB at 256k**, ~24 GiB at 128k, ~12 GiB at 64k. With Q4_K_M (20.8 GiB) only **~64k** fits beside the weights at f16 KV; 128k needs `OLLAMA_KV_CACHE_TYPE=q8_0` (a server change, the owner's call). The vendor confirms the attention layout "would take quite a bit memory for long generation" (HF #7). Independent: one YouTube test reports weak recall past 131k and failed coding tasks, below Qwen3.8-27B (HF #9, vendor agrees it trails Qwen3.8-27B on Artificial Analysis). **Next step when Ollama ≥ b11454 ships: a 64k-rung screen only if the owner accepts a non-256k model**; estimates to be confirmed by `kv-probe.sh`. **Reddit 10-07:** the IFM AMA confirms ~1.5 GB KV per 8k tokens and full attention by design; 4-bit KV quant is their suggested workaround (not available in Ollama, whose KV options are f16/q8_0/q4_0 server-wide); smaller-KV architectures are future work ([1wv8zww](https://www.reddit.com/r/LocalLLaMA/comments/1wv8zww/)) | 2026-10-05 |
| **Kolibri-1** (Aleph Alpha, 2026-10-02/03, Apache-2.0), asked 2026-10-05 | **no**: Q4_K_M/Q4_K_XL = **44.2 GiB** of weights alone, > 35.5 GB usable (and > the 40.4 GB total). Only Q3_K_XL (34.9 GiB) fits, which breaks the 4-bit floor and leaves no room for KV | 78B MoE, 3.46B active, 384 experts / 6 active, 50 layers, 262k context, architecture `kolibri1`. **Also blocked on runtime**: no upstream llama.cpp PR; the community GGUFs "require the experimental Kolibri patch for llama.cpp"; Ollama has only an MLX PR (ollama#18780, Apple only) and no library entry, so Ollama 0.35.1 on `.67` cannot load it. Early hands-on reports (two practitioners, 10-05) say it trails Qwen on tool calls and coding and thinks long; vendor benchmarks are against Qwen3.8-27B. A German-language document model, not a coding agent. **Re-checked 10-07: unchanged.** Upstream has only a feature request ([llama.cpp#29922](https://github.com/ggml-org/llama.cpp/issues/29922), open, no PR; the runtime patch lives in a community GGUF repo); ollama#18780 (MLX) still open. Does not fit at ≥4-bit regardless | 2026-10-05 |
| **Delta sweep 2026-10-05 → 10-07** (*10-07*) | — | **nothing new worth testing.** Details in § Sweep 2026-10-07 and the rows below. The rest is Qwen3.8-27B fine-tunes/abliterations (dense), gemma4-26B-A4B and Xing4.0 abliterations, small MoEs (Lythri 4B-A2B/7B-A4B, ETET-1.0 1.8B-A1B), decision models (Intern-Decision, pplx-decider) and re-quants of measured models (`Accio-Lab/occamy-1.0-APEX-GGUF`, 10-02: mixed-precision repack of occamy, already measured) | 2026-10-07 |
| **MiniCPM-V-4.7-35B-A3B** (OpenBMB) (*R 10-07*) | probably, ~35B-A3B | **blocked: not public.** The HF repo appeared and went private within hours on 10-07 (API 401; "No model card yet", [1wzpyzk](https://www.reddit.com/r/LocalLLaMA/comments/1wzpyzk/)). Multimodal MoE on the **Qwen3.5**-MoE base (older than qwen3.6) with SigLIP vision and 3D M-RoPE; llama.cpp [#29416](https://github.com/ggml-org/llama.cpp/pull/29416) "Support MiniCPM-V 4.7" open since 09-25. No coding/agentic numbers known. **Recheck when the weights and a card with SWE/Terminal-Bench numbers are public, #29416 is merged, and an Ollama release bundles it** | 2026-10-07 |
| Nex-N2.5-mini (nex-agi, 09-08, 35B) (*R 10-07*) | yes | qwen3.6-class 35B fine-tune. Independent Aider Polyglot: **30.8% vs 71.0% for base** qwen3.6, "a disaster" ([1wss436](https://www.reddit.com/r/LocalLLaMA/comments/1wss436/)); a second user: "worse than base across t[asks]". Not tested *10-07, non-HF sweep:* bartowski Q4_K_M 20.8 GiB / Q5_K_M 25.1 GiB (+ mmproj 0.84 GiB); its card claims Terminal-Bench 2.1 73.4 (implausible at 3B active); three HF-tab reports of looping/over-exploring in agent harnesses. | 2026-10-07 |
| Nail-Qwen3.6-35B-A3B (peculiar-ragdoll, Tiel's author) (*R 10-07*) | yes, Q4_K_XL 22.9 GB | recommended on Reddit next to Tiel ([1wqqv3b](https://www.reddit.com/r/LocalLLaMA/comments/1wqqv3b/), 09-26), but its card says it is **Unsloth's qwen3.6 GGUF plus a chat template and a baked-in system prompt, not fine-tuned**. Same weights as the default; a template change is cosmetic | 2026-10-07 |
| Scion-35B-A3B (SkyIsNotGreen, 09-27) (*R 10-07*) | only below 4-bit | **ternary 2-bit** (`pq2_0`) quant of `empero-ai/Qwen3.8-35B-A3B-Distill`, already rejected 09-24 ([1wydetp](https://www.reddit.com/r/LocalLLaMA/comments/1wydetp/)). Breaks the 4-bit floor twice over | 2026-10-07 |
| AREX-2 (BAAI, 09-29), Swift-Qwen3.8-27B 1.0/1.5, Jeff-Code, VeriLoop E2 (*R 10-07*) | yes, **dense 27B** | Qwen3.8-27B-class dense models and fine-tunes that dominate Reddit's 24–32 GB coding threads (e.g. Swift-1.5 27B "most robust" on one harness leaderboard, [1wy5bmy](https://www.reddit.com/r/LocalLLaMA/comments/1wy5bmy/)). Dense rule: qwen3.8:27b measured 4× the field here. AREX-2 targets research/ML engineering, no SWE/Terminal-Bench on its card | 2026-10-07 |
| Agens-Volundr-32B-Preview (Blockway, 10-03, Apache-2.0) (*10-07*) | no runtime | 32B **custom architecture** `volundr` (KDA linear attention + compressed-sparse attention + Engram + mHC, 72 layers). No llama.cpp PR; serving needs Blockway's own sglang build. A GGUF repo appeared 10-05 (5 likes) that no upstream llama.cpp can load. Its own card: SWE-bench Verified-50 **44.0 vs 58.0 for Qwen3.8-27B**, and "long agentic sessions are the weak spot ... repetition loops" ([card](https://huggingface.co/Blockway/Agens-Volundr-32B-Preview)). Recheck only if a v1 with an upstream runtime appears | 2026-10-07 |
| Victoria (rmonsurate, 09-21/09-30) (*10-07*) | **no**: GGUF Q4_K_M 49.2 GiB resident | 288-expert prune of Qwen3.8-Flash-Next, retrained at 4-bit. Claims Terminal-Bench 2.1 70.0% avg@3 (single-author numbers). Too big, and its GGUF needs a patched llama.cpp (`wrong number of tensors` on mainline) ([card](https://huggingface.co/rmonsurate/Victoria)) | 2026-10-07 |
| Naive-N0.5-Flash (NaiveAI, 09-27) (*10-07*) | **no** | 309B MoE / 15.5B active, custom `naive_n05_flash` architecture on MiMo-V2.5 ([card](https://huggingface.co/NaiveAI/Naive-N0.5-Flash)) | 2026-10-07 |
| MiMo-V2.6-Flash-RL / -MOPD, Pro-RL / -MOPD (Xiaomi, 09-21/09-27) (*10-07*) | **no** | 311B total (HF safetensors count). The 9B distill (MiMo-V2.6-Distill-Qwen-9B) is already decided 09-25 | 2026-10-07 |
| Ling 3.1 Flash (inclusionAI, 10-02), Ling-3.0-flash (08-02) (*10-07*) | **no** | the Flash line is ~127B total (Ling-3.0-flash safetensors count). Ling-3.0-tiny (7.9B) is a third of the field's size class. Listed by the [Kilo catalogue](https://kilo.ai/new-open-weight-models) | 2026-10-07 |
| GLM-5.3 Flash / FlashX / Prime, Mistral Large 4, Qwen 3.8 Max Prime (09-10 → 10-06) (*10-07*) | **no** | GLM-5.3-Flash is 321B (`glm5_next`); the others are paid/cloud-class. Mistral Large 4 is on ollama.com as cloud only | 2026-10-07 |
| Ornith-1.5-35B-A3B-DFlash (ornith-ai, 09-20) (*10-07*) | — | a speculative-decoding **drafter** for Ornith-1.5, not a model. Ornith-1.5 itself was measured (41%, 119 s sessions, T5 failed) | 2026-10-07 |
| Maion-Coder (*10-07*) | ? | only an open llama.cpp architecture PR ([#29778](https://github.com/ggml-org/llama.cpp/pull/29778), 10-01: MoE + SWA, "maion-coder"); **no weights found** on HF under that name. Recheck if a model card appears | 2026-10-07 |
| **Delta sweep 2026-09-25 → 10-05** (HF API by trend and by date, A3B GGUFs, "coder" models; Ollama releases) | — | **nothing new worth testing.** No new first-party coder MoE in the 35.5 GB class. Detail in the rows below; the rest are abliterations, sub-4-bit quants (DASHQ-Q2, IQ2, Q3), translation (Index-Translate-35B-A3B), Japanese (ELYZA-Thinking-1.0-32B-A3B) and repacks of qwen3.6/Ornith-1.5 | 2026-10-05 |
| Holo4-35B-A3B (H Company, 09-24) | yes, qwen3.6 MoE fine-tune | a **computer-use VLM** (screenshots → GUI actions), not a coding agent. Card reports OSWorld 2.0 30.9% and AutomationBench 34.5%, **no SWE-bench or Terminal-Bench**. Holo4-27B is the dense sibling (dense rule) | 2026-10-05 |
| Holotron4-30B-A3B (H Company, 09-24) | yes, Nemotron-H Omni | computer-use VLM on Nemotron 3 Nano Omni (the nemotron family failed our tool gates). Its own table: ALE (Linux, code) 0.6, OSWorld 2.0 0.2. NVIDIA licence | 2026-10-05 |
| Humo-Coder-35B-A3B (ooptimum, 10-01) | yes | **Tiel-Coder again**: Ornith-1.5 weights + the Sharp chat template, "nothing was trained" (its card). Tiel is in the field already | 2026-10-05 |
| Whittle-Qwen-3.8-45B/35B-A3B (logic65, 10-04) | 45B no (27.1 GB Q4 + 5.6 GB memory table in CPU RAM); 35B yes | one-person **untrained splice/prune** of Qwen3.8-Flash-Next and qwen3.6. Its own card: "Experimental", invented tool calls on a real chat replay, base qwen3.6 better (20/20 vs 16/18). Same class as the prunes ruled out 09-24 | 2026-10-05 |
| Clef / Clef-Flash (Cloudflare, 10-01), Nimble, Tev1 | — | **decision models** (`/v1/systemone`, probabilities, no text generation). Not a coding agent | 2026-10-05 |
| Qwen3.8-Flash-Next GSQ-RCO-Coder (ISTA-DASLab, 09-26) | only below 4-bit | the 125B-A6B fits 35.5 GB only at ~2-bit GSQ, which breaks the 4-bit floor | 2026-10-05 |
| Agnes-3.0-Flash (09-11) | yes, dense | 33B **dense** (72 layers, custom `agnes` architecture). Dense has been 4× too slow here, and llama.cpp support is unclear | 2026-09-25 |
| Mellum2-12B-A2.5B (JetBrains, 2026-06) | yes, small | MoE 12B total / 2.5B active: **a third of the field's size class**. It is JetBrains' IDE **code-completion** line, not an agentic tool-use model, and has no agentic benchmarks. Found in the 09-25 delta sweep | 2026-09-25 |
| Delta sweep 2026-09-18 → 09-25 | — | **nothing new worth testing.** MiMo-V2.6-Distill-Qwen-9B is dense 9B with a non-standard tool parser, Confucius4-R2T2 is speech recognition, and the rest is repacks of known bases | 2026-09-25 |
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
