// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Drive codex-chain.sh with a fake `codex` that follows a scripted list of outcomes.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const chain=fileURLToPath(new URL('../scripts/codex-chain.sh',import.meta.url));
const host=fileURLToPath(new URL('../scripts/host.mjs',import.meta.url));
const fake=`#!/usr/bin/env bash
for a in "$@"; do last=$a; done; prev=""; for a in "$@"; do [[ $a == -- ]] && prev=1; done; [[ -n $prev && $last == "Use the image"* ]] || { echo "bad args" >&2; exit 64; }
step=$(head -n 1 "$PLAN"); sed -i 1d "$PLAN"; n=$(cat "$COUNTER" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$COUNTER"
echo '{"type":"thread.started","thread_id":"t'$n'"}'
case $step in
 ok) mkdir -p "$CODEX_IMAGES/t$n"; convert -size 20x20 xc:gray "$CODEX_IMAGES/t$n/a.png"; echo '{"type":"turn.completed","usage":{"input_tokens":7,"cached_input_tokens":3,"output_tokens":1}}';;
 refuse) echo '{"type":"item.completed","item":{"type":"agent_message","text":"The request was blocked by moderation."}}';;
 *) exit 1;;
esac
`;
function setup(target,steps){const d=fs.mkdtempSync(path.join(os.tmpdir(),'recreate-chain-')),bin=path.join(d,'bin');fs.mkdirSync(bin);fs.writeFileSync(path.join(bin,'codex'),fake,{mode:0o755});fs.writeFileSync(path.join(d,'plan'),steps.join('\n')+'\n');const input=path.join(d,'src.png');spawnSync('convert',['-size','20x20','xc:white',input]);const dir=spawnSync(process.execPath,[host,'init','--input',input,'--iterations',String(target)],{encoding:'utf8'}).stdout.trim();fs.writeFileSync(path.join(d,'README.md'),'<!-- checkpoints:start -->\n<!-- checkpoints:end -->\n');return {d,dir,env:{...process.env,PATH:`${bin}:${process.env.PATH}`,PLAN:path.join(d,'plan'),COUNTER:path.join(d,'count'),CODEX_IMAGES:path.join(d,'img'),COMMIT_CHECKPOINTS:'0',CHAIN_README:path.join(d,'README.md'),REFUSAL_PAUSE:'0'}};}
const go=s=>spawnSync('bash',[chain,s.dir],{encoding:'utf8',env:s.env});
const manifest=s=>JSON.parse(fs.readFileSync(path.join(s.dir,'manifest.json')));
test('chain accepts images, retries a refusal and reaches the target',()=>{const s=setup(2,['ok','refuse','ok']);const r=go(s);assert.equal(r.status,0,r.stdout+r.stderr);const m=manifest(s);assert.equal(m.frames.length,3);assert.equal(m.refusals.length,1);assert.equal(m.frames[1].agentUsage.input_tokens,7);assert.equal(m.frames[2].threadId,'t3');assert.match(fs.readFileSync(s.env.CHAIN_README,'utf8'),/\| 2 \| \[Current GIF\]/);});
test('chain stops at the refusal limit',()=>{const s=setup(2,['refuse','refuse']);s.env.MAX_REFUSALS='2';const r=go(s);assert.equal(r.status,2,r.stdout+r.stderr);assert.equal(manifest(s).refusals.length,2);assert.equal(manifest(s).pending,null);});
test('chain stops on a failure and keeps the request pending',()=>{const s=setup(2,['fail']);let r=go(s);assert.equal(r.status,3,r.stdout+r.stderr);assert.ok(manifest(s).pending);r=go(s);assert.equal(r.status,3);assert.match(r.stdout,/pending/);});
