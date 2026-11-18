# v6: Qwen3.8-27B "pi-adapted" on the Ollama box

This file is the living document of the task. It holds the verdict, the plan, the status and the
"Resume here" section.

## Verdict so far

Not measured yet.

## The task

The owner wants to use [`harness-hub/Qwen3.8-27B-pi-adapted`](https://huggingface.co/harness-hub/Qwen3.8-27B-pi-adapted)
with Claude Code. It must start with the shell alias `claude-ol-qwen3.8_27b_pi`.

1. Get the model to run on `192.168.100.67` (Ollama 0.40.11).
2. Measure it with the round 11-02 harness (`../ollamaClaudeCode_v4_tielCoder/s15-refresh.sh`).
3. Check if its capabilities fit the owner's work: agentic Qt/C++, Python, GitLab and long summaries.
4. Tell the owner if they should use it.

## What the model is (pre-evaluation, 2026-11-18)

| item | fact | source |
|---|---|---|
| type | a LoRA adapter (r 32, alpha 64, all projections), trained with RL (AsyncGRPO) | card |
| base | `Qwen/Qwen3.8-27B`, dense 27.3B, hybrid (1 attention layer in 4, the rest SSM) | card, `/api/show` of the base on the box |
| GGUF | `harness-hub/Qwen3.8-27B-pi-GGUF`, `Qwen3.8-27B-pi-lora-F16.gguf`, 318,802,304 bytes, sha256 `a64f9184…2d7b67` (matches the HF LFS oid) | HF API |
| trained for | the pi agent, OpenAI chat completions, **thinking off**, temperature 0.8, up to 50 steps | card |
| claims | Terminal-Bench 2.1: 39.5% → 55.8%; SWE-bench Pro (hard 51): 29.4% → 62.7%; one attempt per task | card. Vendor claims. The checkpoint was selected on SWE-bench Pro and a TB subset |
| caveats | trained on BF16; "lower-bit quants drift further"; the GGUF path "has not been re-evaluated"; Q8_0 base suggested | card |
| age | published about 1 day ago; 3 community threads, none about GGUF, Ollama or bugs | HF discussions |
| base on the box | `qwen3.8:27b-q4_K_M` (17.7 GB), renderer `qwen3.8`, parser `qwen3.5`. v3 measured it at 30 tok/s, 4.3× slower than the MoE field | `../ollamaClaudeCode_v3_qwen3.8/README.md` |

The reference result is the base model. The adapter is worth using only if it beats the base and
is near the current default `claude-ol-kat` (KAT-Coder-V2.5-Dev).

## Plan

| step | what | est. | status |
|---|---|---|---|
| P0 | pre-evaluate the card, write the plan and the red team, fix the rule | 20 min | done 10:47 |
| P1 | load the LoRA with `ADAPTER` | 10 min | **failed**: Ollama 0.40.11 says "LoRA adapters are no longer supported" |
| P1b | merge it ourselves: Q8_0 base + LoRA, in place (`merge_lora_inplace.py`), then Q4_K_M; build the base arm the same way (`build.sh`) | ~1 h | running |
| P2 | prove that the adapter is active: greedy output of pi and base must differ | 10 min | |
| P3 | thinking off: renderer `qwen3.8` + parser `qwen3-coder`, no custom template | 30 min | done 11:16: byte-identical to Ollama's renderer at think=false (`render_check.py`). A first Go-template attempt was wrong, see the status table |
| P4 | smoke: residency 100% GPU, tool calls, `think_chars = 0`, one Claude Code turn through the alias | 20 min | alias written to `~/.zshrc` |
| P5 | measure: `v6-run.sh` (s15 harness, arm `pi1118`, n=3), pi vs base vs KAT | ~4–5 h, detached | |
| P6 | read every failure and void run in the transcripts; then believe the score | 30 min | |
| P7 | optional: Q8_0 pi at a smaller window, to see the quant drift | 1–2 h | only if P5 is close |
| P8 | verdict, review file, commit | 30 min | |

### Why the merge, and what it costs

The full account is in [`MERGE_ON_THIS_MACHINE.md`](MERGE_ON_THIS_MACHINE.md).

The card's own merge (`PEFT merge_and_unload` on the BF16 checkpoint) needs about 110 GB of disk and
about 54 GB of RAM. The laptop has 25 GiB free on `/home`, 30 GiB on `/` and 32 GB of RAM.
`llama-export-lora` writes F16 (54 GB). So `merge_lora_inplace.py` adds `2.0 · B·A` to each Q8_0
tensor and quantizes it again to Q8_0. The byte size stays the same, so it overwrites the base file.
Both arms then go through the same `llama-quantize` Q8_0 → Q4_K_M, so the adapter is the only difference.
The LoRA covers FFN in all 64 blocks and q/k/v/o in the 16 full-attention blocks, not the SSM layers.

### Why thinking must be forced off

A capture of Claude Code 2.1.327 shows that each request carries `output_config.effort: high`, also
with `CLAUDE_CODE_DISABLE_THINKING=1` or `MAX_THINKING_TOKENS=0`. Ollama maps that to thinking on.
The adapter was trained with thinking off. The tags therefore use renderer `qwen3.8` with parser
`qwen3-coder`. That parser has no thinking support, so the tag has no thinking capability. Ollama then
drops the thinking request from Claude Code and renders with think=false.

### Arms (all in arm `pi1118`, same client, same server, same sampler)

| tag | what | why |
|---|---|---|
| `qwen3.8-pi:27b-q4km-ctx200k-nothink` | Q8_0 base + merged adapter → Q4_K_M, thinking forced off | the subject, as trained |
| `qwen3.8-base:27b-q4km-ctx200k-nothink` | the same Q8_0 → Q4_K_M path, without the adapter | isolates the adapter effect |
| `kat-coder-v2.5:q5km-ctx256k-agentic` | the current default | the bar to beat and the drift control |

Both Qwen3.8 arms use `num_ctx 200000` (the owner's window from round 11-02), temperature 0.8,
top_p 0.95, top_k 20, presence_penalty 0. The 150k-token summary task needs more than 131072.

## The rule (fixed before the data)

The round 11-02 rule applies unchanged (`../ollamaClaudeCode_v4_tielCoder/ROUND_2026-11-02.md`, "The rule"):
correctness = mean over four tasks of the median share of checks; T5 ≥ 7/8 or not ranked; n=3
final; a session over 600 s is a failed session.

The recommendation to the owner follows from these numbers:

1. **Use it as the default** if T5 ≥ 7/8 and its correctness is more than 3 points above KAT in this arm.
2. **Keep it as an extra alias** if T5 ≥ 7/8 and its correctness is within 3 points of KAT.
3. **Do not use it** in every other case.
4. **The adapter works in Ollama** only if pi beats the base by more than 3 points of correctness, or wins T5. Otherwise the adapter adds nothing here.

## Red team of the plan

| # | attack | consequence if true | counter-measure in the plan |
|---|---|---|---|
| 1 | Ollama ignores `ADAPTER` for the `qwen35` family and loads only the base | we measure the base and call it "pi" | P2: greedy outputs must differ. Identical outputs stop the plan |
| 2 | LoRA on a Q4 base drifts (card warning) | the adapter looks weak because of the quant | P7: Q8_0 arm, if P5 is close. A weak Q4 result is reported as "Q4 only" |
| 3 | Claude Code sends `thinking: adaptive`, so the model thinks, but it was trained with thinking off | off-distribution, slower, worse | P3: a template that closes the think block. Check `think_chars = 0` in the TSV |
| 4 | the custom template breaks tool calls (the Kolibri lesson: wrong tool names scored as passes) | false T5 pass or false fail | strict T5; read the raw tool names; keep the stock-renderer tag as an A/B arm |
| 5 | pi tools (read, write, edit, bash) differ from Claude Code tools | the vendor gain does not transfer | this is the question; the paired base arm measures it |
| 6 | a dense 27B is slow (30 tok/s); sessions hit the 600 s limit | low score from speed, not skill | the rule counts this, and the report says it. Read the transcripts (P6) |
| 7 | the hybrid cache is not reused per turn (the card needs a vLLM flag for it) | every turn prefills the whole history | the summary probe measures repeat prefill; report it |
| 8 | 200k does not fit 100% on the GPU with the adapter | spill = 5× slower, void | the residency check stops it; fall back to 131072 and say so |
| 9 | past `num_ctx` the model silently halves the context | lost context, confident wrong work | overflow probe at the alias cap; the alias caps Claude Code below `num_ctx` |
| 10 | the box is in use, or the 11-02 round restarts | foreign model, void runs | `idle.sh` waits and never evicts; nothing else runs from this laptop |
| 11 | a new model, n=1, vendor numbers selected on the benchmark | false confidence | n=3; vendor numbers are claims only |
| 12 | KAT ran in rb1102, not here | cross-arm comparison | KAT runs again in this arm as the control |

## Status

| time | step | result |
|---|---|---|
| 11-18 10:47 | P0 | LoRA downloaded, hash matches HF. Box idle, Ollama 0.40.11, client 2.1.327 |
| 11-18 10:48 | P1 | `ADAPTER` refused by Ollama 0.40.11. Plan changed to a local merge |
| 11-18 10:50 | P1b | download of `ggml-org/Qwen3.8-27B-GGUF` Q8_0 (28.6 GB) started to `/var/tmp/v6` |
| 11-18 10:55 | P1b | `merge_lora_inplace.py` + 6 tests pass |
| 11-18 10:58 | P3 | Go template looked byte-identical to the renderer. **Harness defect**: the check tag inherited the `qwen3.8` renderer, so the template was never tested |
| 11-18 11:01 | P1b | `build.sh` waits for the download, then builds both tags. Alias `claude-ol-qwen3.8_27b_pi` added (`~/.zshrc`, backup `~/.zshrc.bak-v6-20261118`) |
| 11-18 11:14 | P1b | base arm published (16.5 GB, Q4_K_M 4.92 BPW). Its render check FAILED: the template was used and was wrong (compact JSON, missing newlines) |
| 11-18 11:16 | P3 | base tag re-created with renderer `qwen3.8` + parser `qwen3-coder`: IDENTICAL. Template deleted. `build.sh` fixed by rename while it runs; the pi tag gets re-created after the build |

## Results

None yet.

## Resume here

State (11-18 11:01): `build.sh` runs detached. It waits for the Q8_0 download, then builds and uploads both tags.
Next: P2 and P4 by hand, then start `v6-run.sh`.

Check the state:
1. `tail results/build.log`
2. `ls -l /var/tmp/v6 ~/.cache/v6-out`
3. `curl --noproxy '*' -fsS http://192.168.100.67:11434/api/ps`
4. `pgrep -af 'build.sh|v6-run.sh|s15-refresh'`

Restart the build. It skips every step it has marked in `/var/tmp/v6/.<step>`:
`setsid nohup systemd-inhibit --what=sleep:idle ./build.sh >/dev/null 2>&1 & disown`

If the build says "a merge was interrupted", delete `/var/tmp/v6/Qwen3.8-27B-Q8_0.gguf` and `/var/tmp/v6/.merge-started`, download again, then restart.

Start the measurement after P2 and P4:
`setsid nohup systemd-inhibit --what=sleep:idle ./v6-run.sh >/dev/null 2>&1 & disown`
