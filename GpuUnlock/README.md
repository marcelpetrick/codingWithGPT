# GPU unlock: review

Checked on 2026-11-09. Upstream: [Zagitta/gpu-unlock](https://github.com/Zagitta/gpu-unlock), commit `7eb51bccae0a0b7e599e084d971170e9a1e82d0c`.

## Verdict

This appears to be a real GPU performance project. A limited source review found no clear credential-stealing code. This is not a security audit or proof that the project is safe.

Do not use it on this laptop. The NVIDIA RTX A2000 8GB Laptop GPU has PCI ID `10de:25ba` and a GA107 chip. Neither `25ba` nor GA107 appears in the [upstream supported device table](https://github.com/Zagitta/gpu-unlock/blob/7eb51bccae0a0b7e599e084d971170e9a1e82d0c/kernel/gpu_unlock/recipes.c). The project targets listed GeForce models. It does not establish that this professional GPU needs or can use the change.

## What it does

The Linux kernel module runs before the NVIDIA driver. It uses a GPU firmware security bypass to gain access to protected registers. It changes tensor speed selectors and resets the GPU before the normal driver loads. The project says it does not flash the VBIOS. Its [README](https://github.com/Zagitta/gpu-unlock/blob/7eb51bccae0a0b7e599e084d971170e9a1e82d0c/README.md) describes the process and supported cards.

The goal is faster selected FP16, BF16 and TF32 matrix operations. It is not a general GPU speed boost. The project says quantized Ollama generation often gains little or nothing. Its performance figures are claims from user reports; this review did not run benchmarks. An [independent user report](https://www.reddit.com/r/StableDiffusion/comments/1xdoh8k/i_tested_the_rtx_30series_gpu_unlock_up_to_59/) reports gains on a different GPU and workload.

## Risks and limits

- Installation needs administrator access and adds a kernel module and firmware to the boot process. A kernel module has extensive system access.
- Firmware exploits and GPU resets can cause crashes, boot or display problems, and data loss. More compute can increase heat or power use. Long-term hardware effects are not established here.
- The inspected Makefile uses `sudo` for package installation. The firmware fetch script downloads NVIDIA inputs. A search of the source and packaging found no clear credential collection or exfiltration code. This was not a line-by-line audit, and downloaded dependencies were not audited.
- The author warns about unofficial Windows installers. Do not assume that third-party downloads are related to the GitHub project.
- A cybersecurity flag does not establish malware. The firmware security bypass and privileged kernel code could explain the flag. Only the service provider can say what triggered it.

## Local read-only check

`lspci -nn` identified `NVIDIA Corporation GA107GLM [RTX A2000 8GB Laptop GPU] [10de:25ba]`. `nvidia-smi` reported 8192 MiB of GPU memory and driver `615.71.09`. These commands describe the machine that ran the check, not any remote GPU server. No unlock, installation, GPU benchmark, or hardware change was performed.
