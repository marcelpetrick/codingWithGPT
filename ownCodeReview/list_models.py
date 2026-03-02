#!/usr/bin/env python3
import argparse
import json
import sys
import time
import urllib.request
import urllib.error

DEFAULT_HOST = "http://192.168.100.32:11434"
TAGS_PATH = "/api/tags"
GENERATE_PATH = "/api/generate"


def http_get_json(url: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def http_post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def ns_to_ms(ns: int) -> float:
    return ns / 1_000_000.0


def safe_int(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def make_input_prompt_approx_tokens(target_tokens: int) -> str:
    """
    Ollama doesn't expose a tokenizer via this API.
    We approximate by repeating a fixed sentence; for most BPE tokenizers,
    ~0.75–1.3 tokens per word depending on language/content.

    Goal: create a prompt that is "around" target_tokens.
    This is good enough for a fast comparative benchmark.
    """
    sentence = (
        "Benchmark input: please read this text carefully and acknowledge with a short summary."
    )
    # sentence word count ~14; assume ~16-20 tokens depending on tokenizer
    # Repeat enough times to land near target_tokens
    approx_tokens_per_sentence = 18
    reps = max(1, target_tokens // approx_tokens_per_sentence)
    return (" ".join([sentence] * reps)) + "\n\nNow respond with exactly three bullet points."


def list_models(host: str) -> list[str]:
    url = host.rstrip("/") + TAGS_PATH
    data = http_get_json(url, timeout=10)
    models = data.get("models", []) or []
    names = []
    for m in models:
        name = m.get("name")
        if name:
            names.append(name)
    return names


def benchmark_model(
    host: str,
    model: str,
    input_tokens: int,
    num_predict: int,
    verbose: bool,
    timeout: int,
) -> tuple[bool, str]:
    """
    Returns (ok, output_line_or_error_message)
    """
    url = host.rstrip("/") + GENERATE_PATH

    prompt = make_input_prompt_approx_tokens(input_tokens)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            # Keep deterministic-ish and comparable
            "temperature": 0,
            # Limit output so the whole run stays fast
            "num_predict": num_predict,
        },
    }

    t0 = time.perf_counter()
    try:
        resp = http_post_json(url, payload, timeout=timeout)
    except urllib.error.HTTPError as e:
        # Try to read body if present
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return False, f"{model}: HTTPError {e.code} {e.reason} {body}".strip()
    except Exception as e:
        return False, f"{model}: Error calling /api/generate: {e}"

    wall_s = max(1e-9, time.perf_counter() - t0)

    # Ollama response commonly includes:
    # total_duration, load_duration, prompt_eval_duration, eval_duration (nanoseconds)
    # prompt_eval_count, eval_count
    total_ns = safe_int(resp.get("total_duration", 0))
    load_ns = safe_int(resp.get("load_duration", 0))
    prompt_eval_ns = safe_int(resp.get("prompt_eval_duration", 0))
    eval_ns = safe_int(resp.get("eval_duration", 0))

    prompt_eval_count = safe_int(resp.get("prompt_eval_count", 0))
    eval_count = safe_int(resp.get("eval_count", 0))

    # Throughput: prefer eval_duration if available
    tok_s = None
    if eval_ns > 0 and eval_count > 0:
        tok_s = eval_count / (eval_ns / 1_000_000_000.0)

    # Summary line (compact)
    parts = [
        f"{model}",
        f"wall={wall_s*1000:.0f}ms",
    ]
    if tok_s is not None:
        parts.append(f"gen={eval_count}tok")
        parts.append(f"{tok_s:.1f} tok/s")
    else:
        parts.append(f"gen={eval_count}tok")

    line = " | ".join(parts)

    if verbose:
        # Verbose block in one line (still readable)
        line += (
            " || "
            f"total={ns_to_ms(total_ns):.0f}ms "
            f"load={ns_to_ms(load_ns):.0f}ms "
            f"prompt_eval={ns_to_ms(prompt_eval_ns):.0f}ms({prompt_eval_count}tok) "
            f"eval={ns_to_ms(eval_ns):.0f}ms({eval_count}tok)"
        )

    return True, line


def main():
    ap = argparse.ArgumentParser(description="List Ollama models; optionally benchmark each model.")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"Ollama host (default: {DEFAULT_HOST})")
    ap.add_argument("--benchmark", action="store_true", help="Run a quick per-model benchmark")
    ap.add_argument("--verbose", action="store_true", help="Show verbose timing like ollama --verbose")
    ap.add_argument(
        "--input-tokens",
        type=int,
        default=1000,
        help="Approx input tokens used for the benchmark prompt (default: 1000)",
    )
    ap.add_argument(
        "--num-predict",
        type=int,
        default=128,
        help="Max output tokens for benchmark (default: 128; keep small to finish fast)",
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout seconds per model benchmark call (default: 60)",
    )
    args = ap.parse_args()

    host = args.host.rstrip("/")

    # Get model list
    try:
        names = list_models(host)
    except Exception as e:
        print(f"Error connecting to Ollama at {host}{TAGS_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    if not names:
        print("No models found.")
        return

    # Default behavior: just list names
    if not args.benchmark:
        for name in names:
            print(name)
        return

    # Benchmark mode
    # Keep total runtime short: this is a single request per model with small output.
    for name in names:
        ok, msg = benchmark_model(
            host=host,
            model=name,
            input_tokens=args.input_tokens,
            num_predict=args.num_predict,
            verbose=args.verbose,
            timeout=args.timeout,
        )
        if ok:
            print(msg)
        else:
            # Print errors but continue benchmarking other models
            print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
