# Muse Glimmer on the 40 GB server (`192.168.100.67`)

Written 2026-08-11. Continues the work in `../ollamaClaudeCode_v1/` (measurement
harness, `review2.md`, `fitting_models.md`) and `../ollamaClaudeCode_v0/`
(`OLLAMA_PULL.md`, `LOCAL_OLLAMA_BACKEND.md`).

> **Status: the install is blocked, and not by anything on our side.**
> `muse-glimmer` declares `"requires": "0.32.8"` in its registry config.
> `.67` runs Ollama **0.32.5**. The pull is refused by the registry with HTTP 412
> before a single byte of weights is transferred. Everything downstream of the
> upgrade is prepared below and is copy-paste runnable the moment `.67` is on
> 0.32.8.

---

## 1. What was done, and where it stopped

Host discovery first, using the project in `~/repos/ollamaFarm/`. Its default host
list is `192.168.100.37 192.168.100.67`; a full `/24` sweep of `/api/version`
confirms that list is still complete — `.13` and `.99`, which appear in the
ollamaFarm README, are not currently on the network.

| host | Ollama | VRAM | note |
|---|---|---|---|
| `192.168.100.37` | 0.30.6 | 12.3 GB | too small for a 28B anyway |
| **`192.168.100.67`** | **0.32.5** | **40.4 GB total / 36.1 GB measured usable** | the target |

The pull, against `.67`:

```console
$ curl -s -X POST http://192.168.100.67:11434/api/pull -d '{"model":"muse-glimmer:30b"}'
{"status":"pulling manifest"}
{"error":"pull model manifest: 412: \nThe model you are attempting to pull requires
a newer version of Ollama.\n\nPlease download the latest version at:\n\n\thttps://ollama.com/download\n"}
```

This is not a guess about which version is needed. The registry config blob says so
outright:

```console
$ curl -sL https://registry.ollama.ai/v2/library/muse-glimmer/blobs/sha256:57b82200bf7c…
{"model_format":"gguf","model_family":"muse-glimmer","model_families":["muse-glimmer"],
 "model_type":"27.9B","file_type":"Q4_K_M","renderer":"glimmer","parser":"glimmer",
 "requires":"0.32.8","architecture":"amd64","os":"linux"}
```

And it matches the upstream release history:

| release | date | relevance |
|---|---|---|
| v0.32.5 | 2026-07-27 | **what `.67` runs** |
| v0.32.7 | 2026-08-10 | Muse Glimmer, **Apple Silicon / MLX only** |
| **v0.32.8** | **2026-08-10** | *"Add Muse Glimmer support for NVIDIA, AMD, and additional platforms"* |

`.67` is an NVIDIA box, so 0.32.7 would not have been enough either. **0.32.8 is the
floor.**

I cannot perform the upgrade myself: `ssh 192.168.100.67` returns
`Permission denied (publickey,password)`, and `ollamaFarm`'s `AGENTS.md` records
`.67` as a shared machine whose host-level access "never arrived". The upgrade is a
one-line action for whoever administers the box (§6).

### 1b. "But putting models on that server always worked before" — it did, and it still does

Nothing about our access has regressed. Models have always been installed on both
servers purely over HTTP, without SSH, by two mechanisms that both still work today:

| how | endpoint | used for |
|---|---|---|
| **pull** — the *server* downloads from the registry; the bytes never touch our machine | `POST /api/pull`, or `OLLAMA_HOST=… ollama pull` | every base tag: `qwen3.6:35b-a3b-q4_K_M`, `qwen3.6:27b-q8_0`, `qwen3.5:9b` |
| **create** — build a new tag on the server from one already there; no download, no registry | `POST /api/create`, or `ollama create` | every tuned variant: `-ctx128k`, `-ctx256k`, `-agentic`, `-isot0`, `-isopp0` |

The seventeen tags currently on `.67` are the receipts — `qwen3.6:35b-a3b-q4_K_M-agentic`
and friends were all built through `/api/create` against that box, over the network,
from this machine. That path is untouched and still open.

**What is different is one field in one model's metadata.** The `requires` gate is
per-model, and until now no model we wanted had ever asked for more than `.67`
provides:

| model | `requires` | satisfied by `.67`'s 0.32.5? |
|---|---|---|
| `qwen3.6:35b-a3b-q4_K_M` | *(none)* | yes |
| `qwen3.6:27b-q8_0` | *(none)* | yes |
| `qwen3.5:9b` | `0.17.1` | yes |
| **`muse-glimmer:30b`** | **`0.32.8`** | **no** |

So this is not a permissions problem, a network problem, or a procedure we have
forgotten. It is a model released *the day before yesterday* that demands a runtime
released *yesterday*, on a server last updated on 2026-07-27.

### 1c. Why sideloading around the gate does not help

Worth stating, because it looks like an obvious escape hatch and it is a dead end.

The registry gate is only a version handshake, and it is trivially bypassable: the
manifest, the config blob, the params blob and the GGUF header were all fetched from
`registry.ollama.ai` while writing this document — every hard number in §2 came from
those bytes. The registry refused `.67` because `.67` announced `0.32.5`, not because
of who we are. Ollama even exposes `POST /api/blobs/sha256:<digest>`, so the weights
could be uploaded to `.67` over HTTP and assembled with `/api/create`, no SSH needed.

That would defeat the gate and still leave us with nothing — and this is now
demonstrated rather than argued. Comparing the old `0.32.6` install still on this
laptop against the `0.32.8` tree, by symbol:

| component | 0.32.6 | 0.32.8 | what it is |
|---|---|---|---|
| `libllama.so` — `muse-glimmer` | **0** | **2** (`muse-glimmer.cpp`) | the architecture: graph construction |
| `libllama.so` — `kv_cache_iswa` | 59 | 59 | generic hybrid-cache machinery — **already there** |
| `libmtmd.so` — `muse-glimmer` | **0** | **1** | the vision projector path |
| `ollama` binary — `glimmer` | **0** | **137** | the renderer and the tool/thinking parser |

Three separate layers had no code for this model, and the reason it is *three* is
instructive. The generic parts were already reusable: `kv_cache_iswa` is unchanged at
59 occurrences, and `final_logit_softcapping` / `sliding_window_pattern` are present
in both — Gemma already needed those. What had to be written was the
architecture-specific glue.

The third row is the one that closes the sideloading question. Those 137 symbols are
Go code — `model/parsers/glimmer.go` implementing a stateful streaming
`GlimmerParser` (`consumeHeader`, `consumeBody`, `parseGlimmerATEM`,
`glimmerTrimStrayMessageTag`, `HasToolSupport`, `HasThinkingSupport`) and
`model/renderers.glimmerCompositeValue` for the outbound prompt. **None of that lives
in the GGUF.** It is selected by the `"renderer":"glimmer","parser":"glimmer"` fields
in the registry config blob, and it is compiled in.

So the failure modes without an upgrade are layered, and only the first is loud:

1. **No `muse-glimmer.cpp`** → the graph cannot be built. The model does not load at
   all. This alone makes sideloading pointless.
2. **No glimmer renderer** → tools and messages are never formatted into the protocol
   the model was trained on, so it does not know what tools exist.
3. **No `GlimmerParser`** → even if it generated correctly, Ollama could not tell
   thinking from answer from tool call. Muse Glimmer does not emit JSON tool calls;
   it uses a channel/recipient protocol with header and body sections and an "ATEM
   invoke" wrapper. Unparsed, that surfaces as raw markup in the text and **zero
   `tool_use` blocks** — precisely the `qwen2.5-coder` failure documented in
   `../ollamaClaudeCode_v0/LOCAL_OLLAMA_BACKEND.md`.

**The upgrade is genuinely required. There is no clever way around it**, and the
`requires` field is an honest description of that, not a policy.

---

## 2. What Muse Glimmer actually is

Read out of the GGUF metadata header and the registry manifest — not from the
marketing page. These are exact.

| property | value | source |
|---|---|---|
| architecture | `muse-glimmer` (**dense**, no MoE expert tensors) | GGUF `general.architecture` |
| parameters | 27.9B text + 1.8B perception encoder ≈ 30B | config blob / model card |
| default quant | Q4_K_M | config blob |
| weights on disk | **16.757 GB** text model + **1.400 GB** vision projector | manifest layers |
| layers | **52** | `block_count` |
| native context | **131072**, extensible to 262144 | `context_length` / Unsloth |
| embedding dim | 6656 | `embedding_length` |
| attention heads | 32 query / **2 KV** (aggressive GQA) | `head_count` / `head_count_kv` |
| head dim | 128 (K and V) | `key_length` / `value_length` |
| **attention pattern** | **hybrid: 39 sliding-window (2048) + 13 full-attention layers, `SSSF` repeating ×13** | `sliding_window_pattern` |
| RoPE base | 500000 | `rope.freq_base` |
| vendor default sampling | `temperature 1`, `top_k 64`, `top_p 0.95` | params blob |
| license | Apache 2.0 | model card |
| capabilities | tool calling, vision, thinking with **`low` / `medium` / `high` / `xhigh` reasoning effort** | model card / release notes |

Two things here are unusual and both matter for us:

**It is dense, not MoE.** The whole 16.76 GB gets streamed per generated token.
That is the exact profile `fitting_models.md` identified as the *wrong* one for this
hardware — it is why `qwen3.6:27b-q8_0` managed only 18.1 tok/s while a 3B-active
MoE hit 131.5 tok/s. See §5 for what that costs.

**The 3:1 sliding-window pattern makes its KV cache almost free.** Only 13 of 52
layers keep a full-length cache; the other 39 are capped at a 2048-token window.
Combined with just 2 KV heads, this is the cheapest KV cache we have measured
against on this hardware, by a wide margin.

---

## 2b. Which quantization — **not** q8_0

The Ollama library ships fifteen tags. The ones that could plausibly land on an
NVIDIA box with 36.1 GB usable:

| tag | size | verdict on `.67` |
|---|---|---|
| **`30b-q4_K_M`** (= `:30b` = `:latest`) | **18 GB** | **recommended** |
| `30b-q4_K_M-dflash` | 20 GB | **worth benchmarking** — see below |
| `30b-nvfp4` | 19 GB | needs Blackwell; `.67`'s GPUs are unknown to us |
| `30b-nvfp4-dflash` | 21 GB | same caveat |
| `30b-q8_0` | 31 GB | **no — see below** |
| `30b-q8_0-dflash` | 33 GB | no, worse |
| `30b-mxfp8` / `-dflash` | 33 / 35 GB | no, same problem as q8_0 |
| `30b-bf16` / `-dflash` | 57 / 59 GB | does not fit |
| `30b-mlx*` | — | Apple Silicon only, useless here |

**q8_0 is the wrong pick — but for one reason, not the three I first wrote.**

> **Corrected 2026-08-11, by the measurement in §3.** My first argument here was that
> q8_0 might not fit: 31 GB plus a KV cache that could be either 1.85 GB or 6.98 GB,
> and the 6.98 GB case would have blown past the 36.1 GB ceiling. The measurement
> settled it in q8_0's favour — Ollama honours the sliding window, KV is 1.85 GB, and
> **q8_0 would fit in about 33.2 GB with roughly 3 GB to spare.** The spill argument
> is dead and I have removed it rather than quietly reworded it. The recommendation
> does not change, because the reason that actually decides it was never the fit:

1. ~~It lands on the spill cliff.~~ **Withdrawn — it fits.** See above.
2. **It is the profile `fitting_models.md` called "the worst possible pick for this
   hardware" — dense *and* q8.** Token generation here is memory-bandwidth-bound, so
   a dense q8 streams its full text-weight footprint every token — ~29.6 GB, once
   the 1.4 GB vision projector is excluded, since that is only touched on image
   input. The measured precedent on this exact machine is `qwen3.6:27b-q8_0` at
   29.97 GB → **18.1 tok/s**. Muse Glimmer q8_0 is within a rounding error of that
   footprint, so expect **~14–18 tok/s** (estimate, same bandwidth derivation as
   §5). That is *no faster than the model we already threw off this box*, and
   roughly half of what the same weights give at Q4_K_M.
3. **31 GB must split across two GPUs**, paying the interconnect cost `review.md`
   documents, where 18 GB does not.

So the case rests on throughput, and it is enough on its own: **roughly half the
tokens per second, for the Q4_K_M → Q8_0 quality delta on a 28B dense model, which is
small** — Ollama's Q4_K_M is a k-quant, not a naive round. On a box whose whole point
is agentic runs that generate a lot of tokens, that is a bad trade even though the
weights fit.

**Go with `muse-glimmer:30b` (Q4_K_M, 18 GB).** If quality later proves to be the
binding constraint, the honest next step is Unsloth's `UD-Q6_K_XL` (20–22 GB, still
comfortably inside budget) — not q8_0.

**`dflash` deserves a benchmark.** The `-dflash` tags cost ~2 GB over their base and
were introduced alongside a throughput claim. `q4_K_M-dflash` at 20 GB fits with the
same generous headroom as the base tag, so the comparison is cheap to run and is the
one variable here with real upside. Add it to the §6 step-5 benchmark.

---

## 3. VRAM budget on `.67`

Per token, per full-attention layer, at f16:

```
2 (K and V) × 2 KV heads × 128 head_dim × 2 bytes = 1024 bytes
```

At the full native `num_ctx = 131072`:

| | bytes | GB |
|---|---|---|
| 13 full-attention layers × 1024 × 131072 | 1,744,830,464 | **1.75** |
| 39 sliding-window layers × 1024 × 2048 | 81,788,928 | **0.08** |
| **KV total, if Ollama honours the sliding window** | | **1.83** |
| KV total, if Ollama allocates full-length for all 52 layers | 6,979,321,856 | **6.98** |

### Resolved by measurement, 2026-08-11 — Ollama honours the sliding window

This was the open question the whole budget hung on, and it is now settled. Loading
the model at `num_ctx=32768` makes the runtime print its own allocation:

```
llama_kv_cache_iswa: creating non-SWA KV cache, size = 32768 cells
llama_kv_cache: size = 416.00 MiB ( 32768 cells, 13 layers, 1/1 seqs), K (f16): 208.00 MiB, V (f16): 208.00 MiB
llama_kv_cache_iswa: creating     SWA KV cache, size =  2560 cells
llama_kv_cache: size =  97.50 MiB (  2560 cells, 39 layers, 1/1 seqs), K (f16):  48.75 MiB, V (f16):  48.75 MiB
```

Two caches, split exactly 13 / 39 as the GGUF pattern predicted. And the rate checks
out to the byte: 416 MiB ÷ 32768 cells ÷ 13 layers = **1024 bytes per token per
layer**, the figure derived above. The SWA cache is allocated at 2560 cells rather
than 2048 — a batch-padded window — which is the only correction the measurement
makes to the estimate.

So the real numbers at the full `num_ctx = 131072`:

| | measured basis | GB |
|---|---|---|
| 13 full-attention layers × 1024 × 131072 | confirmed 1024 B/tok/layer | **1.745** |
| 39 sliding-window layers × 1024 × 2560 | confirmed 2560-cell window | **0.102** |
| **KV total at 131072** | | **1.85** |
| text weights | | 16.76 |
| compute buffers / overhead | measured 17.58 total at ctx32768 | ~0.30 |
| **text-only total at full 128K context** | | **≈ 18.9 GB** |
| vision projector, when an image is sent | | +1.40 |
| **total with vision** | | **≈ 20.3 GB** |

Against 36.1 GB usable on `.67`, that is **16–17 GB of headroom at the full native
context**. No spill anywhere near it — and `review2.md` measured a 12.5% spill costing
**5.3× throughput**, so headroom is worth more than any sampling tweak.

A second measured finding, free from the same load: `/api/ps` reported 17.58 GB total
with the 0.54 GB of KV subtracted leaving ~17.04 GB, against a 16.76 GB text model.
**The 1.4 GB vision projector is not resident for text-only requests** — it is paged
in when an image arrives. Text-only agentic work does not pay for the vision
capability.

---

## 4. Best context window: `131072`, and it must be baked in

**Use the full native 131072. Do not tune it down — there is nothing to buy with the
saved GB, and nothing above it to reach for.**

The non-obvious half is that setting it at request time does not work for our use
case, and failing to bake it in fails *silently*. From `../ollamaClaudeCode_v1/ctx-cliff.sh`,
measured on this same server:

> A model whose Modelfile leaves `num_ctx` unset inherits the server default, and the
> Anthropic-compatible `/v1/messages` endpoint has no `num_ctx` knob. The cap is
> **16384 tokens**. Past it the tail of the prompt — which is where the instruction
> lives — is cut off, and the model **stops emitting `tool_use` blocks entirely. No
> error is returned.**

A model advertising 128K, that fits 131072 in VRAM comfortably, still hands Claude
Code a silent 16K window unless `num_ctx` is baked into a Modelfile variant. This is
the single most expensive trap in this whole line of work — it faked a capability
regression once already. So the deployable artifact is a variant, never the bare tag:

```shell
curl -X POST http://192.168.100.67:11434/api/create \
  -H "Content-Type: application/json" \
  -d '{"model":"muse-glimmer:30b-ctx128k-agentic",
       "from":"muse-glimmer:30b",
       "parameters":{"num_ctx":131072,"temperature":0,"presence_penalty":0},
       "stream":false}'
```

### Why `temperature 0` overrides the vendor default of `1`

The params blob ships `temperature 1`. For agentic software work that is a
reliability tax, and this is measured rather than assumed — `review2.md` found
`temperature 0` fixed run-to-run gate flapping, and separately that a vendor-default
`presence_penalty 1.5` cost **35–53% of throughput** on this hardware. Muse Glimmer's
params blob carries no `presence_penalty`, so pinning it to 0 is belt-and-braces, but
it is free and the failure it prevents is expensive to diagnose.

Keep `top_k 64` / `top_p 0.95` as shipped; at `temperature 0` they are inert.

---

## 5. Is it worth using for tool calls, agentic runs, and software development?

Honest answer, given the incumbent: **yes, but as a second model for a specific job —
not as a replacement for the throughput champion.**

The incumbent on `.67` is `qwen3.6:35b-a3b-q4_K_M-agentic`, **measured 131.5 tok/s**,
full 262144 context resident at 33.08 GB, all ten agentic gates passing.

Muse Glimmer's throughput has **not been measured** — the model will not load. But its
profile is bounded well enough to plan with. Extrapolating from the two dense
reference points measured on this exact box (`qwen3.6:27b-q8_0`, 29.97 GB → 18.1 tok/s
⇒ ~542 GB/s effective; `llama3.1:8b`, ~4.9 GB → 86.9 tok/s ⇒ ~426 GB/s), a dense
16.76 GB streamed per token lands at:

> **~25–32 tok/s — an estimate, not a measurement. Roughly 4–5× slower than the
> qwen3.6 MoE currently deployed.**

That is the cost. Against it:

| in its favour | against |
|---|---|
| Purpose-built for agent workloads — tool calling, multi-step reasoning, **failure recovery** | 4–5× slower than the deployed MoE, and dense so that gap will not close |
| **Vision.** Nothing else on the farm reads a screenshot, a diagram, or a failing UI | The 1.4 GB projector is resident even for pure-text runs |
| **Reasoning effort dial** (`low`/`medium`/`high`/`xhigh`) — trade latency for depth per task | New `glimmer` renderer/parser; tool-call reliability through `/v1/messages` is unproven here |
| Sliding-window attention should degrade *gracefully* at 128K, where full-attention models slow down | 128K native vs the MoE's 262144 |
| First-class Claude Code path upstream: `ollama launch claude --model muse-glimmer` | Two days old; expect rough edges |
| Apache 2.0 | |

### Published benchmarks — third-party, not ours

From Unsloth's model page. **These are published figures, not measurements we made**,
and the comparison column is `qwen3.6-27B` while the model actually deployed on `.67`
is the `35b-a3b` MoE — a sibling, not the same weights. Directionally useful, no more.

| benchmark | Muse Glimmer-30B (high) | Qwen3.6-27B (thinking) | who wins |
|---|---|---|---|
| **Agentic coding** | | | |
| SWE-Bench Verified | 76.0 | **77.2** | qwen, narrowly |
| SWE-Bench Pro | **51.2** | 50.2 | muse, narrowly |
| TerminalBench 2.1 | 51.7 | **60.7** | **qwen, clearly** |
| SciCode | **43.6** | 39.8 | muse |
| **General agentic** | | | |
| MCP Atlas | **75.5** | 62.5 | **muse, clearly** |
| WildClawBench | **47.6** | 43.2 | muse |
| Gaia2 | **43.3** | 40.0 | muse |
| OSWorld-Verified | 65.9 | **75.6** | **qwen, clearly** |
| SkillsBench | 44.3 | **46.6** | qwen |
| GDPVal-AA v2 | 953 | **1141** | qwen |
| **Multimodal** | | | |
| MMMU Pro / ScreenSpot Pro / OmniDocBench | 74 / 75.4 / 75.8 | 75 / 76.1 / 77.8 | roughly tied |

The pattern: **Muse Glimmer leads on tool-use and protocol-driven agentic work
(MCP Atlas +13), Qwen3.6 leads on terminal-driven coding (TerminalBench −9) and
desktop control.** On the SWE-Bench pair they are within noise of each other.

For our question — *is this a better Claude Code driver for building software?* —
those two headline numbers point in opposite directions, which is precisely why the
local gates in §6 decide it and this table does not.

### The number that should temper all of the above

`../ollamaClaudeCode_v1` ran SWE-bench Lite through Claude Code against
`qwen3.6:35b-a3b-q4_K_M-agentic` on this hardware and measured **24/300 resolved —
8.0%**. The published SWE-Bench Verified score for the same family is **77.2**.

That is roughly an order of magnitude, and it is not a contradiction — it is what the
harness costs. Published agentic scores come from vendor-tuned scaffolds; ours come
from Claude Code driving a local model over Ollama's Anthropic-compatible endpoint,
where a silent 16K context cap, a `max_tokens` budget that swallows the tool call, and
a mis-built prompt each cost whole percentage points. The last one is literally the
most recent commit in this repo: *"fix: prompt showed test files, never the source
files to edit."*

**So read the 76.0 above as evidence Muse Glimmer belongs in the running, not as a
prediction of what it will resolve here.** The only number that will answer the
user's actual question is a SWE-bench Lite run through the same harness — which is
step 8 of §6, and which cannot start until the server is upgraded.

**Recommended split, once measured:** keep `qwen3.6:35b-a3b-q4_K_M-agentic` as the
default driver for bulk agentic coding — 131.5 tok/s is not a number you give up
lightly on a long SWE-bench-style run. Reach for `muse-glimmer:30b-ctx128k-agentic`
for the two things it can do that the MoE cannot: **anything with an image in the
loop**, and **hard multi-step tasks where `xhigh` reasoning and failure recovery beat
raw token rate**.

Both fit on `.67` simultaneously in principle (20–25 GB + 33 GB > 36.1 GB — they do
*not*, in fact, co-reside). Expect an eviction and a reload penalty when switching;
`ollamaFarm` will show it.

---

## 6. Install procedure — ready to run after the upgrade

### Step 0 — upgrade `.67` to ≥ 0.32.8 *(requires host access; blocked for me)*

```shell
# on 192.168.100.67
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl restart ollama
ollama --version          # must report 0.32.8 or newer
```

### Step 1 — pull, from anywhere on the LAN

```shell
export OLLAMA_HOST=http://192.168.100.67:11434
ollama list                       # sanity: must show the server's models, not local
ollama pull muse-glimmer:30b      # ~18.2 GB, downloaded by the server
```

Do **not** pull `muse-glimmer:30b-mlx` — that is the Apple Silicon build and is
useless on an NVIDIA host.

### Step 2 — create the deployable variant

```shell
cat > /tmp/Modelfile-muse-agentic <<'EOF'
FROM muse-glimmer:30b
PARAMETER num_ctx 131072
PARAMETER temperature 0
PARAMETER presence_penalty 0
EOF
ollama create muse-glimmer:30b-ctx128k-agentic -f /tmp/Modelfile-muse-agentic
```

### Steps 1–3, automated: `./muse-bench.sh`

Steps 1 and 2 above, plus the whole verification sequence below, are wired into
**`muse-bench.sh`** in this directory. It is deliberately thin — the seven agentic
gates, the context-cliff probe and the throughput harness were written and validated
in `../ollamaClaudeCode_v1`, take `--host` and a model as arguments, and are driven
as-is rather than reimplemented. It adds only what v1 could not test, because nothing
on the farm could do it: **vision** and the **reasoning-effort dial**.

```shell
./muse-bench.sh --host 192.168.100.67          # everything
./muse-bench.sh --host 192.168.100.67 --stage cliff   # one stage
```

It refuses to run against an Ollama below 0.32.8 and prints the upgrade command,
because the interesting failure mode is not a crash: on 0.32.5 nothing gets
installed, so every stage would "run" against an absent model and emit a wall of
FAILs that read like model defects.

### Step 3 — verify before trusting it

Run in this order; each step catches a failure the next one would misattribute.
Stages 1–7 are what `muse-bench.sh` executes.

1. **Residency.** `/api/ps` after a first prompt — the whole thing must read
   `100% GPU`. Any CPU split means the estimate in §3 is wrong and throughput will
   fall off a cliff.
2. **Real KV cost.** Compare resident size against §3's two bounds to settle whether
   Ollama honours the sliding window. This is the measurement the q8_0 question in
   §2b turns on — record the answer here when it lands.
3. **The 16K cliff.** The bare tag is expected to cap at 16386 processed tokens with
   `tool_use=NO`; the variant must process the full prompt with `tool_use=YES`. If
   the variant also caps, stop and fix that before anything else — every later result
   would be measuring a 16K model.
4. **Agentic gates.** All seven from v1: single tool, tool selection, multi-turn with
   `tool_result`, parallel calls, nested schema, needle retrieval, and tool use at
   large context. Gates 6 and 7 are the ones that decide repo-scale usability.
5. **Throughput.** Replaces the §5 estimate with a measurement, benchmarked head to
   head against the incumbent in the same run. Delete the estimate once it does.
   Add `muse-glimmer:30b-q4_K_M-dflash` here — it is the one variable with real
   upside (§2b).
6. **Vision** — post an image and confirm a coherent description.
7. **Reasoning effort** — confirm how `low`/`medium`/`high`/`xhigh` are plumbed
   through Ollama's API and what each costs. If the dial is not exposed per-request,
   it has to be baked into four variants the way `num_ctx` was.
8. **SWE-bench Lite through Claude Code** — *not* in `muse-bench.sh`, because it is a
   day-scale run, not a stage. This is the only test that answers the actual question
   (§5): the incumbent scored **24/300 = 8.0%** through this harness. Reuse the v2
   runner and compare like for like, same prompt construction, same 300 instances.

### Step 4 — point Claude Code at it

Existing route, per `../ollamaClaudeCode_v0/LOCAL_OLLAMA_BACKEND.md`:

```shell
export ANTHROPIC_BASE_URL=http://192.168.100.67:11434
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_MODEL=muse-glimmer:30b-ctx128k-agentic
```

Upstream also added a first-class launcher in 0.32.8 — untested here, and it will
use the **bare tag**, so it is subject to the 16K cliff in §4 unless it sets
`num_ctx` itself:

```shell
ollama launch claude --model muse-glimmer
```

Prefer the explicit `ANTHROPIC_BASE_URL` route with the baked variant until someone
verifies what `launch` actually sends.

---

## 7. What is measured, estimated, and unknown

Keeping the `ollamaFarm` house rule: never present an estimate as a measurement.

**Measured / exact** — every figure in §2, taken from the GGUF header and registry
manifest; the 412 refusal and both server versions in §1; the arithmetic in §3;
the 16K cliff, the 5.3× spill cost, the `presence_penalty` and `temperature`
findings, and the 131.5 tok/s incumbent, all from `../ollamaClaudeCode_v1/review2.md`.

**Estimated, and labelled as such** — the ~25–32 tok/s in §5. Bandwidth-derived from
two dense measurements on this box. Replace it with step 5 of §3's checklist.

**Unknown until the model loads** — whether Ollama trims KV for the sliding-window
layers; tool-call reliability of the new `glimmer` parser through `/v1/messages`;
vision throughput and whether the projector stays resident on text-only runs; how
reasoning effort is plumbed; real behaviour at 100k+ prompt tokens.

**Third-party, not ours** — the entire benchmark table in §5. Published by the vendor
and by Unsloth, against a sibling of our incumbent rather than the incumbent itself.

**Blocked** — the upgrade of `.67` to 0.32.8, which needs host access I do not have.
Everything downstream is ready: `./muse-bench.sh --host 192.168.100.67` runs stages
1–7 unattended and writes to `results/`. Expected wall-clock is dominated by the
~18 GB pull and the large-context gates.

## 7b. Measured results, 2026-08-11 — local run

Run on **this laptop**, not on `.67`: Ollama 0.32.8 installed user-local (tarball
into `~/.local`, no sudo, no systemd unit, nothing outside `$HOME`), serving on
`127.0.0.1:11434`. RTX A2000 8 GB, so only 13–15 of 53 layers were GPU-resident.

**Every capability result below is a property of the model and transfers to `.67`.
Every speed number is a property of this laptop and does not.**

### Tool calling — the gates that decide Claude Code compatibility

Run with v1's `agentic-test.sh`, unmodified.

| gate | result |
|---|---|
| T1 single tool, simple schema | **PASS** — correct args |
| T2 tool selection among 4 tools | **PASS** — chose `search_code` |
| T3 multi-turn with `tool_result` | **PASS** — consumed its own tool output |
| T4 parallel tool calls | **PASS** — 2 calls in one turn |
| T5 complex nested schema | **PASS** — exact, 2 edits, no drift |

Five for five. The new `glimmer` parser emits real `tool_use` blocks through
`/v1/messages`, including parallel calls and nested enum/array schemas. **This is the
result that matters most, and it is unambiguous.**

### Long-context retrieval — and a harness bug that hid it

The first run scored T6 **FAIL at every depth**, including 3563 tokens. That was
wrong, and the raw responses show why:

```json
{"message":{"content":"CRIMSON-PANG"},"done_reason":"length","eval_count":64}
```

The model found the needle. v1's harness sends `num_predict: 64`, Muse Glimmer needed
**70**, and it was cut off three characters into the passphrase — so the grep for
`CRIMSON-PANGOLIN-4471` missed and the row was recorded as a miss. **Six tokens.**
That is the same budget artifact `review2.md` documented for tool calls at
`max_tokens=1200`; it was fixed there and left at 64 in the needle path.

Re-run with `needle-v2.sh` (`num_predict 512`, everything else identical to v1's
generator, against the `ctx128k` variant):

| depth | result | prompt tokens actually processed | gen |
|---|---|---|---|
| 4k | **PASS** | 3,563 | 70 |
| 16k | **PASS** | 13,741 | 70 |
| 60k | **PASS** | 56,311 | 84 |
| **120k** | **PASS** | **114,487** | 72 |

**Muse Glimmer retrieves a mid-document needle at 114,487 prompt tokens.** For
comparison, v1's `needle-retest.log` has `qwen3.6:27b-q4_K_M-ctx128k` passing 4k/16k/
60k and **failing at 120k**. The 128K window is real, not nominal — which is exactly
what the sliding-window architecture and the cheap KV were promising in §2.

### The half-window overflow bug is still present in Ollama 0.32.8

Worth recording separately, because it caused the other four false failures and it is
a *server* bug, not a model trait. Against the `ctx32k` variant, prompts larger than
the window reported `prompt_eval_count = 16387` — half of 32768, plus framing:

| requested | num_ctx | processed | outcome |
|---|---|---|---|
| ~60k tokens | 32768 | **16,387** | needle discarded → FAIL |
| ~120k tokens | 32768 | **16,387** | needle discarded → FAIL |
| T7 tool call at long ctx | 32768 | **16,387** | 0/3, no `tool_use` |

`review2.md` measured this on 0.32.5 and called it a regression. **It is unfixed in
0.32.8.** The operational consequence is the same as the 16K cliff: overflow your
baked `num_ctx` and you silently lose half the window *and* tool calling, with no
error. Size the variant for the real workload; do not rely on graceful degradation.

### Speed — laptop only, reported for completeness

| prompt tokens | prefill | generation |
|---|---|---|
| 3,563 | 195.1 tok/s | 2.86 tok/s |
| 13,741 | 119.0 tok/s | 2.45 tok/s |
| 56,311 | 112.1 tok/s | 1.60 tok/s |
| 114,487 | 103.0 tok/s | 0.80 tok/s |

With 13 of 53 layers on an 8 GB laptop GPU and the rest streaming from system RAM and
swap, these say nothing about `.67` beyond one useful shape: **prefill degrades
gently across the full window** (195 → 103 tok/s from 3.5k to 114k), which is the
sliding-window attention behaving as designed. Generation falls off because the box
is swapping, not because of the model.

**The `.67` throughput estimate of ~25–32 tok/s in §5 remains an estimate.** It cannot
be measured without the server, and nothing here changes it.

## 8. Plan

| # | step | status |
|---|---|---|
| 1 | Discover the target server, confirm it is the 40 GB box | **done** — `.67`, via `~/repos/ollamaFarm` |
| 2 | Pull `muse-glimmer` onto it | **blocked** — HTTP 412, needs Ollama ≥ 0.32.8 |
| 3 | Establish the architecture from primary sources | **done** — §2, from the GGUF header and registry blobs |
| 4 | Decide the context window | **done** — §4, `131072`, baked into a Modelfile variant |
| 5 | Decide the quantization | **done** — §2b, Q4_K_M; **q8_0 rejected with reasons** |
| 6 | Build the benchmark runner | **done** — `muse-bench.sh`, drives the v1 harness |
| 7 | Run the capability gates | **done locally** — §7b, 5/5 tool gates and 4/4 needles pass |
| 8 | Measure throughput on `.67` | **waiting on step 2** — laptop numbers do not transfer |

SWE-bench Lite was dropped from scope on 2026-08-11 at the user's direction: the
question is capability and speed, and a day-scale resolve-rate run answers neither
quickly. The 8.0% figure stays in §5 as context for reading published benchmarks, not
as a test to repeat.

**The one action that unblocks steps 2, 7 and 8**, on `192.168.100.67`:

```shell
curl -fsSL https://ollama.com/install.sh | sh && sudo systemctl restart ollama
```
