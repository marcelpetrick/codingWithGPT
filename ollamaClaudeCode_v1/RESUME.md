# RESUME — where we left off

**UPDATE 2026-08-04 (later the same day): the benchmarks ran. Read `review.md`
for results.** Network was fixed by the USB ethernet adapter coming up on
`192.168.100.54/24`. Everything below this banner described the pre-reboot
blocked state and is kept for history; the connectivity section is stale.

Still open after the run:
1. Pull `qwen3.6:27b-q4_K_M` onto `.67` (the actual recommendation) — needs Alex's OK.
2. SSH keys on both servers — no GPU temp/util/power without them.
3. `nvidia-smi -L` on `.67` to confirm the two cards behind the measured ~36.1 GB.
4. Tool-use probe for `qwen3-coder:30b`.
5. Fresh context sweep on `.37` — v0's ctx80k ceiling is obsolete, ctx96k is now free.

---

Last updated: 2026-08-04, before a reboot. Read `plan.md` for the full plan;
this file is only "what to do the moment you sit back down".

---

## One-paragraph state

The old `ollamaClaudeCode/` dir was renamed to `ollamaClaudeCode_v0/` (rename
**not committed yet**). `ollamaClaudeCode_v1/` is new and holds only `plan.md`
and this file. A new Ollama server exists at **192.168.100.67** (from Alex), with
benchmark numbers he pasted for `llama3.1:8b`, `qwen3.6:36b-q4_K_M` and a note
that `qwen3.6:27b-q8_0` never stops thinking. **Zero measurements have been taken
by us.** The blocker is purely network: this laptop had no route to
`192.168.100.0/24`.

---

## Step 1 — after reboot, check connectivity first

```shell
ip -brief addr show | grep -v DOWN
curl -s --max-time 5 http://192.168.100.67:11434/api/version
curl -s --max-time 5 http://192.168.100.37:11434/api/version
```

Expected before the reboot (verified outside the sandbox, 2026-08-04):

```
laptop: 10.185.212.209/8 on wlp0s20f3, default via 10.128.128.128
192.168.100.37 -> no ICMP, port 11434 unreachable
192.168.100.67 -> no ICMP, port 11434 unreachable
```

If it still fails after the reboot, the reboot was not the fix — the laptop is on
a `10.x` network with no route to `192.168.100.0/24`. Options then: VPN, on-site
wifi, or a tunnel:

```shell
ssh -L 11434:192.168.100.67:11434 <jumphost>   # then benchmark localhost:11434
```

Careful: local Ollama already listens on 11434, so pick another local port
(e.g. `-L 11435:...`) or stop the local service first.

## Step 2 — if reachable, fingerprint before anything else (read-only, safe)

```shell
for ip in 192.168.100.37 192.168.100.67; do
  echo "=== $ip ==="
  curl -s --max-time 5 "http://$ip:11434/api/version"; echo
  curl -s --max-time 10 "http://$ip:11434/api/tags" | jq -r '.models[].name' | sort
  echo "--- currently loaded ---"
  curl -s --max-time 5 "http://$ip:11434/api/ps" | jq -r '.models[]? | "\(.name) \(.size_vram/1e9|floor)/\(.size/1e9|floor) GB"'
done
```

Two things to read out of this: does `qwen3.5:9b-ctx80k` exist on `.67`
(needed for the apples-to-apples comparison), and is somebody else's model
loaded right now (if yes, do **not** benchmark — you would steal their VRAM and
get garbage numbers).

## Step 3 — then follow `plan.md` phases 1 → 7

Do not skip to the big models. Phase 3 (one known model, low impact) before
Phase 4 (27b/36b, thinking-mode protocol, needs Alex's OK).

---

## Facts that must not get lost

**The two benchmarks are not comparable.** Alex's numbers come from
`ollama run --verbose <model> "Write exactly 1000 tokens about GPUs."` (prose,
uncapped, 828–2889 tokens). `v0/benchmark.sh` uses a Sieve-of-Eratosthenes
prompt capped at `num_predict: 300`. Longer generations amortise warm-up better,
so they report higher tok/s for the same hardware. The v1 harness must run both
profiles (S = short/coding, L = long/prose) and tag every number.

**Alex's reference numbers on `.67`** (his methodology, profile L):

| Model | eval rate | eval count | total duration | note |
|---|---|---|---|---|
| `llama3.1:8b` | 86.87 tok/s | 828 | 10.44 s | word count 998 |
| `qwen3.6:36b-q4_K_M` | 89.79 tok/s | 2889 | 33.80 s | faster than the 8b — quantisation is q4_K_M |
| `qwen3.6:27b-q8_0` | — | — | — | "denkt ewig nach", thinking never terminates |

Also noted by Alex: **"256K Context als Standard"** on `.67` — unverified whether
that is a server-side `OLLAMA_CONTEXT_LENGTH` or per-model `num_ctx`. It has a
large KV-cache/VRAM impact and would distort every result if left unknown.

**Thinking mode is the known trap, and it has now bitten twice.** v0 run 5 got
0 tok/s from `qwen3.5:27b` and `qwen3.6:27b-q4_K_M`; Alex hit the same with
`qwen3.6:27b-q8_0`. But his `36b-q4_K_M` finished fine — so it is not "big model
= hangs". Test with `"think": false`, with `/no_think` in the prompt, and
uncapped at a 600 s timeout, and count thinking tokens separately.

**The ctx80k sweet spot does not transfer.** It is a property of `.37`'s 12 GB
GPU (fully-GPU up to 12.22 GB, split and −33% speed at ctx96k). `.67` looks
considerably stronger and needs its own sweep.

**`.67` is Alex's machine.** Get permission before a full sweep, before pulling
models, and before creating Modelfile variants. Agree a
`systemctl restart ollama` path in advance — v0 run 3 lost a whole run to a
model-swap deadlock that only a service restart cleared. Unload between models
with `keep_alive: 0` and poll `/api/ps` until VRAM frees.

**Tool use is untested for the whole `qwen3.6` family.** Speed is irrelevant if
Claude Code cannot drive the model. The probe is in `v0/OLLAMA_PULL.md` (expect
`stop_reason: tool_use`). v0 evidence: `qwen3.5` and `mistral-nemo` pass;
`qwen2.5-coder` and `codestral` fail.

---

## Open questions still waiting on the user

1. When is there network access to `192.168.100.0/24`?
2. Is `.37` still in service, or fully replaced by `.67`?
3. How much freedom on `.67` — read-only / sweep existing models / pull + create variants?
4. Who can restart Ollama on `.67` if it deadlocks?
5. Commit the `v0` rename now, or once v1 has results?

## Not done yet

- `benchmark.sh` v1 (harness rewrite) — **can be written offline**, needs no server
- everything in phases 1–7 of `plan.md`
- the `v0` rename is still uncommitted in git
