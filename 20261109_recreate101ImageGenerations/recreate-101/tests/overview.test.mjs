// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {distance, replaceBlock} from '../scripts/drift.mjs';

const host = fileURLToPath(new URL('../scripts/host.mjs', import.meta.url));
const overview = fileURLToPath(new URL('../scripts/overview.mjs', import.meta.url));
const h = (...a) => spawnSync(process.execPath, [host, ...a], {encoding: 'utf8'});
const o = (...a) => spawnSync(process.execPath, [overview, ...a], {encoding: 'utf8'});
const hasMagick7 = spawnSync('magick', ['-version']).status === 0;

test('drift distance is zero for one image and positive for two different images', () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'recreate-drift-'));
  const a = path.join(d, 'a.png');
  const b = path.join(d, 'b.png');
  spawnSync('convert', ['-size', '64x64', 'gradient:white-black', a]);
  spawnSync('convert', ['-size', '64x64', 'gradient:black-white', b]);
  if (hasMagick7) {
    assert.equal(distance(a, a), '0.000');
    assert.ok(Number(distance(a, b)) > 0.1, distance(a, b));
  } else {
    assert.equal(distance(a, b), 'n/a');
  }
  assert.equal(distance(a, path.join(d, 'missing.png')), 'n/a');
  assert.equal(replaceBlock('x<!-- k:start -->old<!-- k:end -->y', 'k', ['new']), 'x<!-- k:start -->\nnew\n<!-- k:end -->y');
  assert.throws(() => replaceBlock('none', 'k', []), /no k markers/);
});

test('overview lists runs and prompts from the data', () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'recreate-overview-'));
  const input = path.join(d, 's.png');
  spawnSync('convert', ['-size', '30x20', 'xc:navy', input]);
  const other = path.join(d, 't.png');
  spawnSync('convert', ['-size', '30x20', 'xc:orange', other]);
  const skill = path.join(d, 'SKILL.md');
  fs.writeFileSync(skill, '# Skill\n\n> Copy the image | exactly.\n');
  const v2 = path.join(d, 'prompt-v2.txt');
  fs.writeFileSync(v2, 'Copy it\nexactly.\n');

  const a = h('init', '--input', input, '--iterations', '1', '--output-dir', d).stdout.trim();
  h('next', '--run-dir', a);
  h('accept', '--run-dir', a, '--image', other);
  const b = h('init', '--input', input, '--iterations', '3', '--output-dir', d, '--provider', 'comfy-test', '--prompt-file', v2).stdout.trim();
  h('next', '--run-dir', b);

  const readme = path.join(d, 'README.md');
  fs.writeFileSync(readme, 'x\n<!-- overview:start -->\nold\n<!-- overview:end -->\n<!-- prompts:start -->\n<!-- prompts:end -->\n');
  const cmp = path.join(d, 'cmp');
  const r = o('--readme', readme, '--out', cmp, '--run', `A=${a}`, '--run', `B=${b}`, '--prompt', `v1=${skill}`, '--prompt', `prompt-v2=${v2}`, '--prompt', `v9=${v2}`);
  assert.equal(r.status, 0, r.stderr);
  const t = fs.readFileSync(readme, 'utf8');
  assert.doesNotMatch(t, /old/);
  assert.match(t, /\| \[A\]\([^)]+\/\) \| <img [^|]*source"> \| <img [^|]*generation 1"><br>gen 1, d = (0\.\d{3}|n\/a) · \[GIF\]\([^)]+evolution\.gif\) \| `codex-host-image-tool` \| v1 \| 1 \/ 1 \| complete \|/);
  assert.match(t, /\| \[B\]\([^)]+\/\) \| .*gen 0, d = 0\.000 \| `comfy-test` \| prompt-v2 \| 0 \/ 3 \| request pending \|/);
  assert.match(t, /\| \[v1\]\(SKILL\.md\) \| Copy the image \\\| exactly\. \| A \|/);
  assert.match(t, /\| \[prompt-v2\]\(prompt-v2\.txt\) \| Copy it exactly\. \| B \|/);
  assert.match(t, /\| \[v9\]\(prompt-v2\.txt\) \| Copy it exactly\. \| — \|/);
  assert.ok(fs.existsSync(path.join(cmp, `overview-${path.basename(a)}-last.jpg`)));

  // Without --prompt the prompts block stays as it is; a run without a GIF gets no link.
  fs.rmSync(path.join(b, 'evolution.gif'), {force: true});
  assert.equal(o('--readme', readme, '--out', cmp, '--run', `B=${b}`, '--default-prompt', 'v0').status, 0);
  assert.doesNotMatch(fs.readFileSync(readme, 'utf8'), /\[B\][^\n]*GIF/);

  const empty = path.join(d, 'empty.txt');
  fs.writeFileSync(empty, '  \n');
  for (const bad of [
    [],
    ['--readme', readme],
    ['--readme', readme, '--out', cmp],
    ['--readme', readme, '--out', cmp, '--run', 'noequals'],
    ['--readme', readme, '--out', cmp, '--run', `A=${a}`, '--prompt', `e=${empty}`],
    ['--x'],
  ]) assert.notEqual(o(...bad).status, 0, bad.join(' '));
  fs.writeFileSync(readme, 'no markers\n');
  assert.notEqual(o('--readme', readme, '--out', cmp, '--run', `A=${a}`).status, 0);
});
