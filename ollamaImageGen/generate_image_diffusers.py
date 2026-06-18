#!/usr/bin/env python3
"""
Text-to-image generation using HuggingFace diffusers + FLUX.1-schnell.

Works on Linux/Windows/macOS with a CUDA GPU (tested: 12 GB VRAM).
Runs locally — model is downloaded to ~/.cache/huggingface/ on first run (~23 GB).

Usage (run ON the machine with the GPU, e.g. SSH into the server):
    pip install diffusers transformers accelerate torch sentencepiece protobuf
    python generate_image_diffusers.py "a red fat cat on a whiteboard"
    python generate_image_diffusers.py "cyberpunk city" --steps 4 --size 1024x1024
    python generate_image_diffusers.py "portrait" --out ~/Desktop/ai_art
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
DEFAULT_STEPS = 4        # schnell is a distilled model; 4 steps is enough
DEFAULT_GUIDANCE = 0.0   # schnell doesn't use CFG
DEFAULT_SIZE = "1024x1024"
DEFAULT_OUT = Path(__file__).parent / "output"


def parse_size(size_str: str) -> tuple[int, int]:
    w, h = size_str.lower().split("x")
    return int(w), int(h)


def load_pipeline(model_id: str, device: str):
    try:
        import torch
        from diffusers import FluxPipeline
    except ImportError:
        sys.exit(
            "Missing packages. Install with:\n"
            "  pip install diffusers transformers accelerate torch sentencepiece protobuf"
        )

    print(f"Loading {model_id} on {device}…")
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    pipe = FluxPipeline.from_pretrained(model_id, torch_dtype=dtype)
    pipe = pipe.to(device)
    return pipe


def generate_image(
    prompt: str,
    steps: int = DEFAULT_STEPS,
    guidance: float = DEFAULT_GUIDANCE,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    model_id: str = DEFAULT_MODEL,
    out_dir: Path = DEFAULT_OUT,
) -> Path:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("Warning: no CUDA GPU found — generation on CPU will be very slow.")

    pipe = load_pipeline(model_id, device)

    generator = torch.Generator(device=device).manual_seed(seed) if seed is not None else None

    print(f"Generating…  prompt={prompt!r}  steps={steps}  {width}x{height}")
    result = pipe(
        prompt=prompt,
        num_inference_steps=steps,
        guidance_scale=guidance,
        width=width,
        height=height,
        generator=generator,
        output_type="pil",
    )
    image = result.images[0]

    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prompt = prompt[:40].replace(" ", "_").replace("/", "-")
    output_path = out_dir / f"{timestamp}_{safe_prompt}.png"
    image.save(output_path)

    print(f"Saved: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate images with FLUX via diffusers (runs locally on GPU)")
    parser.add_argument("prompt", help="Text prompt")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"HuggingFace model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help=f"Inference steps (default: {DEFAULT_STEPS})")
    parser.add_argument("--guidance", type=float, default=DEFAULT_GUIDANCE, help=f"CFG guidance scale (default: {DEFAULT_GUIDANCE})")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="WxH (default: 1024x1024)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory")
    args = parser.parse_args()

    w, h = parse_size(args.size)
    generate_image(
        prompt=args.prompt,
        steps=args.steps,
        guidance=args.guidance,
        width=w,
        height=h,
        seed=args.seed,
        model_id=args.model,
        out_dir=Path(args.out),
    )


if __name__ == "__main__":
    main()
