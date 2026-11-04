# Kolibri Q3 experiment

Version: 0.1.3. Started: 2026-11-04.

## Verdict

Ollama 0.40.11 includes upstream Kolibri architecture support. The actual model fit and output are not yet measured.

## Plan and decision rules

1. Record the candidate, server and rules. Estimate: 10 minutes.
2. Pull Q3_K_S through the existing Ollama API. Estimate: download dependent.
3. Test one request at 4,096 tokens. Stop if the server is busy, unavailable or the model fails.
4. Measure GPU residency at increasing contexts. Record `size` and `size_vram` from `/api/ps`.
5. Find the highest tested fully resident context. A spill is `size_vram < size`.
6. Verify retrieval at the chosen context. Allocation alone does not prove usable context.
7. Run v4 tool gates and coding sessions if the model and template support them.
8. Review findings and record limits. Do not restart or upgrade the shared server.

A result requires a completed request and a nonempty response. Use one request at a time. Record the runtime version and model digest. Stop on a foreign resident model. Unload only a model this experiment loaded. A failed load is not a VRAM measurement. Treat gate failures as systematic only when at least 3 of 8 reruns fail. Report three-run medians and ranges for timing. Use the v4 control in the same session before making comparisons.

## Candidate register, 2026-11-04

| Class | Candidate | Evidence |
| --- | --- | --- |
| Testable | Eliasfpv28 Q3_K_S, 33,870,242,400 bytes | [Model card](https://huggingface.co/Eliasfpv28/Kolibri-1-Q3_K_S-GGUF), revision `3003c47b0d4c47fae0c40f645397b456b50d8931`. Published full-file SHA-256: `26ce4a2f618e3d55d401faaa78bb144057268b8303e645b6e3d552258d1d34aa`. The publisher tested 4,096 tokens on a patched runtime. |
| Known but not fitting | Hob-forge Q3_K_M, approximately 37.5 GB | [Model card](https://huggingface.co/Hob-forge/Kolibri-1-GGUF). We previously measured about 35.56 GB usable VRAM. |
| Blocked | Patched standalone runtime on the server | Shell access is denied. Recheck if the admin supplies an isolated runtime or access. |

The model card's Ollama warning predates upstream support. [Ollama 0.40.11 pins llama.cpp b11845](https://github.com/ollama/ollama/blob/v0.40.11/LLAMA_CPP_VERSION). [That revision registers `kolibri1`](https://github.com/ggml-org/llama.cpp/blob/b11845/src/llama-arch.cpp). This is source evidence, not a successful load.

## Status

| Time, Europe/Berlin | Step | Result |
| --- | --- | --- |
| 2026-11-04 12:56 | Server preflight | `/api/version` returned 0.40.11. `/api/ps` returned no resident models. |
| 2026-11-04 12:56 | Shell access | SSH denied for `mpetrick`. The API remains reachable. |
| 2026-11-04 12:57 | Compatibility | Upstream Kolibri support is present in Ollama's pinned llama.cpp source. A model load is still needed. |

| 2026-11-04 12:58 | Pull | The server accepted the Q3_K_S pull. The digest matches the published checksum. |
| 2026-11-04 12:59 | Residency | A detached chain waits on the pull lock before running the context ladder. |

## Pull script

`pull-model.sh` checks the server version and idle state, then pulls the Q3_K_S tag. It skips an existing tag. It writes streaming progress to standard output and uses `results/pull.lock` to prevent duplicate local runs. It sends a desktop notification at exit.

## Residency script

`after-pull.sh` waits for the pull lock, then starts `residency.py`. The probe checks server version, tag, idle state and response completeness. It records each completed rung in `results/residency.jsonl`. It stops at the first spill or error. It unloads only its exact model tag. The ladder establishes a tested floor, not an exact maximum or verified retrieval depth.

## Resume here

Work in `ollamaClaudeCode_v5_kolibri_tests`. Confirm the server is idle before any run:

```sh
curl --noproxy '*' -fsS http://192.168.100.67:11434/api/version
curl --noproxy '*' -fsS http://192.168.100.67:11434/api/ps
```

Use the v4 harness at `../ollamaClaudeCode_v4_tielCoder/` after confirming model support. Never evict a foreign model. Preserve the user's untracked `vision.md` and unrelated repository changes.
