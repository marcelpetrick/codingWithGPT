# Ollama Image Generation

> **TL;DR: Ollama image generation does not work on Linux with an Nvidia GPU.** It requires Apple MLX and is macOS-only as of Ollama 0.30.6.

Text-to-image generation using the network Ollama server at `192.168.100.37:11434`.

## What's here

| File | Purpose |
|---|---|
| `generate_image.py` | CLI tool: text prompt → PNG saved locally |
| `output/` | Generated images land here (created on first run) |

---

## Quick start

```bash
pip install requests

# Generate with default model (flux2-klein)
python generate_image.py "a red fat cat pointing to a whiteboard that says eat less do more, photorealistic"

# Pull model if not yet on server, then generate
python generate_image.py "sunset over the ocean" --pull

# Use a different model or size
python generate_image.py "cyberpunk cityscape" --model x/z-image-turbo --size 1024x1024

# Custom output directory
python generate_image.py "portrait" --out ~/Desktop/ai_art
```

Images are saved to `./output/` as PNG files named `YYYYMMDD_HHMMSS_<prompt_snippet>.png`.

---

## Server

| | |
|---|---|
| Host | `http://192.168.100.37:11434` |
| Ollama version | `0.30.6` |
| GPU VRAM | ~12 GB |
| OS | Linux |

Connectivity check:
```bash
curl http://192.168.100.37:11434/api/version
# → {"version":"0.30.6"}
```

---

## Image generation models

Ollama added native image generation support (experimental) in early 2026. On the Ollama library, image generation models live under the `x/` namespace.

| Model | Size on disk | VRAM fit | Notes |
|---|---|---|---|
| `x/flux2-klein` | ~5.7 GB | Good for 12 GB GPU | FLUX.2 by Black Forest Labs — fast, good text rendering |
| `x/z-image-turbo` | ~12.7 GB | Tight on 12 GB GPU | Z-Image Turbo by Alibaba — photorealistic, bilingual text |

**`x/flux2-klein` is the recommended starting point** — smaller, faster, and fits comfortably within 12 GB VRAM.

### Pull a model (one-time, runs on the server)

```bash
# via CLI on the server
ollama pull x/flux2-klein
ollama pull x/z-image-turbo

# via API (triggers download on the server without SSH)
python generate_image.py "any prompt" --pull
```

Check what's installed:
```bash
curl -s http://192.168.100.37:11434/api/tags | python3 -c \
  "import json,sys; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

---

## API used

The script uses Ollama's OpenAI-compatible endpoint first, then falls back to the native endpoint:

```
POST http://192.168.100.37:11434/v1/images/generations
```

```json
{
  "model": "x/flux2-klein",
  "prompt": "your text prompt here",
  "n": 1,
  "size": "1024x1024",
  "response_format": "b64_json"
}
```

Response is an OpenAI-format JSON with `data[0].b64_json` containing a base64-encoded PNG.

---

## Platform limitation — Linux not yet supported (Ollama 0.30.6)

**TL;DR: model pulls work on Linux, but generation fails with an MLX error.**

```
mlx runner failed: failed to initialize MLX: failed to load MLX dynamic library
```

Ollama's image generation backend uses **Apple MLX** (Apple's GPU framework), which is macOS-only. The remote server at 192.168.100.37 runs Linux, so generation fails at runtime even after a successful model download.

- Confirmed: `x/flux2-klein` (5.73 GB) pulls successfully on Linux via `/api/pull`
- Confirmed: `/v1/images/generations` and `/api/generate` both return HTTP 500 with the MLX error
- Ollama blog says "Windows and Linux coming soon" — wait for a future Ollama release

**Workaround for Linux: use the HuggingFace `diffusers` library directly** — see `generate_image_diffusers.py`.

---

## Alternative: diffusers (works on Linux now)

`generate_image_diffusers.py` uses HuggingFace diffusers + FLUX.1-schnell directly.
Run it **on a machine with a CUDA GPU** (e.g. SSH into the server at 192.168.100.37).

```bash
# Install once
pip install diffusers transformers accelerate torch sentencepiece protobuf

# Generate (first run downloads ~23 GB model weights to ~/.cache/huggingface/)
python generate_image_diffusers.py "a red fat cat pointing at a whiteboard that says eat less do more, photorealistic"

# Options
python generate_image_diffusers.py "cyberpunk cityscape" --steps 4 --size 1024x1024 --seed 42
```

| | `generate_image.py` (Ollama) | `generate_image_diffusers.py` (diffusers) |
|---|---|---|
| Works on Linux | Not yet (MLX error) | Yes |
| Needs Ollama server | Yes | No |
| Model download | 5.7 GB (flux2-klein) | ~23 GB (FLUX.1-schnell fp16) |
| Quality | Good | Good (same model family) |
| Steps needed | ? | 4 (distilled model) |

---

## Comparison: Ollama vs ComfyUI for image generation

| | Ollama | ComfyUI |
|---|---|---|
| Setup | `ollama pull model` | Complex install, UI, checkpoints |
| API | Simple REST | REST but complex workflow JSON |
| Model choices | Small, curated set | Thousands (SDXL, SD3, FLUX, LoRA…) |
| ControlNet/LoRA | No | Yes |
| Best for | Quick generation, LLM+image pipelines | Max quality, fine control |

For quick text-to-image with the existing Ollama server: use this. For full creative control with LoRA, inpainting, upscaling: add ComfyUI separately.

---

## Related projects

- [`ollamaClaudeCode/`](../ollamaClaudeCode/) — Claude Code routed through the network Ollama server for LLM tasks
- [`ollamaClaudeCode/LOCAL_OLLAMA_SERVER.md`](../ollamaClaudeCode/LOCAL_OLLAMA_SERVER.md) — full benchmark and model list for the network server
