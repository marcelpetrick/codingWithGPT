# GPU unlock check

## Verdict

The upstream project appears to implement a GPU performance unlock. The reviewed laptop GPU is not in its device table. A limited source review found no clear credential-stealing code. This does not prove safety.

## Plan

1. Inspect upstream documentation and source. Allow 10 minutes.
2. Read local GPU details without changing hardware. Allow 2 minutes.
3. Record the result and commit it. Allow 5 minutes.

## Status

| Time, Europe/Berlin | Step | Result |
|---|---|---|
| 2026-11-09 15:52 | Inspect upstream | Reviewed README, device table, Makefile, and targeted source search. |
| 2026-11-09 15:52 | Check local GPU | Found RTX A2000 laptop, GA107, PCI ID `10de:25ba`. |
| 2026-11-09 15:54 | Record result | Added README. No unlock or benchmark was run. |

## Results

See `README.md`. Upstream commit: `7eb51bccae0a0b7e599e084d971170e9a1e82d0c`. The review did not audit every source line or downloaded dependency.

## Resume here

The review is complete for the local machine. For another machine, read its GPU details and compare the PCI ID to the upstream device table. Do not install or run the unlock without a separate decision.

Check commands:

```sh
lspci -nn | rg -i 'vga|3d|display|nvidia|amd'
nvidia-smi
git status --short
```

Restart the source review with:

```sh
git clone https://github.com/Zagitta/gpu-unlock.git /tmp/gpu-unlock-review
git -C /tmp/gpu-unlock-review rev-parse HEAD
rg -n '25ba|GA107' /tmp/gpu-unlock-review/kernel/gpu_unlock/recipes.c
```
