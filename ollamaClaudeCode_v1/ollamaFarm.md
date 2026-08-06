# `ollamaFarm.sh`

A btop-style live monitor for a small farm of Ollama servers.

`ollama ps` tells you what is loaded. This tells you what is *going wrong* — because
on this hardware the expensive mistakes are all silent: nothing errors, nothing warns,
the model answers correctly, and you simply lose a factor of 5 to 7 in throughput.
Every check below exists because it was measured costing real time (`review2.md`).

---

## What it watches

| # | Failure mode | Detected by | Measured cost |
|---|---|---|---|
| 1 | **Eviction thrash** — a second model displaces the resident one | diffing the model set between polls | **~70 s reload** per eviction |
| 2 | **Split placement** — part of the model sits in system RAM | `size_vram < size` | **5.3×** slower |
| 3 | **No baked `num_ctx`** | `/api/show` has no `num_ctx` | **16k** context cap; tool calling dies past it, silently |
| 4 | **`presence_penalty != 0`** | `/api/show` parameters | **~35%** of throughput |

Numbers 3 and 4 cannot be seen from `ollama ps` at all, and number 1 cannot be seen
from a *snapshot* of any kind — only a diff across time reveals it.

---

## At runtime

Real output, both servers busy, 104-column terminal:

```
┌─ Ollama farm ────────────────────────────────────────────────────────────────────────────────────────┐
  2026-08-06 14:42:06   every 1s   [+ slower  - faster  v m w e  d s  p pause  h help  q quit]

  192.168.100.37   ollama 0.30.6  ██████████████░░░░░░░░   8.0/12.2 GB    7ms
      qwen3.5:9b-ctx80k                9.7B Q4_K_M   8.01/8.01  GB ctx 81920   ttl 3m10s
        ↳ presence_penalty=1.5 (~35% slower — bake 0);

  192.168.100.67   ollama 0.32.5  ████████████████████░░  33.1/36.1 GB    6ms
      qwen3.6:35b-a3b-q4_K_M-agentic  36.0B Q4_K_M  33.09/33.09 GB ctx 262144  ttl 1h57m

  EVENTS
    14:42:06 loaded qwen3.5:9b-ctx80k on 192.168.100.37
    14:42:06 loaded qwen3.6:35b-a3b-q4_K_M-agentic on 192.168.100.67

  GPU temp/util/power need nvidia-smi on the host — press s once key access exists.
```

Note the `↳` line: `.37`'s model is running the qwen vendor default
`presence_penalty 1.5` and is giving away about a third of its speed for nothing.
`.67`'s is a purpose-built variant and is clean.

### And when things go wrong

The following frame is **fabricated** to show the alarm states together — the hosts
`.13`/`.99`, the model names and the numbers in it are invented, not measurements.
Every other example in this file is real captured output.

```
┌─ Ollama farm ───────────────────────────────────────────────────────  PAUSED — press p to resume ┐
  2026-08-13 03:04:59   every 5s   [+ slower  - faster  v m w e  d s  p pause  h help  q quit]

  192.168.100.13   ollama 0.32.5  ██████████████████████  35.9/36.1 GB  1840ms
      hoarder-70b:q8_0                69.9B Q8_0    31.40/35.80 GB ctx 4096    ttl 12s   ⚠ SPLIT→CPU (5.3x slower)
        ↳ presence_penalty=1.5 (~35% slower — bake 0); no baked num_ctx (16k cap via /v1/messages, tool calls die past it)
      tiny-yolk:0.5b                   0.5B Q4_0     0.41/0.41  GB ctx 2048    ttl 4m2s

  192.168.100.99   ollama 0.30.6  ░░░░░░░░░░░░░░░░░░░░░░   0.0 GB/?      9ms
      idle — no model resident

  192.168.100.37   ollama 0.30.6  UNREACHABLE (USB ethernet adapter up?)

  EVENTS
    03:04:31 loaded hoarder-70b:q8_0 on 192.168.100.13
    03:04:44 tiny-yolk:0.5b vanished on 192.168.100.13, 238s ttl left — suspected eviction, watching
    03:04:52 EVICTED tiny-yolk:0.5b on 192.168.100.13 → hoarder-70b:q8_0 after 8s (~70 s reload penalty)
    03:04:58 192.168.100.37 went unreachable (was holding: qwen3.5:9b-ctx80k)
```

Everything wrong with that box, top to bottom: the VRAM bar is red because it is at
99%; the 70B is **split to CPU** (31.40 resident of 35.80 total); it has **no baked
`num_ctx`**, so it is capped at 16k and its tool calls will silently stop; it has
`presence_penalty` on; its `ttl` is yellow because it expires in 12 s; latency is
1840 ms because the box is thrashing; a small model was **evicted** to make room; and
another host dropped off the network entirely. `.99` was found by discovery, so its
VRAM ceiling is honestly `?` rather than guessed.

---

## Keys

| key | effect |
|---|---|
| `-` / `+` | refresh **faster** / **slower** — steps the ladder `0.25 0.5 1 2 3 5 10 30` s |
| `p` | pause / resume (a paused frame polls nothing at all) |
| `v` | VRAM bars |
| `m` | per-model detail |
| `w` | the `↳` config warnings |
| `e` | event log |
| `d` | re-run host discovery |
| `s` | nvidia-smi over SSH |
| `h` or `?` | help overlay |
| `q` | quit |

`+` makes the interval *number* bigger, hence slower — the same direction as btop.
Any section you switch off is named in the header (`hidden: models:off(m)`), so a
toggle saved in an earlier session cannot leave you staring at a screen that looks
broken.

---

## Command line

```shell
./ollamaFarm.sh                    # default hosts, 1 s
./ollamaFarm.sh -n 5               # 5 s (snapped to the nearest ladder rung)
./ollamaFarm.sh -H 10.0.0.5,10.0.0.6
./ollamaFarm.sh -p 11435           # non-default port
./ollamaFarm.sh -D                 # scan for hosts at startup
./ollamaFarm.sh --ssh              # add nvidia-smi over SSH
./ollamaFarm.sh --no-color         # plain; NO_COLOR is honoured too
./ollamaFarm.sh --help
```

Requires `curl`, `jq`, `awk`. Checked at startup.

---

## Host discovery

**Hardcoded by default; scanning is opt-in.** Three sources, highest precedence first:

1. `-H a,b,c` — pins the list; never overridden
2. `$XDG_CONFIG_HOME/ollamafarm/hosts` — the cached result of a previous scan
3. the built-in defaults, `192.168.100.37` and `192.168.100.67`

A scan runs only on `-D` or the `d` key. It derives the `/24` from the hosts it
already knows, probes `/api/version` on `.1`–`.254` **64 at a time** with a 0.6 s
timeout, and caches what answered. Measured: both servers found, well under the
refresh interval.

Two deliberate limits:

- It only scans `/24`s **derived from hosts it already knows**. It will not find a
  server on an unrelated subnet — blind-scanning arbitrary ranges is not something a
  monitor should do unasked.
- **Usable VRAM is never probed.** Establishing it means pushing `num_ctx` until the
  model spills, which loads models and disturbs a shared machine. Known ceilings are
  the `VRAM_TOTAL` table in the script; anything else displays `?` and gets no bar,
  rather than a fabricated total.

To teach it a new host's ceiling, add a line to `VRAM_TOTAL` near the top of the
script:

```bash
declare -A VRAM_TOTAL=( [192.168.100.37]=12.2 [192.168.100.67]=36.1 )
```

---

## Configuration

Interval and toggles persist to `$XDG_CONFIG_HOME/ollamafarm/config`
(`~/.config/ollamafarm/config`):

```
idx=2            # index into the interval ladder; 2 = 1 s
show_bars=1
show_models=1
show_warn=1
show_events=1
```

Only these keys are read back, and each is validated on load, so a corrupt or
hand-edited file cannot break a run. Delete the file to return to defaults.
The discovered host list lives beside it in `hosts`.

---

## Load on a shared server

`.67` is a colleague's machine, so the polling is deliberately cheap:

- two `GET`s per host per frame (`/api/version`, `/api/ps`) — both read-only
- `/api/show` is fetched **once per (host, model)** and cached; the parameters cannot
  change while a model is resident
- **nothing** is polled while paused
- the default 1 s can be dialled back to 30 s with `+`; at 1 Hz two hosts are about
  170k requests a day, which is worth knowing before leaving it running overnight

The monitor never loads, unloads, or creates a model.

---

## What it cannot show

**GPU temperature, utilisation, fan and power.** The Ollama HTTP API does not expose
them — it reports model residency only. They live in `nvidia-smi` on the server, and
as of 2026-08-06 SSH to both hosts is refused (`publickey,password`). The `--ssh` /
`s` path is implemented and inert until key access exists; it is not faked.

**Whether a model is actively generating.** `/api/ps` reports residency, not activity.
The latency figure is the closest available proxy: a host busy generating answers
`/api/ps` more slowly, which is why it turns yellow above 400 ms and red above 1500 ms.

---

## Known limits

- The `~70 s` reload figure in the eviction message is the measured cost for the
  33 GB MoE on `.67`. A smaller model reloads faster; the message states the
  penalty it was calibrated against rather than computing a per-model estimate.
- Eviction confirmation uses a 150 s window. A displacement whose replacement takes
  longer than that to become resident stays labelled "suspected".
- Frames are clipped to the terminal height rather than scrolled. Enlarge the window
  or press `m`/`e` if you see `…frame clipped to terminal height`.
