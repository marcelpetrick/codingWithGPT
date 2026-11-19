# Notes: Qwen3.8-27B "pi-adapted" on the Ollama box (2026-11-18)

Ten points on the work and the checks of today. Details are in [`README.md`](README.md).

1. **Goal.** Run [`harness-hub/Qwen3.8-27B-pi-adapted`](https://huggingface.co/harness-hub/Qwen3.8-27B-pi-adapted) with Claude Code on the box `192.168.100.67`. The box has a 40 GB GPU (~35.5 GB usable) and runs Ollama 0.40.11.
2. **Ollama refused the adapter.** `ADAPTER` gives "LoRA adapters are no longer supported". So we merged the LoRA into the weights ourselves.
3. **We merged on the laptop, in place.** `merge_lora_inplace.py` adds the LoRA delta to each tensor of the Q8_0 base and writes it back in the same file. The card's own merge needs ~110 GB of disk and ~54 GB of RAM, which the laptop does not have.
4. **We built a fair control.** The base and the pi model went through the same Q8_0 → Q4_K_M step, so the adapter is the only difference. Both are 16.5 GB and run 100% on the GPU with a 200k window (31.2 GB).
5. **We forced thinking off.** Claude Code always asks for thinking, but the adapter was trained without it. Renderer `qwen3.8` + parser `qwen3-coder` fixed this. A byte-for-byte render check proved it.
6. **We proved the adapter is active.** Logprobs differ on 6 of 6 prompts. The single-turn effect is small.
7. **Smoke checks passed.** Tool calls work, there are 0 thinking characters, and the speed is 30.8 tok/s (20 tok/s at 150k). Past 200k the context is silently halved, so the alias caps Claude Code at 180k.
8. **Functional test: pi is the most correct model on the box.** Python, Qt/C++, GitLab and summary tasks, n=3, all models in one arm: pi 100.0, base 96.7, occamy 93.2, KAT 91.5. The adapter also cuts tool calls by 32% compared with the base.
9. **But it is about 4× slower.** A pi session takes 560 s, a KAT session 138 s. The prefill is 1,060 tok/s against 2,985 for KAT.
10. **Verdict: stay with KAT for daily work.** `claude-ol-kat` is [KAT-Coder-V2.5-Dev](https://huggingface.co/bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF) by Kwaipilot, a Qwen3.6-35B-A3B fine-tune trained with Claude Code as the harness, at Q5_K_M. It has been the default since 2026-10-19. Use `claude-ol-qwen3.8_27b_pi` when correctness matters more than time.

Open, on hold: P7 (the same model at Q8_0, to check how much of the gain is quantization noise), Ornith-1.5 in the same arm, and the rest of round 11-02. The list is in README.md, "Left to do".
