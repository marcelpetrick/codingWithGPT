# Bonsai 27B local runtime

This repository provides a **local-only** runtime for the 1-bit Bonsai 27B GGUF on this Linux machine. It does not install llama.cpp, Ollama, packages, services, or model files outside this working tree.

The server is llama.cpp's OpenAI-compatible HTTP server, built from PrismML's llama.cpp fork because Bonsai's `Q1_0_g128` weights require its custom CUDA kernels. This is deliberately not an Ollama installation or replacement.

## Layout

| Path | Purpose | Committed |
| --- | --- | --- |
| `scripts/` | Safe local build, model download, server, and check commands | Yes |
| `docs/` | Workflow and operational documentation | Yes |
| `runtime/` | Cloned llama.cpp source and local build output | No |
| `models/` | Downloaded model weights | No |
| `logs/` | Server PID and logs | No |

## Quick start

Run every command from this repository root:

```sh
./scripts/build-llama.sh
./scripts/download-model.sh
./scripts/start-server.sh
./scripts/check-server.sh
```

Stop the server with:

```sh
./scripts/stop-server.sh
```

The server binds only to `127.0.0.1:8080`; it is not reachable from the network. See [the workflow guide](docs/workflow.md) before running it.

## Verified configuration

The text-only model has been validated on this machine at a 4096-token context with one concurrent slot. It used 4,096 MiB of the RTX A2000's 8,192 MiB VRAM and generated approximately 15 tokens per second. `check-server.sh` confirms that the local OpenAI-compatible chat-completions endpoint responds; the model may spend its first tokens in its reasoning channel, so a short check response can have an empty visible `content` field while still being a successful completion.

The model is intentionally not imported into Ollama: the native Bonsai `Q1_0_g128` format requires PrismML's local llama.cpp fork and custom CUDA kernels.
