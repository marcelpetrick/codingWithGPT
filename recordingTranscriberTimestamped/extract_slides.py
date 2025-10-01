#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extracts slide images from a Zoom-like recording:
- Detects the slide region automatically via temporal stability (low motion).
- Avoids human faces (penalizes regions where faces are seen).
- Samples 1 frame/second, crops to the slide ROI.
- Uses perceptual hashing (dHash) to cluster "same slide".
- For each cluster, keeps ONLY the latest (to capture annotations added later).
- Saves slide_000.png, slide_001.png, ... to the output directory.

Linux-friendly. Requires: python3, opencv-python, numpy.
Optional: OpenCV Haar cascades (bundled with cv2) for face penalty.
"""

import os
import cv2
import math
import argparse
import numpy as np
from pathlib import Path

# ---------- Utility: robust video read at a specific time ----------
def read_frame_at_time(cap, t_seconds, fallback_last=True):
    """Seek to time (in seconds) and grab a frame. Returns (ok, frame[BGR])."""
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_index = max(0, int(round(t_seconds * fps)))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    if not ok and fallback_last:
        # Try stepping back a little in case of seek/decoding edge
        for back in range(1, 4):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_index - back))
            ok, frame = cap.read()
            if ok:
                break
    return ok, frame

# ---------- Fast perceptual hash (dHash) & distance ----------
def dhash_gray(img_gray, hash_size=16):
    """
    dHash: resize to (hash_size+1) x hash_size, compare adjacent pixels horizontally.
    Returns a boolean array (hash_size * hash_size,) you can store as uint8 or bytes.
    """
    small = cv2.resize(img_gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    return diff.flatten()

def hamming_distance(h1, h2):
    return int(np.bitwise_xor(h1, h2).sum())

# ---------- Temporal stability map (low motion areas) ----------
def compute_stability_map(cap, sample_seconds=30, samples_per_sec=2, downscale_width=640):
    """
    Builds a per-pixel temporal stddev map over the first `sample_seconds`,
    downscaled for speed. Returns (std_map (H,W) float32, scale_ratio, first_frame_fullres).
    """
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duration = total_frames / fps if total_frames > 0 else sample_seconds

    end_time = min(sample_seconds, duration)
    times = np.linspace(0, end_time, max(2, int(end_time * samples_per_sec)), endpoint=False)

    frames_small = []
    first_frame_fullres = None
    for i, t in enumerate(times):
        ok, frame = read_frame_at_time(cap, t)
        if not ok:
            continue
        if first_frame_fullres is None:
            first_frame_fullres = frame.copy()
        # Downscale & grayscale
        h, w = frame.shape[:2]
        scale = downscale_width / float(w)
        new_w = int(downscale_width)
        new_h = max(1, int(round(h * scale)))
        small = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        frames_small.append(gray)

    if len(frames_small) < 2:
        raise RuntimeError("Not enough frames to compute stability map.")

    stack = np.stack(frames_small, axis=0).astype(np.float32)  # (T,H,W)
    std_map = np.std(stack, axis=0)  # temporal stddev per pixel
    return std_map, (first_frame_fullres.shape[1] / std_map.shape[1],
                     first_frame_fullres.shape[0] / std_map.shape[0]), first_frame_fullres

# ---------- Optional: face penalty using Haar cascade ----------
def load_face_cascade():
    # Uses the default Haar cascade that ships with OpenCV installs
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    if not os.path.exists(cascade_path):
        return None
    return cv2.CascadeClassifier(cascade_path)

def face_penalty(gray_roi_small, face_cascade):
    """
    Returns a penalty scalar based on number/size of faces detected.
    Operates on downscaled grayscale ROI for speed.
    """
    if face_cascade is None:
        return 0.0
    faces = face_cascade.detectMultiScale(gray_roi_small, scaleFactor=1.1, minNeighbors=4,
                                          minSize=(24, 24))
    if len(faces) == 0:
        return 0.0
    # Penalize more for more/larger faces
    areas = [w*h for (x, y, w, h) in faces]
    return float(sum(areas))  # simple heuristic

# ---------- ROI search over stability map using integral image ----------
def find_low_motion_roi(std_map, scale_ratio_xy, expected_aspect=16/9, aspect_tolerance=0.25,
                        min_rel_width=0.35, max_rel_width=0.95, stride=8):
    """
    Finds the rectangle (on the downscaled stability map) with the smallest summed stddev
    (i.e., least motion), with aspect ratio near expected_aspect and width within given bounds.
    Returns ROI in full-res coordinates: (x, y, w, h).
    """
    H, W = std_map.shape[:2]
    int_img = cv2.integral(std_map)  # (H+1, W+1)
    face_cascade = load_face_cascade()

    # Precompute a blurred grayscale for face penalty at map scale
    std_norm = cv2.normalize(std_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    best_score = math.inf
    best_rect = None

    # width candidates in pixels (downscaled grid)
    min_w = int(W * min_rel_width)
    max_w = int(W * max_rel_width)
    if min_w >= max_w:
        min_w, max_w = int(W*0.4), int(W*0.9)

    widths = list(range(min_w, max_w+1, max(1, (max_w - min_w)//10 or 1)))
    for w in widths:
        # compute corresponding heights around expected aspect ratio
        h_nominal = int(round(w / expected_aspect))
        for delta in (-aspect_tolerance, 0.0, aspect_tolerance):
            h = int(round(w / (expected_aspect + delta))) if expected_aspect + delta > 0 else h_nominal
            if h < int(H*0.3) or h > int(H*0.98):
                continue

            for y in range(0, H - h, stride):
                y2 = y + h
                for x in range(0, W - w, stride):
                    x2 = x + w
                    # Sum over rect via integral image
                    s = int_img[y2, x2] - int_img[y, x2] - int_img[y2, x] + int_img[y, x]

                    # Face penalty (discourage selecting regions with faces)
                    roi_small = std_norm[y:y2, x:x2]
                    # Downscale roi for fast face check
                    roi_small_ds = cv2.resize(roi_small, (max(64, w//4), max(36, h//4)), interpolation=cv2.INTER_AREA)
                    p = face_penalty(roi_small_ds, face_cascade)

                    score = s + 5.0 * p  # weight faces strongly
                    if score < best_score:
                        best_score = score
                        best_rect = (x, y, w, h)

    if best_rect is None:
        raise RuntimeError("Failed to find a stable ROI.")

    # Map back to full-res coordinates
    sx, sy = scale_ratio_xy  # (x-scale, y-scale)
    x, y, w, h = best_rect
    x_full = int(round(x * sx))
    y_full = int(round(y * sy))
    w_full = int(round(w * sx))
    h_full = int(round(h * sy))
    return (x_full, y_full, w_full, h_full)

# ---------- Main extraction pipeline ----------
def extract_slides(
    input_path: str,
    output_dir: str,
    sample_hz: float = 1.0,
    max_probe_seconds: int = 30,
    hash_size: int = 16,
    same_slide_hamming_thresh: int = 20,
    expected_aspect: float = 16/9
):
    """
    - Detects ROI via stability in the first `max_probe_seconds`.
    - Samples at `sample_hz` (e.g., 1 fps), crops to ROI, compares via dHash.
    - Saves slide PNGs, keeping only the latest while content is "same".
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {input_path}")

    # Build stability map on first ~30s
    std_map, scale_ratio_xy, first_frame = compute_stability_map(
        cap, sample_seconds=max_probe_seconds, samples_per_sec=2, downscale_width=640
    )
    roi = find_low_motion_roi(
        std_map, scale_ratio_xy,
        expected_aspect=expected_aspect, aspect_tolerance=0.25,
        min_rel_width=0.35, max_rel_width=0.95, stride=8
    )
    x, y, w, h = roi
    print(f"[INFO] Detected slide ROI (full-res): x={x} y={y} w={w} h={h}")

    # Prepare output folder
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Iterate over video at fixed sampling rate
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if total_frames > 0 else 0
    if duration == 0:
        # Fallback: run until frames stop
        duration = max_probe_seconds

    # State for slide clustering
    slide_idx = 0
    last_hash = None
    last_path = None

    t = 0.0
    step = 1.0 / max(0.0001, sample_hz)  # seconds
    while t <= duration + 1e-6:
        ok, frame = read_frame_at_time(cap, t)
        if not ok:
            t += step
            continue

        # Crop to ROI (clamp bounds just in case)
        H, W = frame.shape[:2]
        xx = max(0, min(W-1, x))
        yy = max(0, min(H-1, y))
        ww = max(1, min(W-xx, w))
        hh = max(1, min(H-yy, h))
        crop = frame[yy:yy+hh, xx:xx+ww]

        # Hash for similarity
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        cur_hash = dhash_gray(gray, hash_size=hash_size)

        if last_hash is None:
            # First slide: save directly
            out_path = os.path.join(output_dir, f"slide_{slide_idx:03d}.png")
            cv2.imwrite(out_path, crop)
            last_hash = cur_hash
            last_path = out_path
        else:
            dist = hamming_distance(cur_hash, last_hash)
            if dist <= same_slide_hamming_thresh:
                # SAME slide -> overwrite to keep the **latest** state
                cv2.imwrite(last_path, crop)
            else:
                # NEW slide -> increment index, save new file, update reference
                slide_idx += 1
                out_path = os.path.join(output_dir, f"slide_{slide_idx:03d}.png")
                cv2.imwrite(out_path, crop)
                last_hash = cur_hash
                last_path = out_path

        t += step

    cap.release()
    print(f"[DONE] Saved {slide_idx + 1} slide(s) to: {output_dir}")

# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(description="Auto-extract slides from a video via stability + hashing.")
    parser.add_argument("input", help="Input video file (e.g., recording.mkv)")
    parser.add_argument("-o", "--output", default="slides_out", help="Output directory for PNGs")
    parser.add_argument("--hz", type=float, default=1.0, help="Sampling rate (frames per second), default: 1.0")
    parser.add_argument("--probe", type=int, default=30, help="Seconds to analyze for ROI detection, default: 30")
    parser.add_argument("--hash-size", type=int, default=16, help="dHash size (>=8), default: 16")
    parser.add_argument("--dist", type=int, default=20, help="Hamming distance threshold for 'same slide', default: 20")
    parser.add_argument("--aspect", type=float, default=16/9, help="Expected slide aspect ratio, default: 16/9")
    args = parser.parse_args()

    extract_slides(
        input_path=args.input,
        output_dir=args.output,
        sample_hz=args.hz,
        max_probe_seconds=args.probe,
        hash_size=args.hash_size,
        same_slide_hamming_thresh=args.dist,
        expected_aspect=args.aspect
    )

if __name__ == "__main__":
    main()
