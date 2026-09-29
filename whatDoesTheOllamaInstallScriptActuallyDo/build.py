#!/usr/bin/env python3
"""Render index.html from page.template.html, install.sh and the archive listing.

The listing, hash, line count and archive table are derived from the files in this
folder, so the page cannot drift from the script copy it describes. Re-fetch with
`./refresh.sh`, then run this again.
"""
import hashlib
import html
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "install.sh"
LISTING = HERE / "ollama-linux-amd64.contents.txt"
FETCHED = HERE / "FETCHED"  # one line: "<UTC date> <release tag>"

# A line is highlighted when it runs a command through $SUDO / sudo. L380 only builds SUDO_E.
SUDO_RE = re.compile(r"\$SUDO(_E)?\b|^\s*(\|\|\s*)?sudo |\|\| *\\?\s*sudo |^\s+sudo ")
NOT_A_SUDO_CALL = {380}

# Archive groups: (label, predicate on path, explanation). First match wins.
GROUPS = [
    ("bin/ollama", lambda p: p == "bin/ollama",
     "The Go binary: CLI, HTTP server, scheduler and model store in one executable."),
    ("lib/ollama/cuda_v12/", lambda p: p.startswith("lib/ollama/cuda_v12/"),
     "CUDA 12 runtime, cuBLAS/cuBLASLt and the ggml CUDA backend, for older NVIDIA drivers."),
    ("lib/ollama/cuda_v13/", lambda p: p.startswith("lib/ollama/cuda_v13/"),
     "The same for CUDA 13, which needs a recent (580-series or newer) driver. Ollama picks one at runtime."),
    ("lib/ollama/vulkan/", lambda p: p.startswith("lib/ollama/vulkan/"),
     "Vulkan backend, a vendor-neutral GPU path (Intel, AMD, NVIDIA)."),
    ("lib/ollama/libggml-cpu-*.so", lambda p: p.startswith("lib/ollama/libggml-cpu"),
     "One CPU backend per x86 microarchitecture (SSE4.2 to Sapphire Rapids and Zen 4). The best one your CPU supports is loaded."),
    ("llama.cpp libraries", lambda p: re.match(r"lib/ollama/(libggml|libllama|libmtmd|llama-)", p) is not None,
     "ggml core, libllama, libmtmd (multimodal), plus llama.cpp's own <code>llama-server</code> and <code>llama-quantize</code>."),
    ("libgomp", lambda p: "libgomp" in p, "GNU OpenMP runtime used by the CPU backends."),
    ("licenses", lambda p: re.search(r"_(LICENSE|NOTICE)$", p) is not None,
     "Third-party license texts (llama.cpp, MLX, xgrammar, Go, …)."),
    ("other", lambda p: True, "Anything not covered above."),
]


def fmt_size(n: int) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f} GB"
    if n >= 1e6:
        return f"{n / 1e6:.1f} MB"
    return f"{n / 1e3:.0f} kB"


def render_listing(lines: list[str]) -> str:
    out = []
    for n, raw in enumerate(lines, 1):
        cls = []
        if SUDO_RE.search(raw) and n not in NOT_A_SUDO_CALL:
            cls.append("r")
        if raw.lstrip().startswith("#"):
            cls.append("c")
        c = f' {" ".join(cls)}' if cls else ""
        out.append(f'<div class="l{c}" id="L{n}"><span class="no"><a href="#L{n}">{n}</a></span>'
                   f'<span class="tx">{html.escape(raw) or " "}</span></div>')
    return "\n".join(out)


def parse_archive() -> list[tuple[str, int, str]]:
    """Return (path, size, owner) per regular file or symlink in `tar -tv` output."""
    entries = []
    for line in LISTING.read_text().splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6 or parts[0].startswith("d"):
            continue
        path = parts[5].split(" -> ")[0]
        entries.append((path, int(parts[2]), parts[1]))
    return entries


def render_archive(entries) -> tuple[str, str]:
    totals = {g[0]: [0, 0] for g in GROUPS}
    for path, size, _ in entries:
        label = next(g[0] for g in GROUPS if g[1](path))
        totals[label][0] += size
        totals[label][1] += 1
    total = sum(s for _, s, _ in entries)
    owners = sorted({o for _, _, o in entries})
    rows = []
    for label, _, why in GROUPS:
        size, count = totals[label]
        if not count:
            continue
        pct = 100 * size / total
        rows.append(f"<tr><td><code>{html.escape(label)}</code></td><td>{count}</td>"
                    f'<td style="white-space:nowrap">{fmt_size(size)}</td><td>{pct:.0f}%</td><td>{why}</td></tr>')
    cuda = totals["lib/ollama/cuda_v12/"][0] + totals["lib/ollama/cuda_v13/"][0]
    section = f"""
<p>We streamed <code>ollama-linux-amd64.tar.zst</code> through <code>tar -tv</code> without writing it to disk. The full listing is in
<a href="ollama-linux-amd64.contents.txt"><code>ollama-linux-amd64.contents.txt</code></a>. It has {len(entries)} files and symlinks,
<b>{fmt_size(total)} unpacked</b>, and every entry is owned by <code>{html.escape(", ".join(owners))}</code>. So although root's <code>tar</code> preserves
the owners recorded in the archive, they end up <code>root:root</code>, which is what you want.</p>
<div class="table-wrap"><table>
<tr><th>Part</th><th>Files</th><th>Size</th><th>Share</th><th>What it is</th></tr>
{"".join(rows)}
</table></div>
<p><b>{fmt_size(cuda)} ({100 * cuda / total:.0f}%) is NVIDIA's CUDA libraries.</b> They're installed on every amd64 machine, including CPU-only and AMD ones,
because the archive is the same for everyone. The GPU choice only decides what is installed <em>on top</em> (ROCm for AMD, a driver for NVIDIA).
The binary itself is small ({fmt_size(totals["bin/ollama"][0])}). The server doesn't do the maths itself: it starts runner processes backed by these ggml/llama.cpp libraries.</p>"""
    summary = f"{fmt_size(total)}, {fmt_size(cuda)} of it CUDA"
    return section, summary


def main() -> None:
    script = SCRIPT.read_text()
    lines = script.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    fetched = FETCHED.read_text().strip() if FETCHED.exists() else "unknown date"
    archive_section, archive_summary = render_archive(parse_archive())
    page = (HERE / "page.template.html").read_text()
    subs = {
        "{{FETCHED}}": html.escape(fetched),
        "{{LINES}}": str(len(lines)),
        "{{SHA256}}": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        "{{LISTING}}": render_listing(lines),
        "{{ARCHIVE_SECTION}}": archive_section,
        "{{ARCHIVE_SUMMARY}}": html.escape(archive_summary),
    }
    for k, v in subs.items():
        page = page.replace(k, v)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftover:
        raise SystemExit(f"unreplaced placeholders: {leftover}")
    tmp = HERE / "index.html.new"
    tmp.write_text(page)
    os.replace(tmp, HERE / "index.html")
    print(f"index.html: {len(lines)} script lines, "
          f"{sum(1 for i, l in enumerate(lines, 1) if SUDO_RE.search(l) and i not in NOT_A_SUDO_CALL)} sudo lines")


if __name__ == "__main__":
    main()
