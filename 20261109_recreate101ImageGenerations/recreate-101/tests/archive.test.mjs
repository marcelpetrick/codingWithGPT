// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Archived runs keep only every 10th frame and the last frame, as AVIF, and no checkpoint GIFs.
// The tests store PNG bytes under the .avif name: ImageMagick reads the content, so no AVIF codec is needed.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {frameFile} from '../scripts/drift.mjs';

const script = name => fileURLToPath(new URL(`../scripts/${name}.mjs`, import.meta.url));
const node = (name, ...a) => spawnSync(process.execPath, [script(name), ...a], {encoding: 'utf8'});

function archivedRun(iterations) {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'recreate-archive-'));
  const input = path.join(d, 'source.png');
  assert.equal(spawnSync('convert', ['-size', '30x20', 'xc:teal', input]).status, 0);
  const dir = node('host', 'init', '--input', input, '--iterations', String(iterations), '--output-dir', d).stdout.trim();
  for (let i = 0; i < iterations; i++) {
    assert.equal(node('host', 'next', '--run-dir', dir).status, 0);
    const r = node('host', 'accept', '--run-dir', dir, '--image', input);
    assert.equal(r.status, 0, r.stderr);
  }
  fs.rmSync(path.join(dir, 'checkpoints'), {recursive: true, force: true});
  for (const f of fs.readdirSync(path.join(dir, 'frames'))) {
    const n = Number(f.slice(0, 4));
    const p = path.join(dir, 'frames', f);
    if (n % 10 === 0 || n === iterations) fs.renameSync(p, p.replace(/\.png$/, '.avif'));
    else fs.rmSync(p);
  }
  return {d, dir};
}

test('frameFile prefers the recorded PNG and falls back to the archived AVIF', () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'recreate-frame-'));
  fs.mkdirSync(path.join(d, 'frames'));
  assert.equal(frameFile(d, 'frames/0001.png'), path.join(d, 'frames/0001.png'));
  fs.writeFileSync(path.join(d, 'frames/0001.avif'), 'x');
  assert.equal(frameFile(d, 'frames/0001.png'), path.join(d, 'frames/0001.avif'));
  fs.writeFileSync(path.join(d, 'frames/0001.png'), 'x');
  assert.equal(frameFile(d, 'frames/0001.png'), path.join(d, 'frames/0001.png'));
});

test('the README table of an archived run links the kept frames and the GIF', () => {
  const {d, dir} = archivedRun(20);
  const readme = path.join(d, 'README.md');
  fs.writeFileSync(readme, '<!-- checkpoints:start -->\nold\n<!-- checkpoints:end -->\n');
  let r = node('host', 'readme', '--run-dir', dir, '--readme', readme);
  assert.equal(r.status, 0, r.stderr);
  let t = fs.readFileSync(readme, 'utf8');
  assert.match(t, /\| 10 \| \[Frame\]\([^)]*frames\/0010\.avif\) \|/);
  assert.match(t, /\| 20 \| \[Frame\]\([^)]*frames\/0020\.avif\) · \[GIF\]\([^)]*evolution\.gif\) \|/);
  assert.doesNotMatch(t, /Checkpoint GIF|Current GIF|old/);
  assert.equal(JSON.parse(node('host', 'status', '--run-dir', dir).stdout).completed, 20);
  assert.match(node('host', 'next', '--run-dir', dir).stderr, /Archived run/);

  const odd = archivedRun(12);
  r = node('host', 'readme', '--run-dir', odd.dir, '--readme', readme);
  assert.equal(r.status, 0, r.stderr);
  t = fs.readFileSync(readme, 'utf8');
  assert.match(t, /\| 10 \| \[Frame\]\([^)]*frames\/0010\.avif\) \|/);
  assert.match(t, /\| 12 \| \[Current GIF\]/);
});

test('comparison and overview read archived AVIF frames', () => {
  const {d, dir} = archivedRun(10);
  const readme = path.join(d, 'README.md');
  fs.writeFileSync(readme, '<!-- comparison:start -->\n<!-- comparison:end -->\n<!-- overview:start -->\n<!-- overview:end -->\n');
  let r = node('compare', '--readme', readme, '--out', path.join(d, 'cmp'), '--run', `A=${dir}`);
  assert.equal(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(d, 'cmp', `${path.basename(dir)}-0010.jpg`)));
  r = node('overview', '--readme', readme, '--out', path.join(d, 'cmp'), '--run', `A=${dir}`);
  assert.equal(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(d, 'cmp', `overview-${path.basename(dir)}-last.jpg`)));
});
