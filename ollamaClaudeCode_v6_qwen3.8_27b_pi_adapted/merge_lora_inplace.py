#!/usr/bin/env python3
"""Merge a GGUF LoRA adapter into a GGUF base model, in place.

Why: Ollama 0.40.11 refuses ADAPTER ("LoRA adapters are no longer supported"), and
llama-export-lora writes F16 output (54 GB for a 27B model), which does not fit this laptop.
A Q8_0 tensor with a delta added and quantized again has the same byte size, so the merge
can overwrite the base file and needs no extra disk.

W' = W + (alpha / r) * B @ A, per adapted tensor. In numpy order a GGUF tensor with
ne = [n_in, n_out] is (n_out, n_in); lora_a is (r, n_in), lora_b is (n_out, r).

Usage: merge_lora_inplace.py BASE.gguf LORA.gguf [--dry-run]
The base file is changed. Keep the download hash to know the original.
"""
import sys

import numpy as np
import gguf

SUPPORTED = {gguf.GGMLQuantizationType.Q8_0, gguf.GGMLQuantizationType.F16,
             gguf.GGMLQuantizationType.F32}


def lora_pairs(lora):
    a, b = {}, {}
    for t in lora.tensors:
        if t.name.endswith(".lora_a"):
            a[t.name[:-7]] = t
        elif t.name.endswith(".lora_b"):
            b[t.name[:-7]] = t
    if set(a) != set(b):
        raise SystemExit(f"unpaired LoRA tensors: {sorted(set(a) ^ set(b))[:5]}")
    return {k: (a[k], b[k]) for k in a}


def field(reader, key):
    f = reader.fields.get(key)
    return None if f is None else f.parts[f.data[0]]


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    dry = "--dry-run" in argv
    lora = gguf.GGUFReader(argv[2])
    if bytes(field(lora, "adapter.type")).decode() != "lora":
        raise SystemExit("not a LoRA adapter")
    alpha = float(field(lora, "adapter.lora.alpha")[0])
    base = gguf.GGUFReader(argv[1], "r" if dry else "r+")
    if bytes(field(base, "general.architecture")).decode() != bytes(field(lora, "general.architecture")).decode():
        raise SystemExit("architecture differs between base and LoRA")
    tensors = {t.name: t for t in base.tensors}
    pairs = lora_pairs(lora)
    missing = [k for k in pairs if k not in tensors]
    if missing:
        raise SystemExit(f"{len(missing)} LoRA targets are not in the base, e.g. {missing[:3]}")
    done, rel = 0, []
    for name in sorted(pairs, key=lambda n: tensors[n].data_offset):
        ta, tb = pairs[name]
        t = tensors[name]
        if t.tensor_type not in SUPPORTED:
            raise SystemExit(f"{name}: base type {t.tensor_type.name} not supported")
        A = np.asarray(ta.data, dtype=np.float32)          # (r, n_in)
        B = np.asarray(tb.data, dtype=np.float32)          # (n_out, r)
        r = A.shape[0]
        if B.shape[1] != r:
            raise SystemExit(f"{name}: rank mismatch {A.shape} {B.shape}")
        W = gguf.quants.dequantize(t.data, t.tensor_type)  # (n_out, n_in)
        if W.shape != (B.shape[0], A.shape[1]):
            raise SystemExit(f"{name}: shape mismatch W{W.shape} B{B.shape} A{A.shape}")
        delta = (alpha / r) * (B @ A)
        rel.append(float(np.linalg.norm(delta) / np.linalg.norm(W)))
        if not dry:
            q = gguf.quants.quantize(W + delta, t.tensor_type)
            if q.shape != t.data.shape or q.dtype != t.data.dtype:
                raise SystemExit(f"{name}: requantized layout differs {q.shape} vs {t.data.shape}")
            t.data[...] = q
        done += 1
        if done % 32 == 0:
            print(f"{done}/{len(pairs)} {name} |dW|/|W| {rel[-1]:.4f}", flush=True)
    if not dry:
        base.data.flush()
    print(f"MERGED {done} tensors, scale {alpha}/{r}, |dW|/|W| median {np.median(rel):.4f} "
          f"max {max(rel):.4f}{' (dry run, nothing written)' if dry else ''}")


if __name__ == "__main__":
    main(sys.argv)
