#!/usr/bin/env node
// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Build the README overview of all runs and all prompts from the run manifests and the prompt files.
// Usage: overview.mjs --readme README.md --out comparison --run "Label=run-dir" [--run ...]
//                     --prompt "id=file" [--prompt ...] [--default-prompt v1]
// Blocks: <!-- overview:start/end --> (runs) and <!-- prompts:start/end --> (prompts).
// A prompt file that contains lines starting with "> " (for example SKILL.md) gives its first such line.
// A run without a stored prompt uses the --default-prompt id.
import fs from 'node:fs';
import path from 'node:path';
import {distance, replaceBlock, thumbnail} from './drift.mjs';

const fail = message => { throw Error(message); };

function parseArgs(argv) {
  const args = [...argv];
  const flags = {run: [], prompt: []};
  while (args.length) {
    const key = args.shift();
    if (!key.startsWith('--') || !args.length) fail('Expected --option value');
    const value = args.shift();
    const name = key.slice(2);
    if (name === 'run' || name === 'prompt') flags[name].push(value);
    else flags[name] = value;
  }
  return flags;
}

function pair(text, option) {
  const i = text.indexOf('=');
  if (i < 1) fail(`Bad --${option} ${text}`);
  return [text.slice(0, i), text.slice(i + 1)];
}

function promptText(file) {
  const text = fs.readFileSync(file, 'utf8');
  const quoted = text.split('\n').find(line => line.startsWith('> '));
  const result = (quoted ? quoted.slice(2) : text).trim();
  if (!result) fail(`Prompt file ${file} is empty`);
  return result;
}

function status(m) {
  if (m.pending) return 'request pending';
  return m.frames.length - 1 >= m.target ? 'complete' : 'incomplete';
}

function main() {
  const flags = parseArgs(process.argv.slice(2));
  const readme = path.resolve(flags.readme || fail('--readme is required'));
  const out = path.resolve(flags.out || fail('--out is required'));
  if (!flags.run.length) fail('At least one --run is required');
  const fallback = flags['default-prompt'] || 'v1';
  const base = path.dirname(readme);
  const rel = p => path.relative(base, p).split(path.sep).join('/');
  fs.mkdirSync(out, {recursive: true});

  const prompts = flags.prompt.map(p => {
    const [id, file] = pair(p, 'prompt');
    return {id, file: path.resolve(file), text: promptText(path.resolve(file)), runs: []};
  });

  const runs = flags.run.map(r => {
    const [label, dir] = pair(r, 'run');
    const full = path.resolve(dir);
    const m = JSON.parse(fs.readFileSync(path.join(full, 'manifest.json'), 'utf8'));
    return {label, dir: full, m, promptId: m.promptId || fallback};
  });

  const rows = [
    '| Run | Source | Latest frame | Model | Prompt | Generations | Status |',
    '| --- | --- | --- | --- | --- | --- | --- |',
  ];
  for (const run of runs) {
    const frames = run.m.frames;
    const first = frames[0];
    const last = frames[frames.length - 1];
    const name = path.basename(run.dir);
    const firstThumb = path.join(out, `overview-${name}-first.jpg`);
    const lastThumb = path.join(out, `overview-${name}-last.jpg`);
    thumbnail(path.join(run.dir, first.path), firstThumb, 240);
    thumbnail(path.join(run.dir, last.path), lastThumb, 240);
    const d = last.index === 0 ? '0.000' : distance(path.join(run.dir, first.path), path.join(run.dir, last.path));
    const gif = path.join(run.dir, 'evolution.gif');
    const animation = fs.existsSync(gif) ? ` · [GIF](${rel(gif)})` : '';
    const prompt = prompts.find(p => p.id === run.promptId);
    if (prompt) prompt.runs.push(run.label);
    const cells = [
      `[${run.label}](${rel(run.dir)}/)`,
      `<img src="${rel(firstThumb)}" width="120" alt="${run.label}, source">`,
      `<img src="${rel(lastThumb)}" width="120" alt="${run.label}, generation ${last.index}"><br>gen ${last.index}, d = ${d}${animation}`,
      `\`${run.m.provider}\``,
      run.promptId,
      `${frames.length - 1} / ${run.m.target}`,
      status(run.m),
    ];
    rows.push(`| ${cells.join(' | ')} |`);
  }

  const promptRows = ['| Prompt | Text | Runs |', '| --- | --- | --- |'];
  for (const p of prompts) {
    const text = p.text.replace(/\|/g, '\\|').replace(/\s+/g, ' ');
    promptRows.push(`| [${p.id}](${rel(p.file)}) | ${text} | ${p.runs.length ? p.runs.join(', ') : '—'} |`);
  }

  let text = fs.readFileSync(readme, 'utf8');
  text = replaceBlock(text, 'overview', rows);
  if (prompts.length) text = replaceBlock(text, 'prompts', promptRows);
  fs.writeFileSync(readme, text);
  console.log(readme);
}

try {
  main();
} catch (e) {
  console.error(`Error: ${e.message}`);
  process.exitCode = 1;
}
