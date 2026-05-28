# Debugging: Claude Code + Ollama — requests never finish

## Symptom

After setting the `claude-ol` alias and sourcing `.zshrc`, every Claude Code
request hung indefinitely and never returned a response.

## Diagnosis steps

### 1. Verify server reachability

```shell
curl http://192.168.100.37:11434/api/version
# → {"version":"0.22.0"}   ✓ server is up
```

### 2. Check if Anthropic-compatible endpoint exists

```shell
curl -s --max-time 5 -o /dev/null -w "%{http_code}" \
  -X POST http://192.168.100.37:11434/v1/messages \
  -H "Content-Type: application/json" -d '{}'
# → 400   ✓ endpoint exists (400 = bad payload, not 404)

curl -s --max-time 5 -o /dev/null -w "%{http_code}" \
  http://192.168.100.37:11434/v1/models
# → 200   ✓ OpenAI-compatible endpoint also works
```

### 3. Test actual inference — Anthropic API

```shell
curl -s --max-time 30 \
  -X POST http://192.168.100.37:11434/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: ollama" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "qwen3.5:9b-ctx64k",
    "max_tokens": 20,
    "messages": [{"role": "user", "content": "hi"}]
  }'
# → exit code 28 (timeout)  ✗ hangs
```

### 4. Test smallest model to isolate VRAM vs model-size issue

```shell
curl -s --max-time 60 \
  -X POST http://192.168.100.37:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5:0.8b",
    "max_tokens": 20,
    "messages": [{"role": "user", "content": "hi"}]
  }'
# → exit code 28 (timeout)  ✗ even 0.8b hangs
```

### 5. Inspect loaded models

```shell
curl -s http://192.168.100.37:11434/api/ps | jq '.'
```

Output:
```json
{
  "models": [
    {
      "name": "qwen3.5:9b-ctx64k",
      "size": 10832362432,
      "size_vram": 0,
      "context_length": 65536,
      ...
    }
  ]
}
```

## Root cause

**`size_vram: 0`** — the model is loaded entirely into system RAM with no GPU
offloading. All inference runs on CPU.

A 9.7B parameter model at Q4_K_M quantization on CPU produces ~1–3 tokens/second
under load, so even a trivial "hi" prompt may take minutes. All our curl timeouts
fired before any token was generated.

## Benchmark: all models, 180s timeout

Script: `benchmark.sh` — prompt: Sieve of Eratosthenes in Python with type hints.

| Model | Size | Result |
|---|---|---|
| `qwen2.5-coder:32b` | ~20 GB | TIMEOUT >180s |
| `qwen3:14b-q8_0` | ~14 GB | TIMEOUT >180s |
| `qwen3:8b-q8_0` | ~8 GB | TIMEOUT >180s |
| `qwen3.5:0.8b` | ~0.5 GB | TIMEOUT >180s |
| `qwen3.5:9b-ctx64k` | ~5.5 GB | TIMEOUT >180s |
| `qwen3.5-ctx32k:9b` | ~5.5 GB | TIMEOUT >180s |
| `qwen2.5-coder:7b-ctx32k` | ~4 GB | TIMEOUT >180s |
| `qwen2.5-coder:7b` | in progress at cutoff | — |
| `qwen3.5:27b` | ~16 GB | not reached |
| `qwen3-coder:30b` | ~18 GB | not reached |
| `qwen3-vl:4b` | ~4 GB | skipped (vision) |
| `qwen3-vl:8b` | ~8 GB | skipped (vision) |

**0 out of 13 models completed a request within 180 seconds.**

The 0.8b result is the critical data point: a ~500 MB model that should complete
in seconds on any modern CPU still timed out. This rules out "model too large for
VRAM" as the sole explanation and points to a deeper server-side issue.

### Likely causes for 0.8b also timing out

1. **Model-swap overhead**: each timed-out request leaves Ollama mid-load. The
   next request queues behind the previous model being unloaded from RAM before
   the new one can load. On a memory-constrained machine this can take the full
   180s window by itself.

2. **Extremely slow storage**: if the server reads model weights from a slow HDD
   or network share, loading even a 500 MB model can take minutes.

3. **No GPU + memory pressure**: with multiple large models partially resident in
   RAM and no GPU to offload to, the system may be heavily swapping.

4. **Ollama request queue**: Ollama processes one inference at a time. If a prior
   stuck request is not properly cancelled, subsequent requests wait in queue.

## What to check on the server machine

### Step 1 — confirm GPU situation

```shell
nvidia-smi          # NVIDIA: shows VRAM usage and driver version
rocm-smi            # AMD: equivalent
ollama ps           # size_vram should be > 0 if GPU is in use
```

### Step 2 — check system resources during inference

```shell
# While sending a request, monitor in another terminal:
htop                # CPU and RAM usage — watch for 100% CPU and swap usage
free -h             # total / used / swap
iostat -x 1         # disk I/O — high await means storage is the bottleneck
```

### Step 3 — isolate model loading vs inference

Send a request with `num_predict 1` (generate exactly 1 token) and measure how
long it takes. If it still times out, the bottleneck is model loading, not
inference speed:

```shell
time curl -s --max-time 300 \
  -X POST http://192.168.100.37:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3.5:0.8b", "prompt": "hi", "stream": false, "options": {"num_predict": 1}}'
```

### Step 4 — check Ollama logs on the server

```shell
journalctl -u ollama -f        # systemd
# or
~/.ollama/logs/server.log      # manual install
```

Look for: CUDA errors, out-of-memory messages, model load failures.

### Step 5 — fix GPU offloading (if GPU exists but is unused)

```shell
# Verify Ollama was installed with GPU support
ollama --version
ollama serve --help | grep gpu

# For NVIDIA: confirm CUDA toolkit is present
nvcc --version
ldconfig -p | grep libcuda

# Reinstall Ollama to pick up CUDA (if missing)
curl -fsSL https://ollama.com/install.sh | sh
```

After reinstalling, pull a model and confirm `size_vram > 0`:

```shell
ollama pull qwen3.5:0.8b
curl http://localhost:11434/api/ps | jq '.[].size_vram'
```

## Expected state once GPU is working

```shell
curl http://192.168.100.37:11434/api/ps | jq '.models[] | {name, size_vram}'
# should show size_vram matching (or close to) model file size
```

Typical token speeds with GPU:
- 0.8b → 80–150 tok/s
- 7–9b → 30–60 tok/s
- 14b  → 15–30 tok/s
- 30b+ → 5–15 tok/s (or split across GPUs)

At those speeds, Claude Code sessions are interactive. At CPU speeds (1–3 tok/s
for 7b+), they are not.
