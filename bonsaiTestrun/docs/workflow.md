# Local-only workflow

## Safety boundary

All mutable runtime state is kept under the repository root. The scripts do not call `sudo`, package managers, `pip install`, or `systemctl`; they neither install nor modify host services. The only external actions are a git clone into `runtime/` and a resumable `curl` model download into `models/`.

```mermaid
flowchart LR
    A[Repository scripts and docs] --> B[runtime/llama.cpp source]
    B --> C[runtime/llama.cpp/build]
    D[models/Bonsai-27B-Q1_0.gguf] --> E[Local llama-server]
    C --> E
    E --> F[127.0.0.1:8080 only]
    F --> G[Local browser or curl client]
```

## Runtime sequence

```mermaid
sequenceDiagram
    participant U as User
    participant B as build-llama.sh
    participant D as download-model.sh
    participant S as start-server.sh
    participant L as llama-server
    U->>B: build locally
    B->>B: clone PrismML fork under runtime/
    B->>B: build CUDA binary under runtime/
    U->>D: download 1-bit text model
    D->>D: save GGUF under models/
    U->>S: start local server
    S->>L: 4K context, full GPU offload
    L-->>U: OpenAI-compatible API at localhost:8080
```

## Initial configuration

The initial server configuration is intentionally conservative:

- Model: `Bonsai-27B-Q1_0.gguf` only; no vision projection or speculative drafter.
- Context: 4096 tokens.
- GPU: request full layer offload (`-ngl 99`).
- Concurrency: one slot (`--parallel 1`); prompt-cache RAM is disabled and warmup is skipped to protect the 8 GB GPU budget.
- Binding: `127.0.0.1` only.
- GPU budget: the vendor model card reports about 5.2 GB peak memory at 4K context for the 1-bit language model. Check actual usage on this RTX A2000 8 GB GPU before increasing context.

## Build record

The local build uses PrismML's `prism` branch at commit `62061f9`, CUDA 13.3, and the RTX A2000 Laptop GPU's compute capability 8.6. It is generated under `runtime/llama.cpp/build/` and is ignored by git, so it can be deleted and recreated without touching the host installation.

The local-only 1-bit text model was downloaded as `models/Bonsai-27B-Q1_0.gguf` (3.54 GiB). The downloader first writes a `.partial` file and renames it only after a successful transfer.

## Validation record

The text-only server was started on `127.0.0.1:8080` and answered a chat-completions request successfully. On this machine, the 4K single-slot configuration occupied 4,096 MiB of 8,192 MiB GPU memory and generated about 15 tokens/second for a 32-token reasoning response. The validation process was stopped after the test; use `scripts/start-server.sh` to run it again.

## Validation and troubleshooting

`check-server.sh` sends a short chat completion to the local API and prints the result. While the server runs, inspect GPU use with:

```sh
nvidia-smi
```

If startup fails with an out-of-memory error, first close GPU-heavy programs and retry. Do not increase context, add vision, or add the drafter until a 4K text-only session succeeds. All generated state may be removed safely with `rm -rf runtime models logs`; this removes only repository-local artifacts.
