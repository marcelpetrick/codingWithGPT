# Muse Glimmer and Nemotron 3.5 Lightning on the 40 GB server (`192.168.100.67`)

Written 2026-08-11, **substantially revised 2026-08-13** after `.67` was upgraded.
Continues the work in `../ollamaClaudeCode_v1/` (measurement harness, `review2.md`,
`fitting_models.md`) and `../ollamaClaudeCode_v0/` (`OLLAMA_PULL.md`,
`LOCAL_OLLAMA_BACKEND.md`).

> **Status 2026-08-13: unblocked and installed.** `.67` now runs Ollama **0.32.9**,
> which satisfies `muse-glimmer`'s `requires: 0.32.8`. Both models were pulled onto
> the server and benchmarked there. §7b's laptop numbers are superseded by §7c, which
> is measured on the real hardware; the laptop install has been deleted.

### Revision note — what changed on 2026-08-13, and what did not

The server moved under this document, so every claim about it was re-checked against
the wire rather than carried forward. Recording both outcomes, because "still true"
is as much a result as "was wrong":

| claim | status on 0.32.9 |
|---|---|
| `.67` runs Ollama 0.32.5 | **wrong now** — 0.32.9. The 412 gate is gone |
| the install is blocked | **wrong now** — both models pulled fine |
| incumbent qwen3.6 MoE does 131.5 tok/s | **still true** — re-measured 131.4 tok/s |
| bare tags cap at ~16K and lose `tool_use` | **still true** — re-measured, see §4 |
| overflowing a baked window discards half of it | **still true, and now proven properly** — see §4 |
| `.67` = 40.4 GB | **not spendable** — measured usable ceiling is ≈35.5 GB (§11.4) |
| Muse Glimmer throughput ≈ 25–32 tok/s (estimate) | **superseded by measurement** — §7c |

**A second round on 2026-08-13** added `qwen3.6:35b-a3b-mtp-q4_K_M` and
`qwen3.6:27b-q8_0` for a five-model comparison, and in doing so **found three errors in
this document's own earlier conclusions** — the incumbent's retrieval depth, Muse
Glimmer's vision exclusivity, and the recommendation built on both. All are corrected in
**§11**, which is the section to read if you only read one.

One earlier claim also turned out to be under-evidenced rather than wrong, and is
corrected in §4: the "half window" finding had been measured only at `num_ctx=32768`,
where a half-window discard and a fallback to the 16384 default are the *same number*.
It has now been re-run at a 60k window, which separates them.

---

## 1. What was done

Host discovery first, using the project in `~/repos/ollamaFarm/`. Its default host
list is `192.168.100.37 192.168.100.67`; a full `/24` sweep of `/api/version`
confirms that list is still complete — `.13` and `.99`, which appear in the
ollamaFarm README, are not currently on the network.

| host | Ollama (2026-08-13) | VRAM | note |
|---|---|---|---|
| `192.168.100.37` | 0.30.6 | 12.3 GB | too small for a 28B, **and too old for either model** |
| **`192.168.100.67`** | **0.32.9** | **40.4 GB (stated, not measured — see below)** | the target |
| `192.168.100.13`, `.99` | offline | — | in the ollamaFarm README, not on the network |

`.37` was not upgraded and is a non-target twice over: 0.30.6 is below Muse Glimmer's
`requires: 0.32.8`, and 12.3 GB will not hold either model regardless.

**On the 40.4 GB figure — it is stated, not measured, and cannot be measured from
here.** It comes from ollamaFarm's hardcoded `VRAM_TOTAL` table
(`declare -A VRAM_TOTAL=( [192.168.100.37]=12.3 [192.168.100.67]=40.4 )`), whose own
`docs/vram-discovery.md` is explicit that **the Ollama HTTP API exposes no total-VRAM,
free-VRAM or GPU-count field anywhere** — `/api/ps` gives per-model `size` and
`size_vram` and nothing else. So 40.4 GB is a number a human stands behind, not one
this document verified. What *was* verified is the only thing that actually matters
operationally: everything loaded during this evaluation reported **100% GPU
residency** with no split (§7c), and a 24 GB model plus a 19 GB model both sat there
without spilling.

### Why the pull used to fail, and why it now does not

The refusal was never about access. Until 2026-08-12 the request came back as:

```console
$ curl -s -X POST http://192.168.100.67:11434/api/pull -d '{"model":"muse-glimmer:30b"}'
{"status":"pulling manifest"}
{"error":"pull model manifest: 412: \nThe model you are attempting to pull requires
a newer version of Ollama.\n\nPlease download the latest version at:\n\n\thttps://ollama.com/download\n"}
```

This was not a guess about which version was needed. The registry config blob says so
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
| v0.32.5 | 2026-07-27 | what `.67` ran until 2026-08-12 |
| v0.32.7 | 2026-08-10 | Muse Glimmer, **Apple Silicon / MLX only** |
| **v0.32.8** | **2026-08-10** | *"Add Muse Glimmer support for NVIDIA, AMD, and additional platforms"* |
| **v0.32.9** | — | **what `.67` runs now** — satisfies the gate |

`.67` is an NVIDIA box, so 0.32.7 would not have been enough either; 0.32.8 was the
floor and 0.32.9 clears it. The upgrade was performed by the box's administrator, not
by me — `ssh 192.168.100.67` still returns `Permission denied (publickey,password)`,
and every operation in this document is done over HTTP.

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

| model | `requires` | old 0.32.5 | current 0.32.9 |
|---|---|---|---|
| `qwen3.6:35b-a3b-q4_K_M` | *(none)* | yes | yes |
| `qwen3.6:27b-q8_0` | *(none)* | yes | yes |
| `qwen3.5:9b` | `0.17.1` | yes | yes |
| **`muse-glimmer:30b`** | **`0.32.8`** | **no** | **yes** |
| **`nemotron-3.5-lightning:30b`** | *(none declared)* | — | yes |

So it was never a permissions problem, a network problem, or a procedure we had
forgotten. It was a model released *the day before yesterday* demanding a runtime
released *yesterday*, on a server last updated 2026-07-27. One `apt`-scale action on
the host cleared it, and the `/api/pull` + `/api/create` path described above worked
unchanged the moment it did.

### 1c. Why the gate was real, and why sideloading around it would not have helped

Kept after the upgrade, because it answers the question *"why does the server need a
newer Ollama at all?"* — and because it is the evidence that waiting for the upgrade
was the right call rather than an admission of defeat.

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

## 2c. The second candidate: Nemotron 3.5 Lightning

Added to scope on 2026-08-13. Same method as §2 — everything below is read out of the
registry manifest, the config blob and the GGUF metadata header, not the model card.

```console
$ curl -sL https://registry.ollama.ai/v2/library/nemotron-3.5-lightning/blobs/sha256:7101a4a1d9e3…
{"model_format":"gguf","model_family":"nemotron_h_moe","model_families":["nemotron_h_moe"],
 "model_type":"32.9B","file_type":"Q4_K_M","renderer":"nemotron-3.5-nano",
 "parser":"nemotron-3.5-nano","requires":"0.32.9","architecture":"amd64","os":"linux"}
```

Two things to flag immediately, because both contradict the library web page:

- **It declares `requires: 0.32.9`.** The Ollama library page lists no minimum
  version. `.67` clears this by exactly one patch release — had the administrator
  stopped at 0.32.8, Muse Glimmer would have installed and this one would not. It also
  ships its own `nemotron-3.5-nano` renderer and parser, so §1c's argument applies
  verbatim: that code is compiled into the binary, not carried in the GGUF.
- **The GGUF says 32.9B and `128x2.5B`, not "30B".** There is no vision projector
  layer in the manifest — `model`, `template`, `license`, `params` and nothing else —
  confirming it is **text-only**.

| property | value | source |
|---|---|---|
| architecture | **`nemotron_h_moe` — hybrid Mamba-2 SSM + attention MoE** | GGUF `general.architecture` |
| parameters | 32.9B total, **128 experts, 6 active + 1 shared** | config / `expert_count`, `expert_used_count` |
| weights on disk | **25.431 GB** (Q4_K_M) | manifest |
| layers | **53** | `block_count` |
| **attention layers** | **7 of 53** — indices 5, 12, 19, 26, 33, 42, 52 | `head_count_kv` array |
| SSM layers | **46 of 53** (`conv_kernel 4`, `state_size 128`, `group_count 8`, `inner_size 4096`) | `ssm.*` |
| native context | **1048576 (1M)** | `context_length` |
| embedding dim | **2688** (small — it is a wide-MoE, narrow-residual design) | `embedding_length` |
| attention heads | 32 query / 2 KV | `head_count` / `head_count_kv` |
| expert FFN / shared FFN | 1856 / 3712, `expert_weights_scale 2.5`, norm on | `expert_*` |
| speculative decoding | **`nextn_predict_layers 1`** — MTP head built in | GGUF |
| RoPE base | 10000 (vs Muse's 500000) | `rope.freq_base` |
| capabilities | tools, thinking. **No vision** | manifest / model card |

**The layer map is the whole story.** Rendering `head_count_kv` per block, `A` for an
attention layer and `~` for an SSM/MoE one:

```
~~~~~A~~~~~~A~~~~~~A~~~~~~A~~~~~~A~~~~~~~~A~~~~~~~~~A
```

A Mamba-2 layer carries a fixed-size recurrent state; its cost does not grow with
sequence length. Only the 7 attention layers keep a KV cache. At the same
1024 B/token/layer this document derived in §3:

| num_ctx | KV cache (7 attention layers) | + 25.43 GB weights |
|---|---|---|
| 131072 | **0.94 GB** | ≈ 26.4 GB |
| 262144 | **1.88 GB** | ≈ 27.3 GB |
| 1048576 | **7.52 GB** | ≈ 32.9 GB |

So on paper the **full 1M window fits on a 40 GB box**, which nothing else on this
farm can claim. Muse Glimmer gets its cheap KV from sliding windows (39 of 52 layers
capped at 2048); Nemotron gets it by not having attention in 46 of 53 layers at all.
Different mechanism, same consequence, and Nemotron's scales further.

**MoE with 6 of 128 experts active is the profile `fitting_models.md` said this
hardware wants** — the opposite of Muse Glimmer's dense 16.76 GB per token. That is
the reason to expect it to be the faster of the two despite being the larger download,
and §7c measures whether it is.

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

> **Corrected 2026-08-13 on `.67`.** Both halves of the paragraph above need adjusting,
> and in the useful direction. Measured on the server at the full `num_ctx=131072`, the
> model reports **19.45 GB** — and it still reports **19.45 GB after a real image
> request**, unchanged. So the "+1.40 GB with vision" row in the table above never
> materialises: **vision is free**, not paged in on top. The right budget line for
> Muse Glimmer at its full native window, text or image, is **19.45 GB**, leaving
> ~17 GB spare. See §7c.

---

## 4. Best context window: `131072`, and it must be baked in

**Use the full native 131072. Do not tune it down — there is nothing to buy with the
saved GB, and nothing above it to reach for.**

The non-obvious half is that setting it at request time does not work for our use
case, and failing to bake it in fails *silently*.

### Re-measured on 0.32.9, 2026-08-13 — both traps survive the upgrade

There are **two** distinct silent-truncation failures, not one. They were conflated
in the earlier draft because at `num_ctx = 32768` they produce the same number.
`./cliff-probe.sh --host 192.168.100.67 --port 11434`, run against models already on
the box so the result is about the *server*, not about Muse Glimmer:

| model | prompt | processed | `tool_use` |
|---|---|---|---|
| `qwen3.6:27b-q4_K_M` *(bare tag)* | ~4k | 4,090 | YES |
| `qwen3.6:27b-q4_K_M` *(bare tag)* | ~16k | 16,090 | YES |
| `qwen3.6:27b-q4_K_M` *(bare tag)* | ~32k | **16,386** | **NO** |
| `qwen3.6:27b-q4_K_M` *(bare tag)* | ~50k | **16,386** | **NO** |
| `qwen3.6:27b-q4_K_M-ctx128k` | ~32k | 33,290 | YES |
| `qwen3.6:27b-q4_K_M-ctx128k` | ~50k | 53,090 | YES |

**Trap 1 — the bare tag inherits a 16384 default.** `/v1/messages` has no `num_ctx`
knob, so a model whose Modelfile leaves it unset is capped at 16,386 processed tokens
no matter how much you send. The tail of the prompt — where the instruction lives — is
discarded, and `tool_use` stops entirely. **No error is returned.** Unchanged from
0.32.5; the upgrade did not fix it.

**Trap 2 — overflowing a baked window costs you half of it.** This one had been
asserted on weaker evidence than it deserved. The earlier measurement used a 32768
variant and saw 16,387 processed — but "half of 32768" and "fell back to the 16384
default" are the same number, so that run could not tell the two apart. Re-run at a
window where they differ, using the 60k variant already on the box:

```
qwen3.6:27b-q8_0-ctx60k, ~120k tokens sent via /v1/messages:
  input_tokens = 30002   stop = end_turn   tool_use = NO
```

**30,002 — half the window, not 16,386.** The half-window discard is real, it is
separate from trap 1, and it is still present in 0.32.9. The operational consequence
is the same in both cases and worth stating plainly: **overflow your window and you
silently lose both context and tool calling.** Size the variant for the real workload;
do not rely on graceful degradation, because there is none.

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

## 5. Verdict: are these worth using as a Claude Code driver?

**Everything in this section is now measured on `.67`.** The three-way summary, all
from §7c, with the server idle before every run:

> **Superseded by §11, which corrects two errors in the table below.** Two of this
> table's cells were wrong and both flattered the newcomers: the incumbent does **not**
> fail at 120k (it passes at 146,957 — the "fails" datum belonged to a different model),
> and vision is **not** unique to Muse Glimmer (every `qwen3.6` tag has it, and the
> incumbent is 4.5× faster at it). **Read §11.** The table is kept as written so the
> correction is legible rather than silently patched.

| | `qwen3.6:35b-a3b-q4_K_M-agentic` *(incumbent)* | `muse-glimmer:30b` | `nemotron-3.5-lightning:30b` |
|---|---|---|---|
| **generation** | **131.4 tok/s** | 27.9–28.9 tok/s | **44.9–48.5 tok/s** |
| **prefill** (~35k prompt) | **3,988 tok/s** | 1,962 tok/s | 3,050 tok/s |
| resident / window | 32.54 GB @ 262144 | **19.45 GB @ 131072** | 31.21 GB @ 262144 |
| GPU residency | 100% | 100% | 100% |
| tool gates T1–T5 | pass | **5/5** | **5/5** |
| needle, deepest pass | ~~fails at 120k~~ **PASS @146,957** | **114,487 tok** | **161,516 tok** |
| max window at 100% GPU | 262144 | 131072 (native) | **524288** |
| vision | ~~no~~ **yes, and faster** | yes | no |
| thinking dial | no | `low`/`medium`/`high` | yes |

**The headline, as revised:** the incumbent is 3–4.5× faster than either newcomer,
retrieves as deeply, and does vision better. **Neither newcomer displaces it for any
workload except one** — Nemotron is the only model that stays fully GPU-resident beyond
262144 tokens.

~~Between the two new models, Nemotron is the better general pick … Muse Glimmer earns
its place only where vision matters.~~ **Withdrawn.** Nemotron's apparent retrieval
advantage was a tokenizer artifact (§11.1) and Muse Glimmer's vision advantage does not
exist (§11.2). See §11.6 for the recommendation that replaces this.

Two caveats that the raw table hides:

- **Nemotron's tokenizer is less efficient on code-like text.** The identical needle
  document measured 3,563 tokens for Muse and **4,916 for Nemotron — 38% more**. Its
  context advantage in *characters* is therefore meaningfully smaller than its
  advantage in tokens, and its effective speed lead shrinks on token-dense input.
- **Muse's dense architecture is the reason it is slow**, and that will not improve.
  §2 predicted this and §7c confirms it: 16.76 GB streamed per generated token against
  Nemotron's ~6 active experts.

The rest of this section — the pre-measurement estimate and the published-benchmark
table — is kept for the record.

### The original estimate, and how it held up

Before the server was upgraded, throughput was extrapolated from two dense reference
points on this box (`qwen3.6:27b-q8_0`, 29.97 GB → 18.1 tok/s; `llama3.1:8b`, ~4.9 GB
→ 86.9 tok/s) to:

> **~25–32 tok/s — an estimate, not a measurement.**

**Measured: 27.9–28.9 tok/s.** The bandwidth derivation was sound, and it is recorded
here as a check on the method rather than to claim credit — the same method predicted
q8_0 would spill, and §2b shows that one was wrong.

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
prediction of what it will resolve here.** A SWE-bench Lite run through this harness is
the only thing that would settle it, and it was dropped from scope (§8) — so this table
stays what it always was: third-party context, not a result.

**Recommended split, now measured:** keep `qwen3.6:35b-a3b-q4_K_M-agentic` as the
default driver for bulk agentic coding — **131.4 tok/s** is not a number you give up
lightly on a long run. Reach for **`nemotron-3.5-lightning:30b-ctx256k-agentic`** when
the working set is large: it retrieves at **161k tokens** where the incumbent fails at
120k, and at 44.9 tok/s it costs less than Muse for the privilege. Reach for
**`muse-glimmer:30b-ctx128k-agentic`** for the one thing neither of the others can do
at all: **anything with an image in the loop**.

The `xhigh` reasoning level that earlier drafts leaned on as a Muse selling point is
**not available** — Ollama 0.32.9 rejects it (§7c). Three levels, not four.

**None of the three co-reside**: 19.45 + 31.21 + 33.08 GB against ~40 GB. Switching
models costs an eviction and an ~18 s reload, measured. `ollamaFarm` will show it.

---

## 6. Install procedure — as actually performed on 2026-08-13

### Step 0 — upgrade `.67` to ≥ 0.32.8 *(done by the box's administrator)*

```shell
# on 192.168.100.67
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl restart ollama
ollama --version          # reports 0.32.9
```

Note the version actually landed on: **0.32.9, not 0.32.8**. That turned out to
matter — `nemotron-3.5-lightning` declares `requires: 0.32.9` (§2c), so 0.32.8 would
have installed Muse Glimmer and refused Nemotron.

### Step 1 — pull, from anywhere on the LAN

No SSH involved; the *server* does the downloading.

```shell
export OLLAMA_HOST=http://192.168.100.67:11434
ollama list                              # sanity: the server's models, not local
ollama pull muse-glimmer:30b             # 16.76 GB text + 1.40 GB vision projector
ollama pull nemotron-3.5-lightning:30b   # 25.43 GB
```

Or equivalently, which is what was used here so progress could be logged:

```shell
curl -X POST http://192.168.100.67:11434/api/pull \
  -H 'Content-Type: application/json' -d '{"model":"muse-glimmer:30b","stream":true}'
```

Do **not** pull the `-mlx` tags of either model — those are Apple Silicon builds and
are useless on an NVIDIA host.

### Step 2 — create the deployable variants

The bare tag is never the deployable artifact, for the reason measured in §4.

```shell
curl -X POST http://192.168.100.67:11434/api/create -H 'Content-Type: application/json' \
  -d '{"model":"muse-glimmer:30b-ctx128k-agentic","from":"muse-glimmer:30b",
       "parameters":{"num_ctx":131072,"temperature":0,"presence_penalty":0},"stream":false}'

curl -X POST http://192.168.100.67:11434/api/create -H 'Content-Type: application/json' \
  -d '{"model":"nemotron-3.5-lightning:30b-ctx256k-agentic","from":"nemotron-3.5-lightning:30b",
       "parameters":{"num_ctx":262144,"temperature":0,"presence_penalty":0},"stream":false}'
```

### Step 3 — the benchmark battery: `./head2head.sh`

This is what actually produced §7c, and it replaced `muse-bench.sh` as the entry point
once there were **two** models to compare rather than one to characterise.

```shell
./head2head.sh --host 192.168.100.67 \
    muse-glimmer:30b-ctx128k-agentic \
    nemotron-3.5-lightning:30b-ctx256k-agentic
```

Per model it runs throughput → residency/KV → tool gates T1–T5 → needle retrieval, and
between **every** stage it calls `./idle.sh`, which unloads whatever is resident and
polls `/api/ps` until the server is genuinely empty. That gate is the point of the
script. `.67` holds ~40 GB; these models are 19.45 and 31.21 GB, so two of them cannot
co-reside, and a benchmark that starts against a busy box measures eviction, reload and
spill instead of the model. `review2.md` put a 12.5% spill at **5.3× slower** — larger
than the real difference between any two models here, so a co-resident run would have
produced a confident, wrong verdict. If the server will not empty, `head2head.sh`
aborts rather than producing a number.

Supporting scripts, each usable alone:

| script | what it answers |
|---|---|
| `./idle.sh` | is the server empty? make it so, or fail |
| `./tokrate.sh` | prefill and generation tok/s from Ollama's own counters |
| `./cliff-probe.sh` | do bare tags still silently truncate? (§4) |
| `./needle-v2.sh` | retrieval depth, with a generation budget that does not manufacture failures |
| `./kv-probe.sh` | how does footprint scale with `num_ctx`? |
| `./muse-bench.sh` | the original single-model runner; superseded, kept because its preflight documents the 0.32.8 gate |

### Step 3b — the order to verify in, and why

Each check catches a failure the next one would misattribute:

1. **Residency first.** `/api/ps` must read `100% GPU`. Any CPU split and every later
   number is measuring the spill, not the model. *(Result: 100% for both.)*
2. **Real footprint vs. prediction.** Sweep `num_ctx` and find where residency stops
   being 100%. *(Result: Nemotron holds to 524288 and spills at 1048576.)*
3. **The truncation traps.** The bare tag must cap at ~16386 with `tool_use=NO`, the
   variant must process the full prompt. If the *variant* caps too, stop — everything
   after would be measuring a 16K model. *(Result: both traps confirmed live, §4.)*
4. **Agentic gates.** T1–T5 decide Claude Code compatibility at all. *(Result: 10/10.)*
5. **Needle retrieval** with an adequate `num_predict` — **not** v1's T6, which sends
   64 and truncates Muse mid-passphrase. *(Result: 8/8.)*
6. **Throughput**, on an idle box, head to head with the incumbent in the same session.
7. **Vision** and **reasoning effort** — the two things v1 could not test at all.

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

**Measured on `.67`** — everything in §7c: throughput for all three models, residency
and GPU split, the context sweep to 1M, all ten tool gates, all eight needle depths,
vision, and the reasoning-effort dial. Plus the two truncation bugs re-measured in §4.

**Measured / exact, from primary sources** — every figure in §2 and §2c, taken from the
GGUF metadata headers and registry manifests, and cross-checked against `/api/show` on
the server after install.

**Inherited from v1 and re-verified where it mattered** — the 131.5 tok/s incumbent
(re-measured 131.4), the 16K cliff (re-measured), the half-window discard (re-measured
*and* strengthened). The 5.3× spill cost and the `presence_penalty`/`temperature`
findings are carried over from `review2.md` and were **not** re-run here.

**Estimated, and superseded** — the ~25–32 tok/s in §5 was an estimate; it measured
27.9–28.9. It is kept only as a check on the estimation method.

**Stated by a human, not verifiable here** — `.67` = 40.4 GB. The Ollama HTTP API has
no VRAM field at all (§1). What is verified is that everything loaded stayed at 100%
GPU up to 32.38 GB, and spilled at 34.17 GB — which brackets the true ceiling between
those two figures without confirming 40.4.

**Still unknown** — why Nemotron's per-token footprint is ~21.5 kB rather than the
~7 kB its 7 attention layers imply (§7c); whether `-dflash` tags are faster, which was
dropped to keep the run serial; and how either model behaves over a multi-hour Claude
Code session rather than a gate.

**Third-party, not ours** — the entire published benchmark table in §5, from the vendor
and Unsloth, against a sibling of our incumbent rather than the incumbent itself.

**No longer blocked** — `.67` is on 0.32.9 and both models are installed and measured.

## 7c. Measured results, 2026-08-13 — on `.67`, the real hardware

**These supersede §7b.** Every number below was taken on `192.168.100.67`
(Ollama 0.32.9) with the server verified idle before each stage by `./idle.sh`, and
one model resident at a time — 17 GB and 25 GB cannot co-reside in ~40 GB, and a
partial offload would have been measured as a model defect rather than a scheduling
one. Driven by `./head2head.sh --host 192.168.100.67 <model>`; raw logs in
`results/h2h-muse.log` and `results/h2h-nemotron.log`.

### Throughput (`./tokrate.sh`, Ollama's own counters, `temperature 0`, `seed 42`)

| model | prompt tok | prefill tok/s | **generation tok/s** | cold load |
|---|---|---|---|---|
| `qwen3.6:35b-a3b-q4_K_M-agentic` | 25 | 92 | **123.30** | 11.6 s |
| *(incumbent)* | 3,180 | 3,017 | **131.37** | — |
| | 35,102 | 3,988 | **112.32** | — |
| `muse-glimmer:30b-ctx128k-agentic` | 69 | 317 | **28.91** | 18.4 s |
| | 2,624 | 1,168 | **28.54** | — |
| | 27,180 | 1,963 | **27.91** | — |
| `nemotron-3.5-lightning:30b-ctx256k-agentic` | 29 | 3 | **48.45** | 18.2 s |
| | 3,457 | 2,619 | **43.91** | — |
| | 37,836 | 3,050 | **44.93** | — |

The incumbent's **131.4 tok/s reproduces v1's 131.5** on the newer runtime, which is
what makes the other two rows comparable to the v1 corpus at all.

Generation is essentially flat with prompt length for all three — the models are
memory-bandwidth-bound on weights, not on context. **Nemotron is 1.6× Muse**, exactly
as §2c predicted from 6-of-128 active experts versus a dense 16.76 GB.

### Residency and the real context ceiling

```
muse-glimmer:30b-ctx128k-agentic       total 19.45 GB  vram 19.45 GB  100% GPU  ctx=131072
nemotron-3.5-lightning:30b-ctx256k…    total 31.21 GB  vram 31.21 GB  100% GPU  ctx=262144
```

Muse at **19.45 GB** against §3's predicted ≈18.9 GB — close, and comfortably inside
budget with ~17 GB spare at its full native window.

**A correction to §3:** that section predicted vision would add +1.40 GB on top. It
does not. After a real image request the model still reported **19.45 GB, unchanged**.
The projector is inside the figure already; vision is free on this box.

Nemotron's footprint was swept with `./kv-probe.sh` (`results/kv-nemotron.txt`):

| `num_ctx` | resident | GPU |
|---|---|---|
| 32768 | 26.28 GB | 100% |
| 131072 | 28.39 GB | 100% |
| 262144 | 31.21 GB | 100% |
| **524288** | **32.38 GB** | **100%** |
| 1048576 | **34.17 GB** | **96% — spills 1.3 GB** |

**The full 1M window loads but does not fit.** At 96% GPU, 1.3 GB sits in system RAM,
and `review2.md` measured a 12.5% spill costing **5.3× throughput**. So the honest
ceiling is **524288 at 100% GPU**, and 262144 is the safe production setting.

Note also that the growth is **not linear** — ~21.5 kB/token between 32k and 262k, then
~4.5 kB/token beyond. So the §2c estimate of 1024 B/token × 7 attention layers is *not*
what Ollama actually allocates, and the naive/SWA verdict line `kv-probe.sh` prints is
calibrated for Muse's geometry and is **meaningless for Nemotron** — read the table,
not the verdict. Why the per-token cost is ~3× the KV arithmetic is unexplained and is
recorded as unknown rather than guessed at.

### Tool calling — the gates that decide Claude Code compatibility

Run with v1's `agentic-test.sh`, unmodified, through `/v1/messages`.

| gate | Muse Glimmer | Nemotron |
|---|---|---|
| T1 single tool, simple schema | **PASS** | **PASS** |
| T2 tool selection among 4 tools | **PASS** | **PASS** |
| T3 multi-turn with `tool_result` | **PASS** | **PASS** |
| T4 parallel tool calls | **PASS** | **PASS** |
| T5 complex nested schema | **PASS** | **PASS** |

**Ten for ten.** Both new renderers/parsers (`glimmer`, `nemotron-3.5-nano`) emit real
`tool_use` blocks including parallel calls and nested enum/array schemas. This is the
result that matters most for using either as a Claude Code driver, and it is
unambiguous.

### Long-context retrieval

`./needle-v2.sh`, `num_predict 512`. Both models, mid-document needle:

| depth | Muse: processed | result | Nemotron: processed | result |
|---|---|---|---|---|
| 4k | 3,563 | **PASS** | 4,916 | **PASS** |
| 16k | 13,741 | **PASS** | 19,820 | **PASS** |
| 60k | 56,311 | **PASS** | 79,706 | **PASS** |
| 120k | **114,487** | **PASS** | **161,516** | **PASS** |

**Both retrieve where the incumbent fails.** v1's `needle-retest.log` has
`qwen3.6:27b-q4_K_M-ctx128k` passing 4k/16k/60k and **failing at 120k**. The 128K and
256K windows here are real, not nominal.

The token counts in the two "processed" columns are the same document: **Nemotron
needs 38% more tokens to represent it**. That is a tokenizer difference and it is worth
remembering whenever a context budget is quoted in tokens.

### The `num_predict 64` harness artifact reproduces on the server

Worth recording because it is a trap in the *harness*, not either model. v1's
`agentic-test.sh` T6 still sends `num_predict: 64`:

```
T6_needle_4k    FAIL    missed_at_3563_prompt_tokens     <- muse, via v1 harness
4k              PASS    prompt_eval=3563  eval=70        <- same model, needle-v2.sh
```

Muse Glimmer needs **70** tokens to emit `CRIMSON-PANGOLIN-4471` and gets cut off at
64, three characters into the passphrase. Nemotron is terser (**14** tokens) and passes
the same gate, which is exactly why a budget artifact like this masquerades as a model
difference. **Use `needle-v2.sh`, not v1's T6.**

### Vision — Muse Glimmer only

```
image: ../ollamaClaudeCode_v0/failingOutput.png   prompt_eval=1,177   gen=28.9 tok/s   wall=38.3 s
"The image is a screenshot of a Linux terminal emulator window - **Konsole** -
 whose title bar reads `ollamaClaudeCodeTest : cl…`"
```

Correct: right application, right window title, read off the pixels. A screenshot costs
**~1,177 prompt tokens**, generation runs at the same 28.9 tok/s as text, and residency
does not move. Nothing else on the farm can do this at all.

### Reasoning effort — and one documented capability that is not exposed

| `think` | thinking (approx. tok) | answer tok | wall |
|---|---|---|---|
| `false` | 0 | 562 | 32.5 s |
| `"low"` | ~160 | 516 | 18.6 s |
| `"medium"` | ~277 | 711 | 25.4 s |
| `"high"` | ~635 | 1,139 | 40.4 s |
| `"xhigh"` | — | — | **rejected** |

The dial works and is plumbed through `/api/chat`'s `think` field, costing roughly
linear time in effort. But:

```json
{"error":"invalid think value: \"xhigh\" (must be \"high\", \"medium\", \"low\", …)"}
```

**`xhigh` is advertised on the model card and is not accepted by Ollama 0.32.9.** Three
levels, not four. Anything planned around `xhigh` needs to wait for upstream.

## 7b. Superseded — local laptop run, 2026-08-11

> **Kept only as provenance. Read §7c instead.** This run happened while `.67` was
> still on 0.32.5 and the only way to see the model work at all was to install Ollama
> on the laptop. **That install has since been deleted** at the user's instruction —
> the three `muse-glimmer` tags, the `~/.local/ollama-0.32.8` tree and the local
> server are all gone, and the laptop's pre-existing models were left untouched. Only
> the server is in scope now.

Run on **this laptop**, not on `.67`: Ollama 0.32.8 installed user-local (tarball
into `~/.local`, no sudo, no systemd unit, nothing outside `$HOME`), serving on
`127.0.0.1:11434`. RTX A2000 8 GB, so only 13–15 of 53 layers were GPU-resident.

**Every capability result below is a property of the model and transfers to `.67`.
Every speed number is a property of this laptop and does not** — and the speed numbers
have now been replaced by real ones in §7c.

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
| 2 | Pull `muse-glimmer` onto it | **done** — 2026-08-13, after the 0.32.9 upgrade |
| 3 | Establish the architecture from primary sources | **done** — §2, GGUF header + registry blobs |
| 4 | Decide the context window | **done** — §4, `131072` baked into a variant |
| 5 | Decide the quantization | **done** — §2b, Q4_K_M; **q8_0 rejected with reasons** |
| 6 | Build the benchmark runner | **done** — `head2head.sh` + `idle.sh` + `tokrate.sh` |
| 7 | Run the capability gates | **done on `.67`** — §7c, 10/10 tool gates, 8/8 needles |
| 8 | Measure throughput on `.67` | **done** — §7c, all three models |
| 9 | Add Nemotron 3.5 Lightning | **done** — §2c architecture, §7c measurements |
| 10 | Re-verify the stale `.67` claims | **done** — revision note at the top |

Dropped from scope, deliberately:

- **SWE-bench Lite**, on 2026-08-11 at the user's direction: the question is capability
  and speed, and a day-scale resolve-rate run answers neither quickly. The 8.0% figure
  stays in §5 as context for reading published benchmarks, not as a test to repeat.
- **The `-dflash` variants** (§2b). Each would have meant another ~20 GB pull and a
  second serialized battery; the models must be benchmarked one at a time on this box,
  so the cost is wall-clock, not curiosity. Still the one remaining variable with
  plausible upside.

### What to actually deploy

> **Revised by §11.6** after two more models were measured. The block below is the
> superseded version; its middle and last entries rest on the two errors §11 corrects.

```shell
export ANTHROPIC_BASE_URL=http://192.168.100.67:11434
export ANTHROPIC_AUTH_TOKEN=ollama

# --- current recommendation, per §11.6 ---
# default: 129.0 tok/s, full 262144 window, 3.65 GB lighter than the incumbent
export ANTHROPIC_MODEL=qwen3.6:35b-a3b-mtp-q4_K_M-agentic
# equally good, 131.4 tok/s, no draft_num_predict override to depend on
export ANTHROPIC_MODEL=qwen3.6:35b-a3b-q4_K_M-agentic
# only when the working set exceeds 262144 tokens — its sole remaining advantage
export ANTHROPIC_MODEL=nemotron-3.5-lightning:30b-ctx256k-agentic

# --- superseded ---
# "deep-context work: retrieves at 161k where the incumbent fails at 120k"
#   -> the incumbent does not fail; it passes at 146,957 (§11.1)
# "anything with an image in the loop — the only model here that can"
#   -> the incumbent does vision too, 4.5x faster and more accurately (§11.2)
export ANTHROPIC_MODEL=muse-glimmer:30b-ctx128k-agentic   # not recommended
```

Never the bare tag, for the reason measured in §4. Expect an eviction and an ~18 s
reload when switching — they do not co-reside, and the usable ceiling is ≈35.5 GB, not
40.4 GB (§11.4).

---

## 9. How this was benchmarked

Written so the numbers in §7c can be reproduced, disputed, or re-run against the next
model without re-deriving the method. The house rule from `~/repos/ollamaFarm/AGENTS.md`
applies throughout: **never fabricate a measurement**, and label anything that is not one.

### 9.1 The environment, and the one thing that had to be controlled

All measurements ran against `192.168.100.67`, Ollama **0.32.9**, over HTTP from this
laptop. No SSH — every operation is `/api/pull`, `/api/create`, `/api/chat`,
`/api/show`, `/api/ps`, `/api/delete` or `/v1/messages`.

The single most important control is **residency**. `.67` holds roughly 40 GB and the
models under test are 19.45 GB and 31.21 GB. They cannot co-reside. If a benchmark
starts while the previous model is still held by `keep_alive`, one of three things
happens and all of them silently corrupt the result:

1. the incoming model is evicted and reloaded mid-run, and `load_duration` leaks into
   the timings;
2. the incoming model is **partially offloaded to system RAM** — `review2.md` measured
   a 12.5% spill costing **5.3× throughput**, which is larger than the true difference
   between any two models here, so this failure produces a confident wrong verdict
   rather than an obviously broken one;
3. somebody else's model gets evicted, which is rude on a shared box.

So `./idle.sh` is a hard gate, not a courtesy: it asks every resident model to unload
with `keep_alive: 0`, then **polls `/api/ps` until it is actually empty** rather than
sleeping a guessed interval, and exits non-zero if it cannot. `./head2head.sh` calls it
between *every* stage and **aborts the run** rather than benchmark into a busy server.
Each `-- residency / KV --` block in `results/h2h-*.log` shows the gate firing.

### 9.2 What "tokens per second" means here

Two rates, both taken from **Ollama's own counters** in the `/api/chat` response, never
from wall-clock:

```
prefill    tok/s = prompt_eval_count / prompt_eval_duration
generation tok/s = eval_count        / eval_duration
```

`eval_duration` excludes model load, which is what makes a cold and a warm run
comparable; `load_duration` is reported in its own column instead of being folded in,
because an 18 s cold load would otherwise dominate a 10 s generation.

Controls in `tokrate.sh`, so the model is the only variable:

- **`temperature 0` and `seed 42`** — deterministic, and it removes sampling cost as a
  confound.
- **fixed `num_predict 256`** rather than letting each model stop where it likes. A
  chatty model would otherwise look slower purely by generating more, and a terse one
  would post a rate measured over a handful of tokens. *(Nemotron still stopped early
  on some rows — see 9.6.)*
- **three prompt sizes** — 0, 2000 and 20000 words — to separate "slow model" from
  "slow at long context". All three models turned out to be essentially flat, which is
  itself the finding: they are bandwidth-bound on weights, not on context.
- **the same filler text** as `needle-v2.sh`, so token counts stay comparable across
  every script in this directory.

### 9.3 Capability gates

**Tool calling** uses `../ollamaClaudeCode_v1/agentic-test.sh` **unmodified**. That
matters: it was written and validated against the incumbent, so reusing it verbatim
means a pass here is comparable to a pass there rather than to a fresh harness that
might be easier. It drives `/v1/messages` — the Anthropic-compatible endpoint Claude
Code actually speaks, not `/api/chat` — because the question is whether these models
work *as a Claude Code driver*, and the renderer/parser layer (§1c) is exactly what
that endpoint exercises. T1–T5 cover a single tool, selection among four, a multi-turn
exchange consuming a `tool_result`, parallel calls in one turn, and a nested
enum/array schema.

**Retrieval** uses `./needle-v2.sh`, not v1's built-in T6. A secret passphrase is
buried at the **midpoint** of generated filler prose — mid-document, because that is
where the half-window discard (§4) would silently eat it — and the model is asked for
the passphrase alone. Four depths: ~4k, 16k, 60k, 120k. Every row reports
`prompt_eval_count`, so a truncated prompt is visible rather than being scored as a
retrieval failure.

**Context truncation** uses `./cliff-probe.sh` against models *already on the box*, so
the result is a property of the **server**, not of either new model.

**Footprint scaling** uses `./kv-probe.sh`: build a variant at each `num_ctx`, load it,
read `size` and `size_vram` from `/api/ps`, delete it.

**Vision** posts a real screenshot (`../ollamaClaudeCode_v0/failingOutput.png`) and
checks the description against what is actually in the image.

**Reasoning effort** sweeps `think: false|low|medium|high|xhigh` on one fixed word
problem and records thinking length, answer length and wall time.

### 9.4 The exact commands that produced §7c

```shell
./idle.sh       --host 192.168.100.67
./tokrate.sh    --host 192.168.100.67 qwen3.6:35b-a3b-q4_K_M-agentic
./cliff-probe.sh --host 192.168.100.67 --port 11434 \
                 qwen3.6:27b-q4_K_M qwen3.6:27b-q4_K_M-ctx128k
./head2head.sh  --host 192.168.100.67 muse-glimmer:30b-ctx128k-agentic
./head2head.sh  --host 192.168.100.67 nemotron-3.5-lightning:30b-ctx256k-agentic
./kv-probe.sh   --host 192.168.100.67 --port 11434 \
                 --model nemotron-3.5-lightning:30b --ctxs "32768 131072 262144 524288"
```

Artefacts, all committed:

| file | contents |
|---|---|
| `results/tokrate.tsv` | every throughput row, machine-readable |
| `results/h2h-muse.log`, `results/h2h-nemotron.log` | full battery transcripts incl. the idle gate |
| `results/agentic/*.tsv`, `*.raw.jsonl` | tool gates, verdicts and raw responses |
| `results/needle-v2.log`, `*.raw.jsonl` | retrieval, with `prompt_eval_count` per row |
| `results/cliff-0.32.9-qwen.txt` | both truncation traps, incl. the 60k disambiguation |
| `results/kv-nemotron.txt` | the `num_ctx` footprint sweep |
| `results/vision-muse.txt`, `results/reasoning-effort.txt` | the two v1 could not test |
| `results/inventory-67.txt` | §10, regenerable |

### 9.5 Verifying against a claim rather than trusting the harness

Two checks kept the harness honest:

- **A known-good control.** The incumbent was re-measured first. It came back at
  **131.4 tok/s** against v1's **131.5** on the older runtime. Had that drifted, every
  other number this session would have been suspect and the comparison to the v1 corpus
  invalid.
- **A prediction made before the measurement.** §5 estimated Muse at 25–32 tok/s from
  bandwidth arithmetic, published before the server was reachable. It measured 27.9–28.9.
  The same method predicted q8_0 would spill and was **wrong** (§2b), so this is
  reported as one hit and one miss, not as a validated method.

### 9.6 Known limitations of this methodology

Stated because they bound how far the numbers should be pushed:

- **`num_predict 256` was not always reached.** Several rows stopped early (Nemotron at
  96 and 143 tokens, the incumbent at 78–108). The rates are still computed over what
  was generated, but a rate measured over ~80 tokens is noisier than one over 256.
- **Single run per cell.** No repeats, no error bars. The 3–4× gaps discussed here are
  far larger than plausible run-to-run variance, but two models within ~10% of each
  other could not be separated by this data.
- **One needle, one position.** The passphrase sits at the midpoint every time. This
  finds the half-window discard by construction, but it does **not** sweep depth, so it
  is not a full "needle in a haystack" grid.
- **`prompt_eval_duration` on tiny prompts is meaningless.** Nemotron's 3.2 tok/s
  prefill on a 29-token prompt is measurement floor, not a result.
- **Gates are not a session.** T1–T5 prove the protocol works. They say nothing about
  whether a model stays coherent over a multi-hour Claude Code run — the thing that
  actually decides day-to-day usability, and the reason the 8.0% SWE-bench figure in §5
  is worth remembering.
- **`-dflash` was not tested.** Each variant means another ~20 GB pull and another
  serialized battery. It remains the one untested variable with plausible upside.

---

## 10. Every model on `192.168.100.67`

Generated by the script embedded in §10.1; raw output in `results/inventory-67.txt`.
**23 tags** as of 2026-08-13 — the two `-agentic` variants of §11.5 were added after
this table was first written, and are listed in §11 rather than repeated here.

| model | size | params | quant | `num_ctx` | temp | `pp` | capabilities |
|---|---|---|---|---|---|---|---|
| `qwen3.6:27b-mtp-q8_0-ctx60k` | 29.98 GB | 27.3B | Q8_0 | 60000 | 0.6 | **1.5** | thinking, tools, vision |
| `qwen3.6:27b-mtp-q8_0-ctx128k` | 29.98 GB | 27.3B | Q8_0 | 131072 | 1 | **1.5** | thinking, tools, vision |
| `qwen3.6:27b-mtp-q8_0` | 29.98 GB | 27.3B | Q8_0 | *bare* | 1 | **1.5** | thinking, tools, vision |
| `qwen3.6:27b-q8_0-ctx60k` | 29.97 GB | 27.8B | Q8_0 | 60000 | 0.6 | **1.5** | thinking, tools, vision |
| `qwen3.6:27b-q8_0` | 29.97 GB | 27.8B | Q8_0 | *bare* | 1 | **1.5** | thinking, tools, vision |
| **`nemotron-3.5-lightning:30b-ctx256k-agentic`** | 25.43 GB | 32.9B | Q4_K_M | **262144** | **0** | **0** | thinking, tools |
| `nemotron-3.5-lightning:30b` | 25.43 GB | 32.9B | Q4_K_M | *bare* | 1 | — | thinking, tools |
| `qwen3.6:35b-a3b-q4_K_M-ctx128k` | 23.94 GB | 36.0B | Q4_K_M | 131072 | 1 | **1.5** | thinking, tools, vision |
| `qwen3.6:35b-a3b-q4_K_M-ctx256k` | 23.94 GB | 36.0B | Q4_K_M | 262144 | 1 | **1.5** | thinking, tools, vision |
| `qwen3.6:35b-a3b-q4_K_M-isot0` | 23.94 GB | 36.0B | Q4_K_M | 262144 | 0 | **1.5** | thinking, tools, vision |
| **`qwen3.6:35b-a3b-q4_K_M-agentic`** | 23.94 GB | 36.0B | Q4_K_M | **262144** | **0** | **0** | thinking, tools, vision |
| `qwen3.6:35b-a3b-q4_K_M-isopp0` | 23.94 GB | 36.0B | Q4_K_M | 262144 | 1 | 0 | thinking, tools, vision |
| `qwen3.6:35b-a3b-q4_K_M` | 23.94 GB | 36.0B | Q4_K_M | *bare* | 1 | **1.5** | thinking, tools, vision |
| `qwen3.6:35b-a3b-mtp-q4_K_M-ctx128k` | 22.62 GB | 35.5B | Q4_K_M | 131072 | 1 | **1.5** | thinking, tools, vision |
| `qwen3.6:35b-a3b-mtp-q4_K_M` | 22.62 GB | 35.5B | Q4_K_M | *bare* | 1 | **1.5** | thinking, tools, vision |
| **`muse-glimmer:30b-ctx128k-agentic`** | 18.16 GB | 27.9B | Q4_K_M | **131072** | **0** | **0** | thinking, tools, **vision** |
| `muse-glimmer:30b` | 18.16 GB | 27.9B | Q4_K_M | *bare* | 1 | — | thinking, tools, vision |
| `qwen3.6:27b-q4_K_M-ctx128k` | 17.42 GB | 27.8B | Q4_K_M | 131072 | 1 | **1.5** | thinking, tools, vision |
| `qwen3.6:27b-q4_K_M` | 17.42 GB | 27.8B | Q4_K_M | *bare* | 1 | **1.5** | thinking, tools, vision |
| `qwen3.5:9b-ctx80k` | 6.59 GB | 9.7B | Q4_K_M | 81920 | 1 | **1.5** | thinking, tools, vision |
| `qwen3.5:9b` | 6.59 GB | 9.7B | Q4_K_M | *bare* | 1 | **1.5** | thinking, tools, vision |

**15 of 23 tags carry a baked `num_ctx`; 8 are bare** and therefore subject to the
16,386-token cap of §4 whenever they are driven through `/v1/messages`.

Three things this table makes visible that a plain `ollama list` does not:

- **`presence_penalty 1.5` is on 15 of the 23 tags.** `review2.md` measured that
  vendor default costing **35–53% of throughput** on this hardware. Only the four
  `-agentic` / `-isopp0` variants clear it. **Prefer an `-agentic` tag for anything
  that generates a lot of tokens** — the difference is free.
- **Five tags are now fully tuned for agentic use** (`num_ctx` baked, `temperature 0`,
  `presence_penalty 0`): `qwen3.6:35b-a3b-q4_K_M-agentic`,
  `qwen3.6:35b-a3b-mtp-q4_K_M-agentic`, `qwen3.6:27b-q8_0-agentic`,
  `nemotron-3.5-lightning:30b-ctx256k-agentic` and `muse-glimmer:30b-ctx128k-agentic`.
  These are the five benchmarked in §11.
- **Nothing here is larger than ~34 GB resident, and the measured GPU ceiling is
  ≈35.5 GB** (§11.4) — so the real headroom is far thinner than the stated 40.4 GB
  suggests. The q8_0 tags sit closest to it: `qwen3.6:27b-q8_0-agentic` is at 34.03 GB
  and could not be given a window larger than 81,920 without spilling. That is exactly
  what §2b's throughput argument was about.

The `-isot0` and `-isopp0` tags are v1's **isolation variants** — one changes only
`temperature`, the other only `presence_penalty`, against the same base — which is how
review2.md attributed the 35–53% cost to `presence_penalty` specifically rather than to
"the agentic settings" as a bundle. Keep them; they are the control group.

### 10.1 Regenerating this table

```shell
curl -s http://192.168.100.67:11434/api/tags | python3 -c '
import sys,json
ms=json.load(sys.stdin)["models"]
for m in sorted(ms,key=lambda x:-x["size"]):
    d=m.get("details",{})
    print("%8.2f GB  %-46s %-7s %s"%(m["size"]/1e9,m["name"],
          d.get("parameter_size","?"),d.get("quantization_level","?")))'
```

The `num_ctx` / `temperature` / `presence_penalty` and capability columns need one
`POST /api/show` per tag — `results/inventory-67.txt` is the full output.

**Read-only, and deliberately so.** `ollamaFarm`'s `AGENTS.md` records `.67` as a
shared machine. Everything added this session is additive (`muse-glimmer:*`,
`nemotron-3.5-lightning:*`); no pre-existing tag was modified or removed, and the four
temporary `*-kvprobe-*` tags created by `kv-probe.sh` were deleted afterwards.

---

## 11. Five models, measured the same way — and three corrections

Added 2026-08-13. Two more models were tuned and put through the identical battery so
the comparison covers everything on `.67` worth considering as a Claude Code driver.
**Running them exposed three errors in the earlier sections of this document**, all of
which flattered the newer models. They are corrected below and at the source.

### 11.0 The chart

| | `qwen3.6:35b-a3b-q4_K_M` **-agentic** | `qwen3.6:35b-a3b-mtp-q4_K_M` **-agentic** | `qwen3.6:27b-q8_0` **-agentic** | `muse-glimmer:30b` **-ctx128k-agentic** | `nemotron-3.5-lightning:30b` **-ctx256k-agentic** |
|---|---|---|---|---|---|
| architecture | MoE, 3B active | MoE + MTP head | **dense** | **dense** | hybrid Mamba-2 + MoE |
| **generation** | **131.4 tok/s** | **129.0 tok/s** | 18.1 tok/s | 28.9 tok/s | 44.9 tok/s |
| **prefill** (35k) | **3,988 tok/s** | 3,369 tok/s | 1,464 tok/s | 1,963 tok/s | 3,050 tok/s |
| resident | 32.54 GB | **28.89 GB** | 34.03 GB | **19.45 GB** | 31.21 GB |
| GPU residency | 100% | 100% | 100% | 100% | 100% |
| **max `num_ctx` at 100% GPU** | 262144 | 262144 | **81920** | 131072 | **524288** |
| tool gates T1–T5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| **needle, 80k-word doc** | **PASS** @146,957 | **PASS** @146,957 | **FAIL** — window | **PASS** @114,487 | **PASS** @161,516 |
| vision | **yes** | yes | yes | yes | **no** |
| cold load | 11.6 s | 12.3 s | 14.2 s | 18.4 s | 18.2 s |

Every cell measured on `.67`, Ollama 0.32.9, server idle before each stage.

**The q8_0 "FAIL" is not a retrieval failure.** Its window is 81,920 and the prompt was
~147k tokens, so the overflow bug of §4 halved it: `prompt_eval = 40,962`, exactly half.
The needle was in the discarded half. Within its window it retrieves fine (72,419 at
the 60k depth). This is a **third independent confirmation** of trap 2, at a third
window size — 32768 → 16,387, 61440 → 30,002, 81920 → 40,962.

### 11.1 Correction 1 — the incumbent does *not* fail at 120k

§5 and §7c claimed the incumbent "fails at 120k". **That was wrong.** The figure came
from v1's `needle-retest.log`, which measured **`qwen3.6:27b-q4_K_M-ctx128k`** — a
different model, a different size, a different quant. I attributed it to the `35b-a3b`
MoE because both are "the qwen on `.67`".

Measured directly (`results/needle-incumbent.txt`), the incumbent **passes all four
depths, including 146,957 prompt tokens**. So the claim that "both newcomers beat it
at depth" is false and is withdrawn.

Worse for the newcomers, the token counts are not comparable across models. All four
passing models were given the **same 80,003-word document**; they merely tokenize it
differently:

| model | tokens for the same document |
|---|---|
| `qwen3.6` family | 146,957 |
| `muse-glimmer` | 114,487 *(and this is its ceiling — window is 131072)* |
| `nemotron` | 161,516 |

**Nemotron's 161,516 is not more retrieval, it is a less efficient tokenizer.** In
characters of real document, all four retrieved identically. The only honest ranking
here is by *window headroom*, where Nemotron genuinely leads (524288 at 100% GPU).

### 11.2 Correction 2 — vision is not unique to Muse Glimmer

§5 listed vision as something "nothing else on the farm" can do. **Every `qwen3.6` tag
on `.67` reports the `vision` capability**, which §10's inventory shows plainly and
which I did not act on when writing §5.

Tested head to head on the same screenshot (`results/vision-incumbent.txt`):

| | prompt tokens | generation | what it reported |
|---|---|---|---|
| `muse-glimmer` | 1,177 | 28.9 tok/s | "Konsole", read the window title |
| **incumbent** | **869** | **129.8 tok/s** | **"Claude Code v2.1.156"**, read the invoked command and its flag |

The incumbent is **4.5× faster at vision, uses fewer prompt tokens for the same image,
and extracted more from it.** Muse Glimmer's one remaining differentiator does not
survive contact with a measurement.

### 11.3 Correction 3 — what follows for Muse Glimmer

Combining the two corrections: against the incumbent, Muse Glimmer is **4.5× slower,
has half the context window, retrieves less document, and loses the vision comparison
it was recommended for.** Its `xhigh` reasoning level, the other pillar of the earlier
recommendation, is rejected by Ollama (§7c).

**There is no workload on this box where Muse Glimmer is the right choice.** It is a
capable model — 5/5 tool gates, real 128K retrieval — that happens to be outclassed by
what was already installed. Keeping it costs nothing but it should not be deployed, and
the §8 recommendation to reach for it "for anything with an image in the loop" is
withdrawn.

### 11.4 How the parameters for the two new models were chosen

Not assumed — measured, and in each case the shipped default lost.

**Context window: sweep until residency stops being 100%.** `./kv-probe.sh` at several
`num_ctx`, watching `size_vram / size`:

| `qwen3.6:27b-q8_0` | resident | GPU | | `qwen3.6:35b-a3b-mtp` | resident | GPU |
|---|---|---|---|---|---|---|
| 16384 | 29.67 GB | 100% | | 131072 | 26.15 GB | 100% |
| 32768 | 30.41 GB | 100% | | **262144** | **27.57 GB** | **100%** |
| 65536 | 32.82 GB | 100% | | *(262144 is the architectural max)* | | |
| **81920** | **34.03 GB** | **100%** | | | | |
| 98304 | 36.08 GB | **95%** | | | | |
| 131072 | 38.33 GB | **93%** | | | | |

So **81920** for the q8_0 — notably better than the 60000 the pre-existing `-ctx60k`
tag used — and the full **262144** for the MoE.

This sweep also yields the most useful number in this document for future planning:
**at `num_ctx=131072` the q8_0 asked for 38.33 GB and only 35.56 GB stayed on the GPU.
The usable ceiling is therefore ≈35.5 GB, not the 40.4 GB in ollamaFarm's table.** That
independently corroborates v1's "36.1 GB measured usable" and means roughly 5 GB of the
stated 40.4 is not spendable on a model.

**`draft_num_predict` — the MTP knob, and the shipped default is wrong.** The `-mtp`
tags carry a multi-token-prediction head for speculative decoding and ship
`draft_num_predict 4`. Four variants, identical but for that value, measured on an idle
server:

| `draft_num_predict` | generation | prefill (35k) | vs. off |
|---|---|---|---|
| **0 — off** | **129.2 tok/s** | **3,384 tok/s** | — |
| 2 | 105.1 tok/s | 1,958 tok/s | **−19%** |
| **4 — shipped default** | 100.6 tok/s | 1,950 tok/s | **−22%** |
| 8 | 58.9 tok/s | 1,945 tok/s | **−54%** |

**Speculative decoding is a net loss here at every setting, and the deeper the draft the
worse it gets.** It costs prefill too — nearly halved the moment it is enabled at all.
The plausible reading is that draft-token rejection dominates: on a 3B-active MoE the
target model is already cheap per token, so verifying speculative tokens costs more than
it saves. Whatever the cause, the measurement is unambiguous, so
`qwen3.6:35b-a3b-mtp-q4_K_M-agentic` bakes **`draft_num_predict 0`**.

With MTP off, the MTP tag is within noise of the plain incumbent (129.0 vs 131.4) while
using **3.65 GB less memory** (28.89 vs 32.54 GB) at the same 262144 window. That makes
it a mildly better default than the incumbent if memory is tight, and otherwise a wash.

**`presence_penalty 0` — re-verified rather than inherited.** v1 measured the vendor
default of 1.5 costing 35–53% of throughput. Re-run on 0.32.9, same base model, same
window, **only `presence_penalty` differing**:

| prompt | `pp 0` | `pp 1.5` | cost |
|---|---|---|---|
| 25 tok | 124.5 tok/s | 81.2 tok/s | **−35%** |
| 3,180 tok | 129.2 tok/s | 85.3 tok/s | **−34%** |
| 35,102 tok | 111.8 tok/s | 77.2 tok/s | **−31%** |

**Confirmed at the low end of v1's range: 31–35%.** Since 15 of the 21 tags on `.67`
carry `presence_penalty 1.5` (§10), this is the single cheapest performance win
available on that server.

**`temperature 0`** is carried over from v1 on reliability grounds (it fixed run-to-run
gate flapping) rather than speed; the table above shows it is not a throughput factor.

### 11.5 The two new deployable tags

```shell
# MoE + MTP head, with MTP disabled because it costs 22%
curl -X POST http://192.168.100.67:11434/api/create -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.6:35b-a3b-mtp-q4_K_M-agentic","from":"qwen3.6:35b-a3b-mtp-q4_K_M",
       "parameters":{"num_ctx":262144,"temperature":0,"presence_penalty":0,
                     "draft_num_predict":0},"stream":false}'

# dense q8_0, window sized to the measured 100%-GPU ceiling
curl -X POST http://192.168.100.67:11434/api/create -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.6:27b-q8_0-agentic","from":"qwen3.6:27b-q8_0",
       "parameters":{"num_ctx":81920,"temperature":0,"presence_penalty":0},"stream":false}'
```

### 11.6 Revised recommendation

1. **`qwen3.6:35b-a3b-mtp-q4_K_M-agentic`** — new default. 129.0 tok/s, full 262144
   window, 3.65 GB lighter than the incumbent, vision, 5/5 gates.
2. **`qwen3.6:35b-a3b-q4_K_M-agentic`** — the incumbent, 131.4 tok/s. Interchangeable
   with the above; pick it if you would rather not depend on a `draft_num_predict 0`
   override being respected.
3. **`nemotron-3.5-lightning:30b-ctx256k-agentic`** — only when the working set exceeds
   262144 tokens. It is the sole model that stays 100% GPU-resident at 524288, and that
   is now its *only* advantage: at 44.9 tok/s it is 2.9× slower than the default, and
   its deeper needle result was a tokenizer artifact, not better retrieval.
4. **`qwen3.6:27b-q8_0-agentic`** — only to check whether a q8 quant fixes a specific
   quality problem. At 18.1 tok/s and a 81,920 window it is the slowest and most
   constrained option, exactly as `fitting_models.md` predicted for dense + q8 on this
   hardware. §2b's argument is confirmed by direct measurement.
5. **`muse-glimmer:30b-ctx128k-agentic`** — not recommended (§11.3).
