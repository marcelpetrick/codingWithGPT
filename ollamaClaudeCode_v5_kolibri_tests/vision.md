# Vision: Kolibri-1 on 40 GB VRAM

Assessment date: 4 November 2026.

## Goal

Run Aleph Alpha's Kolibri-1 locally on hardware with 40 GB of VRAM, preferably through Ollama, using a compressed version where necessary.

## Conclusion

40 GB VRAM is potentially sufficient for a 3-bit quantized version at a modest context length. The original FP8 checkpoint does not fit entirely in that VRAM budget. Working Ollama support was not verified during this assessment; the documented community route uses a patched llama.cpp runtime.

## Model background

The model card supplied in the conversation describes Kolibri-1 as a German- and English-focused mixture-of-experts reasoning model with tool calling.

| Property | Value from the supplied model card |
| --- | --- |
| Total parameters | 78.1 billion |
| Active parameters per token | 3.46 billion |
| Original published precision | Mostly FP8, with selected tensors in BF16 |
| Approximate FP8 weight memory | 78 GB |
| Native context | 262,144 tokens |
| Extended context reported by the publisher | 1,048,576 tokens |
| Publisher's serving recommendation | At most 262,144 tokens for efficiency and complex tasks |
| Documented serving routes | Transformers and vLLM with the Aleph Alpha inference plugin |
| Weight license | Apache 2.0 |

The small active parameter count reduces computation per token. It does not make this a 3.46B-parameter model for storage purposes: all experts still need to be stored, whether in GPU memory or a supported CPU/GPU offloading arrangement.

The publisher's long-context capabilities are not a promise that those contexts will fit on 40 GB VRAM or work correctly in an experimental quantized runtime.

## Available compressed versions

Community GGUF quantizations are available. File sizes below are reported by their publishers; the fit assessments are estimates, not measured VRAM usage on the user's hardware.

| Quantization | Weight file size | Assessment for 40 GB VRAM | Source |
| --- | --- | --- | --- |
| Q4_K_M | 47.5 GB | Too large for full GPU loading | [Hob-forge](https://huggingface.co/Hob-forge/Kolibri-1-GGUF) |
| Q3_K_M | 37.5 GB | Plausible at short context, with limited headroom | [Hob-forge](https://huggingface.co/Hob-forge/Kolibri-1-GGUF) |
| Q3_K_S | 33.87 GB / 31.54 GiB | More promising fit | [Eliasfpv28](https://huggingface.co/Eliasfpv28/Kolibri-1-Q3_K_S-GGUF) |
| Q2_K | 28.6 GB | More headroom, but more aggressive compression | [Hob-forge](https://huggingface.co/Hob-forge/Kolibri-1-GGUF) |

GB and GiB are different units. Compare the actual available GPU memory with model allocations rather than subtracting differently expressed numbers.

Weight file size is only part of the memory budget. The context's key/value cache, runtime buffers, other GPU allocations, and concurrent requests also require memory. More aggressive quantization can reduce accuracy; the original model's benchmark scores should not be assumed to transfer to these conversions.

## Ollama compatibility

The reviewed Hob-forge model instructions explicitly require a llama.cpp patch for the `kolibri1` architecture and warn that Ollama and other llama.cpp-based applications need architecture support before loading it.

The Q3_K_S author likewise states that Ollama compatibility has not been verified. Its documented runtime is a pinned llama.cpp revision with the supplied experimental patch.

Hugging Face displays generic Ollama launch commands above some model cards. Those generated commands are not proof that a particular model architecture is supported by an installed Ollama version.

Therefore, an Ollama-only deployment remains unconfirmed. Recheck support against the exact installed Ollama version before downloading a large file specifically for that route.

## Recommended initial experiment

Start with the Q3_K_S conversion and its documented patched llama.cpp runtime:

1. Identify the exact GPU or GPUs, available VRAM, operating system, and system RAM.
2. Follow the runtime build instructions in the Q3_K_S repository.
3. Load `Kolibri-1-Q3_K_S.gguf` with an initial context of 4,096 tokens and one concurrent request.
4. Measure actual GPU memory use and generation speed on representative German and English prompts.
5. Check reasoning and tool calling separately if those features are needed.
6. Increase context only after confirming memory headroom and correctness.

This is a reasonable starting configuration, not a guarantee of fit or performance. The Q3_K_S publisher reports limited functional tests, including runs on an RTX 3060 plus an Intel Arc Pro B60. These do not establish performance on the user's hardware or validate full long-context behavior.

If a desired quantization does not fit entirely in VRAM, partial CPU offloading may be an option with a compatible runtime and sufficient system RAM. Its performance depends on the hardware and configuration; no throughput estimate has been established here.

## Information still needed

- Exact GPU model, or the models and VRAM capacities of multiple GPUs.
- Total system RAM.
- Operating system and installed Ollama version.
- Desired context length and number of simultaneous requests.
- Whether using patched llama.cpp instead of Ollama is acceptable.

## Evidence and limits

This document consolidates the supplied model card and the compatibility and quantization assessment from this conversation. No model was downloaded or run, and no memory or speed benchmark was performed. Compatibility statements reflect the reviewed sources on the assessment date and may change.

## Sources

- [Official Kolibri-1 model card](https://huggingface.co/Aleph-Alpha/Kolibri-1) — model background; the full card was supplied in the conversation.
- [Hob-forge Kolibri-1 GGUF](https://huggingface.co/Hob-forge/Kolibri-1-GGUF) — quantization sizes, required patch, and compatibility warning.
- [Eliasfpv28 Kolibri-1 Q3_K_S GGUF](https://huggingface.co/Eliasfpv28/Kolibri-1-Q3_K_S-GGUF) — file size, runtime instructions, validation scope, and limitations.
- [llama.cpp Kolibri-1 support request](https://github.com/ggml-org/llama.cpp/issues/29922) — upstream support tracking; shown as open when reviewed.
