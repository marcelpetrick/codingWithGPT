# Kolibri Q3 experiment

Version: 0.3.16. Started: 2026-11-04.

## Verdict

Kolibri Q3_K_S runs on Ollama 0.40.11. The highest tested full-GPU context is 147,456 tokens. At 148,480 tokens, the server reports a spill. Retrieval passed at 131,506 prompt tokens. The stock template failed the first tool-call gate. The corrected-template gate is unresolved because six API responses were empty.

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

## Cold throughput

Ollama 0.40.11, 2026-11-04. Each row is median and range for three cold samples. The v4 prompts, seed 42 and temperature 0 are used. Kolibri uses a 147,456-token tag. The control uses its 262,144-token tag. This difference is a deployment confound.

| Prompt words | Model | Generation tokens/s, median [range] | Prefill tokens/s, median [range] |
| --- | --- | --- | --- |
| 0 | Kolibri Q3_K_S | 107.38 [105.99, 107.57] | 108.1 [103.0, 109.0] |
| 0 | Qwen 3.6 control | 124.59 [124.54, 125.69] | 69.1 [61.3, 72.7] |
| 2,000 | Kolibri Q3_K_S | 107.26 [106.51, 107.97] | 2,222.2 [2,221.8, 2,251.5] |
| 2,000 | Qwen 3.6 control | 127.75 [122.53, 129.56] | 2,894.8 [2,800.7, 2,916.1] |
| 20,000 | Kolibri Q3_K_S | 97.01 [96.66, 97.14] | 2,919.4 [2,915.0, 2,922.8] |
| 20,000 | Qwen 3.6 control | 110.08 [109.58, 112.0] | 4,762.7 [4,730.7, 4,764.0] |

Short prefill rates use only about 25 prompt tokens and are noisy. The output lengths vary because models can stop before the 256-token limit. Raw responses and rows are in `measurements/`. Model digests and client versions are in `measurements/provenance.json`.

## Retrieval results

The corrected-template arm retrieved the v4 needle at 4,536, 18,349 and 74,239 reported prompt tokens. The 80,000-word request returned only 73,730 prompt tokens at a 147,456-token allocation. This indicates overflow and half-window truncation. Do not score that trial as a model failure. The default probe now rejects inputs above the calibrated 70,000-word limit and checks the model digest. The smaller rerun passed at 112,417 and 131,506 prompt tokens. The raw responses and logs are in `measurements/`.

## Coding results

The sandbox used Claude Code 2.1.274 and a 147,456-token client limit for both models. All three easy runs passed for both models. Kolibri took 101, 117 and 208 seconds. Qwen took 27, 28 and 30 seconds.

Kolibri passed 18/18 held-out tests in all three hard runs. Its times were 389, 483 and 809 seconds. Qwen passed 16/18, 15/18 and 16/18. Its times were 48, 48 and 62 seconds. These are three runs of one Python fixture, not a general coding ranking. The first Kolibri easy row has a documented rescore.

The full v4 T3/T7 stage stopped on empty API content in its first request. The raw response is in `measurements/deep-empty-response.jsonl`. No T3 or T7 score was recorded. The later independent checks were held pending diagnosis.

## Agentic gates

The corrected-template Kolibri arm and the Qwen control each passed 3/3 trials for T2, T4, T5, T8, T9 and T11. Kolibri passed 0/3 T10 argument-fidelity trials. The control passed 3/3. The Kolibri failures need eight reruns and raw response inspection before classification. T1 produced one pass and one malformed call among two scoreable corrected-template responses. Six empty responses are invalid. The extra-gate log records verdicts and details, not complete responses. Coding sessions are running in the sandbox.

The corrected-template T1 test continued after empty API content. That violated the fail-fast rule. Its six empty responses are retained as invalid, not as model failures. The copied scorers now save the raw response and stop on empty content.

## English and German smoke checks

Both models returned the exact answer for all three English and three German arithmetic prompts. These six simple prompts do not establish general language or reasoning quality. Raw responses are in `measurements/bilingual.jsonl`.

## Template investigation

The stock Ollama template always appends `<think>`, even when thinking is disabled. The [official tokenizer template](https://huggingface.co/Aleph-Alpha/Kolibri-1/blob/main/tokenizer_config.json) instead closes the thinking block for disabled thinking. `templates/kolibri-no-think.gotmpl` changes only that generation prefix. It is an experimental A/B arm based on the installed Ollama template. It does not yet implement every detail of the official template. Keep its results separate from the stock template.

The stock-template T1 smoke returned no tool call. The first corrected-template trial returned `content: null` and crashed the v4 scorer before it saved the response. A second identical request returned the correct `write_file` call. The stock template passed 2 of 8 T1 trials. The corrected template returned one valid call, one malformed call and six null-content responses. The six empty responses are invalid under the run rules. The original wrapper incorrectly continued and labeled them failures. The model gate is therefore unresolved. The cause may be the model, parser or template. Raw responses are in `measurements/`.

## Agentic smoke test

`agentic-smoke.sh` copies the v4 T1 gate into the results directory and runs it once. It checks server version, idle state, residency and context. The single trial is a smoke test, not a reliability score.

`gate-reliability.sh` repeats T1 eight times. It patches the copied v4 scorer to stop and save the raw response when content is empty. The request and scoring conditions otherwise stay the same. Apply the pre-registered 3-of-8 failure threshold instead of the copied summary label.

`needle-probe.sh` runs the v4 retrieval ladder on the corrected-template arm. It preserves the prompts and adds fail-fast checks for transport errors and empty answers.

`speed-probe.sh` runs v4 throughput prompts for Kolibri and the same-session Qwen control. It alternates models and unloads each after a sample. It saves raw responses and stops on errors, empty answers or spills. It takes three cold samples per prompt size and model.

`near-limit.sh` waits for all 18 speed samples and retries retrieval at 60,000 and 70,000 words. Compare the reported prompt token counts with the 147,456-token allocation before scoring.

`agentic-battery.sh` runs v4 gates T2, T4, T5 and T8–T11 three times on each model. It patches the copied scorer for null content and stops on reported transport errors. T3 and T7 remain separate tests.

`coding-bench.sh` runs three easy and three hard Claude Code sessions per model in the existing v4 sandbox image. Both models use the same 147,456-token client limit. The copied harness checks sandbox egress and refuses a missing working tree. The sandbox CLI version differs from the host; compare only the two sandbox arms. The first session committed its changes. The original v4 scorer compares with current `HEAD` and can miss committed edits. Subsequent sessions use the fixture root commit as the baseline. The first session was re-scored from its saved tree. It changed only `stats.py` and passed all four tests. The corrected verdict is PASS. See `measurements/easy-run1-rescore.txt`.

`deep-probe.sh` runs v4 T3 and T7 once per model after the coding stage. T7 itself repeats three times. The copied harness omits retrieval, already measured separately. It rejects malformed responses and uses safe scorer parsing instead of `eval`. A T7 prompt must report at least 40,000 tokens. Rerun any failure eight times before classification.

`fidelity-retry.sh` waits for the deep gates and reruns T10 eight times. It saves each request and complete response for diagnosis.

`thinking-retry.sh` repeats T1 eight times with adaptive thinking. It labels this A/B arm separately from the disabled-thinking gate.

The first control hard run produced a saved tree with 16/18 hidden tests. Strict shell mode stopped the scorer before it saved a timing row. This incomplete run is retained separately and repeated. The resume logic skips recorded sessions.

`dashboard.html` is generated by `make_dashboard.py` from measurement files and the v4 history. `dashboard_watch.py` copies completed coding rows and regenerates it on file events. Firefox reloads the page every 60 seconds.

`bilingual-probe.sh` waits for adaptive-thinking tests. It then runs three paired English and German arithmetic prompts per model. After the empty deep-gate response was examined, `after-raw` resumes this independent stage. These are smoke checks, not a broad language-quality benchmark.

`reasoning-arm.sh` tests one further template change after the bilingual stage. It adds the official disabled-reasoning instruction to the corrected-template system message. It repeats T1 eight times and keeps this arm separate. The first API response had null content, so this arm stopped without a score. The raw response is in `measurements/reason-effort-t1.jsonl`. Three or more scoreable failures would be systematic.

`raw-diagnostic.sh` tests one T1-shaped prompt using `/api/generate` with `raw: true`. The manually rendered prompt approximates the corrected template; it is a diagnostic arm, not a score comparable to T1. It saves the request and response. This diagnostic returned a correctly shaped `write_file` call. The prompt and sampling differ from T1, so it does not isolate the cause of the empty API responses.

`native-tool-probe.sh` checks one T1-shaped request through `/api/chat` at temperature zero. This is a diagnostic, not a reliability score. The native chat request returned empty content without a tool call. It is invalid under the run rules. The request and response are in `measurements/`. Raw generation produced a tool call, but its manually rendered prompt was not identical.

## Resume here

Work in `ollamaClaudeCode_v5_kolibri_tests`. Confirm the server is idle before any run:

```sh
curl --noproxy '*' -fsS http://192.168.100.67:11434/api/version
curl --noproxy '*' -fsS http://192.168.100.67:11434/api/ps
```

The model tag is `kolibri1:q3ks-ctx147456-nothink-ab`. The coding benchmark is resumable and skips recorded sessions. After checking the logs and confirming the server is idle, restart it with:

```sh
setsid nohup systemd-inhibit --what=sleep:idle ./coding-bench.sh >>results/coding.log 2>&1 </dev/null & disown
```

Check `results/coding.log`, `results/deep.log`, `results/fidelity.log`, `results/thinking.log` and `results/dashboard-watch.log`. Do not restart downstream stages until their prior stage finishes. Inspect partial results before restarting a stage that refuses existing output. Never evict a foreign model. Preserve unrelated repository changes.
