# Bonsai 27B local runtime plan

## Feasibility

This computer can plausibly run the 1-bit, text-only Bonsai 27B model locally. It has 31 GiB of system RAM, 33 GiB of swap, and an NVIDIA RTX A2000 Laptop GPU with 8 GiB of VRAM (not 8 GB of system RAM).

The native 1-bit model is a 3.9 GB GGUF using PrismML's custom `Q1_0_g128` format and hybrid-attention kernels. PrismML estimates approximately 5.2 GB peak memory for the language model at a 4K-token context, including runtime overhead; full GPU offload at a 2K-4K context is therefore a realistic starting point on this GPU.

Native Ollama is not the current implementation target. Although Ollama can import many GGUF models, Bonsai's documented CUDA path requires PrismML's `llama.cpp` fork, which contains the custom `Q1_0_g128` kernels. The runnable result will instead be a local `llama-server` instance exposing an OpenAI-compatible API. We can reassess native Ollama only when it supports these kernels.

The ternary model, the optional vision component, the speculative-decoding drafter, and long contexts should not be enabled initially: they add memory pressure to an 8 GB GPU. The advertised 262K-token context is not a practical target for this hardware.

## Plan

1. Clone PrismML's `llama.cpp` fork into this repository and build the CUDA backend. Limit compilation parallelism to avoid exhausting the laptop's GPU or host memory.
2. Download only `Bonsai-27B-Q1_0.gguf` (about 3.9 GB). Do not download the vision projection or 1.79 GB speculative drafter during the initial setup.
3. Start `llama-server` bound to `127.0.0.1`, with all model layers GPU-offloaded and a conservative 4K-token context window.
4. Verify a real completion, inspect GPU residency and VRAM consumption with `nvidia-smi`, record generation speed, and confirm that the server remains stable under a short multi-turn conversation.
5. Add a small runnable wrapper and README covering installation, server start/stop, health check, and an example OpenAI-compatible chat request.
6. If the text-only runtime is stable, test an 8K context. Evaluate vision support, speculative decoding, and a native Ollama import only as separate experiments with explicit memory measurements.

## Sources

- [PrismML Bonsai 27B announcement](https://prismml.com/news/bonsai-27b)
- [Bonsai 27B GGUF model card](https://huggingface.co/prism-ml/Bonsai-27B-gguf)
- [Ollama model import documentation](https://docs.ollama.com/import)
