# Ollama systems: versions and update decision

Checked **2026-10-05 09:35 CEST**. **Update 17:00: the owner upgraded `.67` to 0.35.1 at ~16:45, during KAT's extended pass;** that pass is labelled mixed-runtime (`ROUND_2026-09-24.md`). The re-baseline below is now owed. The decision here follows the round rule: the runtime is part of the
measurement, so a shared server is never upgraded mid-round (`AGENTS.md`, `ROUND_2026-09-24.md` § Runtime).

## Verdict

| system | role | runs | latest stable | update? | when |
|---|---|---|---|---|---|
| `192.168.100.67:11434` | the benchmark box, ~35.5 GB VRAM | **0.35.1** since 10-05 ~16:45 (was 0.33.3) | 0.40.0 (10-06) | **done** to 0.35.1 (owner, 10-05); no reason to go to 0.40.0 yet (`CANDIDATE_REGISTER.md` 10-07) | re-baseline owed: steps 4–5 of the procedure below (the round closed 10-08) |
| `192.168.100.37:11434` | small models only, ~12 GB | **0.32.15** | 0.40.0 | **yes, can go first** | any time; it is not part of the running round. The owner's call (shared server) |
| laptop, Claude Code | client | host 2.1.289, containers **pinned 2.1.283** | — | keep the pin for this round | re-pin with the post-upgrade re-baseline |

`v0.40.0` went stable on 10-06; it pins llama.cpp b11351 and brings nothing the field needs yet (K2-Horizon support is expected in ~0.40.1).

## Why update `.67` at all

1. **Silent truncation (the main reason).** 0.33.3 ends a completion *as if normal* after 30 repeats of
   the same trimmed token (ollama#18374); a digit run or blank-line run can trigger it, and Claude Code
   sees an ordinary end of turn. Fixed since 0.34.1 ("runaway repeat detection now requires 100 repeat
   tokens", and the error is real). Not yet shown to have hit a trial, but it has the shape of every
   defect this project has found.
2. Structured outputs on thinking models in one pass (0.34.4), `/api/show` advertises thinking levels
   (0.34.3): useful to verify thinking parity per model.
3. llama.cpp b10760 → b11081+: analysed on 09-24, **nothing measurable** for one GPU at batch 1.
4. 0.35.x adds decision models (`/v1/systemone`: Nimble, Tev1, Clef). Irrelevant to the coding field.
5. **It unblocks no candidate today.** Xing4.0 (llama.cpp#29012) and K2-Horizon MoVA (#29535) are still
   unmerged upstream, so no Ollama release loads them (`CANDIDATE_REGISTER.md`, 10-05).

## Why not mid-round (history, 10-05 09:35; the owner upgraded at 16:45 anyway, see the top)

- The extended qwen3.6 vs KAT pair and the Laguna screen are running on 0.33.3. An upgrade mid-pass
  splits one measurement across two runtimes.
- The Anthropic endpoint's thinking mapping changed (`output_config.effort` passes through as a
  model-defined level, with ollama#18473): "thinking on" may mean something else per model afterwards,
  so the thinking-parity arm is **not comparable across the upgrade**.
- History: the 0.32.15 upgrade re-ranked the field (+221% for nemotron, 0% for the control). An
  upgrade is a measurement event, not maintenance.

## Upgrade procedure for `.67` (after the round)

1. Confirm idle: `curl --noproxy '*' -fsS http://192.168.100.67:11434/api/ps` returns `{"models":[]}`,
   and no driver runs (`pgrep -af '^bash \./'`).
2. Record the pre-upgrade state in the round document (version, `ollama list` digests).
3. Upgrade to the then-latest stable (0.35.1 today), keep the same environment (`OLLAMA_*` vars, the
   KV-cache type unchanged so R4 stays a separate step).
4. Re-run before trusting any number: the thinking-parity smoke test, the T5 gate, and one reference
   pass per standing model (qwen3.6 greedy first, then KAT), all on the **same pinned Claude Code**.
   Change the client pin only in a separate, labelled step afterwards, so the two confounds never mix.
5. Label all rows with the new runtime version, and never pool them with 0.33.3 rows.

`.37`: upgrade straight to 0.35.1; afterwards check `/api/version` and one small-model generation.

## Check commands

```bash
for h in 192.168.100.67 192.168.100.37; do echo "$h $(curl --noproxy '*' -fsS -m 8 http://$h:11434/api/version)"; done
gh release list -R ollama/ollama -L 5
```
