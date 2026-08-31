# Qwen3-VL 32B vision and OCR on the 40 GB Ollama server

Measured on a 40 GB-class server on 2026-08-31 with Ollama `0.32.15`. The preceding v3
study measured about **35.56 GB usable VRAM**.
The model pulled for this run is exactly `qwen3-vl:32b`: 33.4B parameters, Q4_K_M,
20 GB on disk, 262,144 native context, with completion, vision, tools, and thinking
capabilities.

## Verdict

**Yes, it does OCR and useful image descriptions.** With Qwen's explicit `/no_think`
directive it transcribed the controlled invoice with **9/9 exact fields**, described every
labeled UI control, and extracted all five chart values.
Decode throughput was **25.5–26.6 tok/s**.

The important operational finding is that Ollama `think:false` is ignored for this tag. Without
`/no_think`, requests could spend the full output budget in hidden reasoning and return an
empty answer. The invoice still returned no answer after raising the budget to
4,096 tokens. `/no_think` in the user prompt fixed it immediately: 636 generated tokens,
26.6 seconds, exact OCR.

## Results

The curated measurements are in [`results/benchmark-summary.tsv`](results/benchmark-summary.tsv).

| image | objective checks | wall | prompt tokens | generated | decode |
|---|---:|---:|---:|---:|---:|
| controlled invoice OCR | 9/9 | 26.6 s | 1,106 | 636 | 26.54 tok/s |
| embedded UI screenshot | 6/6 | 33.0 s | 1,097 | 846 | 26.41 tok/s |
| expense treemap | 10/10 | 25.4 s | 4,109 | 613 | 25.48 tok/s |

What it saw:

- The invoice transcription preserved the identifier, date, customer, item names, quantities,
  all prices, VAT, total, payment term, and `VISION-7Q4K-92` reference.
- The embedded UI description identified the LVGL Simulator, green Accept, red Cancel, blue
  Config, `total clicks: 8`, and the slider position.
- The treemap extracted Rent €1200, Food €1000, Kids €900, Car €200, and Clothes €100, and
  correctly explained that rectangle area encodes expense size.

Raw responses are deliberately excluded: the committed result is the aggregate measurement,
not prompts, local paths, screenshots, or server addresses.

## Maximum context for image OCR

The base tag advertises 262K but defaults to 32K when loaded. Context was increased in 1K
rungs around the GPU boundary and tested with a real image, not merely a text-only load.

| baked context | result with image | residency | conclusion |
|---:|---|---:|---|
| 49,152 | OCR 9/9 | 34.47 GB, 100% GPU | works |
| **50,176** | **OCR 9/9** | **34.76 GB, 100% GPU** | **maximum verified OCR rung** |
| 51,200 | HTTP 500 | — | vision workspace no longer fits |
| 52,224 | HTTP 500 | — | fails |
| 53,248 | HTTP 500 | 35.61 GB text-only | loading is not enough; image fails |
| 54,272 | not run | 36.92 GB total / 34.55 GB GPU | CPU spill, rejected |

The installed OCR model is therefore `qwen3-vl:32b-ctx49k`, built from
[`Modelfile-qwen3-vl-32b-ctx49k`](Modelfile-qwen3-vl-32b-ctx49k). The shell cap is 45,000,
leaving 5,176 tokens for the answer below the baked 50,176-token window. Full probe data is in
[`results/context-probe.tsv`](results/context-probe.tsv).

## Shell command

`claude-vision` is defined in [`claude-vision.zsh`](claude-vision.zsh) and sourced by `~/.zshrc`.
It pre-warms the 49K model for two
hours, pins all Claude model slots to the same Ollama tag, uses a compact OCR-specific system
prompt, disables coding tools, and routes Anthropic requests through
[`anthropic_no_think_proxy.py`](anthropic_no_think_proxy.py). The proxy removes Claude-specific
coding scaffolding and injects `/no_think` into actual user turns, including image-only turns.
Set the server only in your local shell configuration, then start a new shell or run:

```shell
export OLLAMA_VISION_HOST=http://your-ollama-host:11434
source claude-vision.zsh
claude-vision
```

Direct `/api/chat` image requests with `/no_think` are verified at 25–40 seconds. A raw
Anthropic-format image request through the compatibility proxy also completed correctly in
20 seconds. The original direct Claude Code alias is explicitly rejected: a real image-only
session repeated its internal transcription until it hit 2,048 tokens four times. The latest
proxy sanitization is preserved here but has not yet passed a complete interactive Claude Code
image-paste run, so this integration must not be represented as fully verified.

## How this follows the earlier benchmarks

The repository history shows a clear progression:

- `ollamaClaudeCode_v0`: throughput on the smaller `.37` server; vision models were skipped.
- `v1`: added agentic tool gates, context/KV probes, needle retrieval, and the first `.67`
  matrix.
- `v2`: added a reproducible vision stage using `failingOutput.png`, plus guarded idle checks,
  throughput, context, tool use, and end-to-end comparisons.
- `v3_qwen3.8`: required an idle server and one resident model, recorded runtime versions,
  separated load/prefill/decode time, measured VRAM and usable context, ran T1–T7 tool gates,
  real vision, needle retrieval, and a scored Claude Code fixture.

The most relevant commits are `7246777` (first v2 vision benchmark), `8f75f84` (head-to-head
vision correction), `f3a2b1b` (Qwen3.8 plus the Ollama 0.32.15 re-ranking), `b48ed59`
(35.56 GB ceiling), `b43c361` (end-to-end turn economy), and `3cff7e9` (all Claude model slots
wired in shell functions).

Other `codingWithGPT` directories containing “ollama” cover generated-code trials
(`ollamaClaudeCodeTest*`, `ollamaNemotron3.5LightningTest*`, `ollama_northmini_jumpNRun`),
image generation (`ollamaImageGen`), host discovery (`ollamaScanner`), and the v0–v3 benchmark
line above. Only the v0–v3 line supplied the methodology for this run.

## Reproduce

```shell
export OLLAMA_HOST="$OLLAMA_VISION_HOST"
ollama pull qwen3-vl:32b
ollama create qwen3-vl:32b-ctx49k -f Modelfile-qwen3-vl-32b-ctx49k
./benchmark_vision.py --model qwen3-vl:32b
./benchmark_vision.py --model qwen3-vl:32b-ctx49k --case ocr-invoice
```

The three synthetic/generic fixtures are checked into `fixtures/`; `ocr-invoice.svg` is the ground-truth source
for the generated PNG.
