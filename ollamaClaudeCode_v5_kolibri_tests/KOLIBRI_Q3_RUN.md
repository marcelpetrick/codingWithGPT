# Kolibri Q3 experiment

Version: 0.2.21. Started: 2026-11-04.

## Verdict

Kolibri Q3_K_S runs on Ollama 0.40.11. The highest tested full-GPU context is 147,456 tokens. At 148,480 tokens, the server reports a spill. Retrieval passed at 74,239 prompt tokens. The stock and corrected templates both failed the first tool-call reliability gate.

## Plan and decision rules

1. Record the candidate, server and rules. Estimate: 10 minutes.
2. Pull Q3_K_S through the existing Ollama API. Estimate: download dependent.
3. Test one request at 4,096 tokens. Stop if the server is busy, unavailable or the model fails.
4. Measure GPU residency at increasing contexts. Record `size` and `size_vram` from `/api/ps`.
5. Find the highest tested fully resident context. A spill is `size_vram < size`. After a spill, bisect the interval at 1,024-token resolution. If 4,096 spills, test 2,048 before declaring failure.
6. Verify retrieval at the chosen context. Allocation alone does not prove usable context.
7. Run v4 tool gates and three easy and three hard Claude Code sessions if the model and template support them. Compare against the v4 control measured in the same session. Keep T1–T5 unchanged. Run long-context gates only when their actual prompt fits. Label scaled probes separately. Measure cold prefill, generation and warm cache behavior.
8. Review findings and record limits. Do not restart or upgrade the shared server.

A result requires a completed request and a nonempty response. Use one request at a time. Record the runtime version and model digest. Stop on a foreign resident model. Unload only a model this experiment loaded. A failed load is not a VRAM measurement. Treat gate failures as systematic only when at least 3 of 8 reruns fail. Report three-run medians and ranges for timing. Use the v4 control in the same session before making comparisons.

## Candidate register, 2026-11-04

| Class | Candidate | Evidence |
| --- | --- | --- |
| Testable | Eliasfpv28 Q3_K_S, 33,870,242,400 bytes | [Model card](https://huggingface.co/Eliasfpv28/Kolibri-1-Q3_K_S-GGUF), revision `3003c47b0d4c47fae0c40f645397b456b50d8931`. Published full-file SHA-256: `26ce4a2f618e3d55d401faaa78bb144057268b8303e645b6e3d552258d1d34aa`. The publisher tested 4,096 tokens on a patched runtime. |
| Known but not fitting | Hob-forge Q3_K_M, approximately 37.5 GB | [Model card](https://huggingface.co/Hob-forge/Kolibri-1-GGUF). We previously measured about 35.56 GB usable VRAM. |
| Blocked | Patched standalone runtime on the server | Shell access is denied. Recheck if the admin supplies an isolated runtime or access. |

The publisher later reported a 32,768-token configuration on two GPUs with a Q8 KV cache. The publisher did not validate full 32k inputs. The same note says its original source revision cannot be resolved. See [LOCAL-RUNTIME.md](https://huggingface.co/Eliasfpv28/Kolibri-1-Q3_K_S-GGUF/blob/3003c47b0d4c47fae0c40f645397b456b50d8931/LOCAL-RUNTIME.md). This evidence does not prove a fit or quality on our server.

The model card's Ollama warning predates upstream support. [Ollama 0.40.11 pins llama.cpp b11845](https://github.com/ollama/ollama/blob/v0.40.11/LLAMA_CPP_VERSION). [That revision registers `kolibri1`](https://github.com/ggml-org/llama.cpp/blob/b11845/src/llama-arch.cpp). This is source evidence, not a successful load.

## Status

| Time, Europe/Berlin | Step | Result |
| --- | --- | --- |
| 2026-11-04 12:56 | Server preflight | `/api/version` returned 0.40.11. `/api/ps` returned no resident models. |
| 2026-11-04 12:56 | Shell access | SSH denied for `mpetrick`. The API remains reachable. |
| 2026-11-04 12:57 | Compatibility | Upstream Kolibri support is present in Ollama's pinned llama.cpp source. A model load is still needed. |

| 2026-11-04 12:58 | Pull | The server accepted the Q3_K_S pull. The digest matches the published checksum. |
| 2026-11-04 12:59 | Residency | A detached chain waits on the pull lock before running the context ladder. |
| 2026-11-04 13:18 | Pull | Ollama verified the weight digest and registered the model. It reports completion, tools and thinking capabilities. |
| 2026-11-04 13:19 | First loads | 4,096 and 8,192 tokens ran fully on GPU. Both outputs included 391 but stopped at the 128-token limit. |
| 2026-11-04 13:22 | Context search | 147,456 tokens used 35,336,382,052 GPU bytes. At 148,480, `size_vram < size`. Full results: `measurements/`. |

## Pull script

`pull-model.sh` checks the server version and idle state, then pulls the Q3_K_S tag. It skips an existing tag. It writes streaming progress to standard output and uses `results/pull.lock` to prevent duplicate local runs. It sends a desktop notification at exit.

## Residency script

`after-pull.sh` waits for the pull lock, then starts `residency.py`. The probe checks server version, tag, idle state and response completeness. It records each completed rung in `results/residency.jsonl`. It resumes only when recorded contexts, model digest and server version match. It stops at the first spill or error. It unloads only its exact model tag. The ladder establishes a tested floor, not an exact maximum or verified retrieval depth.

`after-residency.sh` waits for the ladder lock and runs `refine.py`. The refinement requires a completed ladder. It records its own results and resumes only matching runs.

## Retrieval results

The corrected-template arm retrieved the v4 needle at 4,536, 18,349 and 74,239 reported prompt tokens. The 80,000-word request returned only 73,730 prompt tokens at a 147,456-token allocation. This indicates overflow and half-window truncation. Do not score that trial as a model failure. Rerun at a smaller input. The raw responses and log are in `measurements/`.

## Template investigation

The stock Ollama template always appends `<think>`, even when thinking is disabled. The [official tokenizer template](https://huggingface.co/Aleph-Alpha/Kolibri-1/blob/main/tokenizer_config.json) instead closes the thinking block for disabled thinking. `templates/kolibri-no-think.gotmpl` changes only that generation prefix. It is an experimental A/B arm based on the installed Ollama template. It does not yet implement every detail of the official template. Keep its results separate from the stock template.

The stock-template T1 smoke returned no tool call. The first corrected-template trial returned `content: null` and crashed the v4 scorer before it saved the response. A second identical request returned the correct `write_file` call. The stock template passed 2 of 8 T1 trials. The corrected template passed 1 of 8 T1 trials. Six returned null content. One emitted nested tool arguments. This exceeds the pre-registered 3-of-8 failure threshold for this configuration. It does not identify whether the cause is the model, parser or template. Raw responses are in `measurements/`.

## Agentic smoke test

`agentic-smoke.sh` copies the v4 T1 gate into the results directory and runs it once. It checks server version, idle state, residency and context. The single trial is a smoke test, not a reliability score.

`gate-reliability.sh` repeats T1 eight times. It patches the copied v4 scorer to handle `content: null`. The request and scoring conditions otherwise stay the same. Apply the pre-registered 3-of-8 failure threshold instead of the copied summary label.

`needle-probe.sh` runs the v4 retrieval ladder on the corrected-template arm. It preserves the prompts and adds fail-fast checks for transport errors and empty answers.

`speed-probe.sh` runs v4 throughput prompts for Kolibri and the same-session Qwen control. It alternates models and unloads each after a sample. It saves raw responses and stops on errors, empty answers or spills. It takes three cold samples per prompt size and model.

`near-limit.sh` waits for all 18 speed samples and retries retrieval at 60,000 and 70,000 words. Compare the reported prompt token counts with the 147,456-token allocation before scoring.

`agentic-battery.sh` runs v4 gates T2, T4, T5 and T8–T11 three times on each model. It patches the copied scorer for null content and stops on reported transport errors. T3 and T7 remain separate tests.

`coding-bench.sh` runs three easy and three hard Claude Code sessions per model in the existing v4 sandbox image. Both models use the same 147,456-token client limit. The copied harness checks sandbox egress and refuses a missing working tree. The sandbox CLI version differs from the host; compare only the two sandbox arms.

## Resume here

Work in `ollamaClaudeCode_v5_kolibri_tests`. Confirm the server is idle before any run:

```sh
curl --noproxy '*' -fsS http://192.168.100.67:11434/api/version
curl --noproxy '*' -fsS http://192.168.100.67:11434/api/ps
```

Use the v4 harness at `../ollamaClaudeCode_v4_tielCoder/` after confirming model support. Never evict a foreign model. Preserve the user's untracked `vision.md` and unrelated repository changes.
