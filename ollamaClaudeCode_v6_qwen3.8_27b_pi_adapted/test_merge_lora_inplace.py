"""Test merge_lora_inplace.py on a tiny synthetic Q8_0 base and F16 LoRA.

Run: ~/.cache/v6-venv/bin/python -m pytest -q test_merge_lora_inplace.py
"""
import importlib.util
import pathlib

import numpy as np
import gguf
import pytest

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("merge", HERE / "merge_lora_inplace.py")
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)

Q8 = gguf.GGMLQuantizationType.Q8_0
RNG = np.random.default_rng(7)
N_IN, N_OUT, R, ALPHA = 64, 96, 4, 8.0


def write_base(path, w, other):
    wr = gguf.GGUFWriter(str(path), "qwen35")
    wr.add_tensor("blk.0.ffn_up.weight", gguf.quants.quantize(w, Q8), raw_dtype=Q8)
    wr.add_tensor("blk.0.ffn_down.weight", gguf.quants.quantize(other, Q8), raw_dtype=Q8)
    wr.write_header_to_file(); wr.write_kv_data_to_file(); wr.write_tensors_to_file(); wr.close()


def write_lora(path, a, b, arch="qwen35", pair=True):
    wr = gguf.GGUFWriter(str(path), arch)
    wr.add_string("adapter.type", "lora")
    wr.add_float32("adapter.lora.alpha", ALPHA)
    wr.add_tensor("blk.0.ffn_up.weight.lora_a", a.astype(np.float16))
    if pair:
        wr.add_tensor("blk.0.ffn_up.weight.lora_b", b.astype(np.float16))
    wr.write_header_to_file(); wr.write_kv_data_to_file(); wr.write_tensors_to_file(); wr.close()


def read(path, name):
    t = next(t for t in gguf.GGUFReader(str(path)).tensors if t.name == name)
    return gguf.quants.dequantize(t.data, t.tensor_type)


@pytest.fixture
def files(tmp_path):
    w = RNG.normal(0, 0.05, (N_OUT, N_IN)).astype(np.float32)
    other = RNG.normal(0, 0.05, (N_IN, N_OUT)).astype(np.float32)
    a = RNG.normal(0, 0.05, (R, N_IN)).astype(np.float32)
    b = RNG.normal(0, 0.05, (N_OUT, R)).astype(np.float32)
    base, lora = tmp_path / "base.gguf", tmp_path / "lora.gguf"
    write_base(base, w, other)
    write_lora(lora, a, b)
    return base, lora, w, other, a, b


def test_merge_adds_scaled_delta_and_keeps_size(files):
    base, lora, w, other, a, b = files
    size = base.stat().st_size
    before_other = read(base, "blk.0.ffn_down.weight")
    merge.main(["x", str(base), str(lora)])
    assert base.stat().st_size == size
    a16, b16 = a.astype(np.float16).astype(np.float32), b.astype(np.float16).astype(np.float32)
    expect = w + (ALPHA / R) * (b16 @ a16)
    got = read(base, "blk.0.ffn_up.weight")
    assert np.abs(got - expect).max() < 2e-3          # Q8_0 rounding only
    assert np.abs(got - w).max() > 1e-2               # the delta is really there
    assert np.array_equal(read(base, "blk.0.ffn_down.weight"), before_other)


def test_dry_run_writes_nothing(files):
    base, lora, *_ = files
    raw = base.read_bytes()
    merge.main(["x", str(base), str(lora), "--dry-run"])
    assert base.read_bytes() == raw


def test_refuses_wrong_architecture(tmp_path, files):
    base, _, _, _, a, b = files
    other = tmp_path / "llama.gguf"
    write_lora(other, a, b, arch="llama")
    with pytest.raises(SystemExit, match="architecture"):
        merge.main(["x", str(base), str(other)])


def test_refuses_unpaired_tensor(tmp_path, files):
    base, _, _, _, a, b = files
    bad = tmp_path / "bad.gguf"
    write_lora(bad, a, b, pair=False)
    with pytest.raises(SystemExit, match="unpaired"):
        merge.main(["x", str(base), str(bad)])


def test_refuses_shape_mismatch(tmp_path, files):
    base, _, _, _, a, b = files
    bad = tmp_path / "t.gguf"
    write_lora(bad, a[:, :32], b)
    with pytest.raises(SystemExit, match="shape mismatch"):
        merge.main(["x", str(base), str(bad)])


def test_usage_without_arguments():
    with pytest.raises(SystemExit):
        merge.main(["x"])
