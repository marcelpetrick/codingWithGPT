// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Shared helpers for the README blocks: drift distance, thumbnails and README block replacement.
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';

// Drift: ImageMagick 7 SSIM distortion against a reference on 256x256 copies (0 = identical).
// Returns 'n/a' when ImageMagick 7 (`magick`) is not available.
export function distance(reference, image) {
  const args = [
    reference, '-resize', '256x256!', '-colorspace', 'sRGB',
    image, '-resize', '256x256!', '-colorspace', 'sRGB',
    '-metric', 'SSIM', '-compare', '-format', '%[distortion]', 'info:',
  ];
  const result = spawnSync('magick', args, {encoding: 'utf8'});
  const value = Number.parseFloat(result.stdout);
  if (result.status !== 0 || !Number.isFinite(value)) return 'n/a';
  return value.toFixed(3);
}

// Write a JPEG thumbnail when it is missing or older than its source.
export function thumbnail(source, target, size = 320) {
  const stale = !fs.existsSync(target) || fs.statSync(target).mtimeMs < fs.statSync(source).mtimeMs;
  if (!stale) return;
  const result = spawnSync('convert', [source, '-resize', `${size}x${size}`, '-quality', '82', target], {encoding: 'utf8'});
  if (result.status !== 0) throw Error(`convert: ${result.stderr}`);
}

// Replace the text between <!-- BLOCK:start --> and <!-- BLOCK:end -->.
export function replaceBlock(text, block, lines) {
  const start = `<!-- ${block}:start -->`;
  const end = `<!-- ${block}:end -->`;
  const i = text.indexOf(start);
  const j = text.indexOf(end);
  if (i < 0 || j < i) throw Error(`README has no ${block} markers`);
  return text.slice(0, i + start.length) + '\n' + lines.join('\n') + '\n' + text.slice(j);
}
