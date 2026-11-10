// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const host=fileURLToPath(new URL('../scripts/host.mjs',import.meta.url));
const compare=fileURLToPath(new URL('../scripts/compare.mjs',import.meta.url));
const h=(...a)=>spawnSync(process.execPath,[host,...a],{encoding:'utf8'});
const c=(...a)=>spawnSync(process.execPath,[compare,...a],{encoding:'utf8'});
test('comparison table follows the manifests of several runs',()=>{const d=fs.mkdtempSync(path.join(os.tmpdir(),'recreate-compare-')),input=path.join(d,'s.png');spawnSync('convert',['-size','30x20','xc:navy',input]);
 const a=h('init','--input',input,'--iterations','2','--output-dir',d).stdout.trim();for(let i=0;i<2;i++){h('next','--run-dir',a);h('accept','--run-dir',a,'--image',input);}
 const b=h('init','--input',input,'--iterations','4','--output-dir',d).stdout.trim();h('next','--run-dir',b);h('accept','--run-dir',b,'--image',input);h('next','--run-dir',b);h('refuse','--run-dir',b,'--outcome','moderation_blocked');h('next','--run-dir',b);
 const readme=path.join(d,'README.md');fs.writeFileSync(readme,'x\n<!-- comparison:start -->\nold\n<!-- comparison:end -->\n');
 let r=c('--readme',readme,'--out',path.join(d,'cmp'),'--step','2','--run',`A=${a}`,'--run',`B=${b}`);assert.equal(r.status,0,r.stderr);const t=fs.readFileSync(readme,'utf8');
 assert.match(t,/\| A \| `codex-host-image-tool` \| v1 \| 2 \/ 2 \| 0 \| .* s \(2 timed\) \| complete \|/);assert.match(t,/\| B \| .* \| 1 \/ 4 \| 1 \| .* \| request pending \|/);assert.match(t,/\| 2 \| <img src="cmp\/run0-0002.jpg"[^|]*<br>d = (0\.000|n\/a) \| — \|/);assert.match(t,/d = 0\.000/);assert.doesNotMatch(t,/\| 4 \|/);assert.doesNotMatch(t,/old/);assert.ok(fs.existsSync(path.join(d,'cmp/run1-0000.jpg')));
 assert.equal(c('--readme',readme,'--out',path.join(d,'cmp'),'--step','2','--run',`A=${a}`).status,0);
 const m=JSON.parse(fs.readFileSync(path.join(b,'manifest.json')));m.frames=m.frames.map(f=>({...f,started:undefined}));fs.writeFileSync(path.join(b,'manifest.json'),JSON.stringify(m));assert.equal(c('--readme',readme,'--out',path.join(d,'cmp'),'--run',`B=${b}`).status,0);assert.match(fs.readFileSync(readme,'utf8'),/Unavailable/);
 for(const bad of [[],['--readme',readme],['--readme',readme,'--out',d],['--readme',readme,'--out',d,'--step','0','--run',`A=${a}`],['--readme',readme,'--out',d,'--run','noequals'],['--x']]) assert.notEqual(c(...bad).status,0);
 fs.writeFileSync(readme,'none\n');assert.notEqual(c('--readme',readme,'--out',d,'--run',`A=${a}`).status,0);
 fs.writeFileSync(readme,'<!-- comparison:start --><!-- comparison:end -->');fs.writeFileSync(path.join(a,'frames/0000.png'),'broken');fs.rmSync(path.join(d,'cmp'),{recursive:true});assert.notEqual(c('--readme',readme,'--out',path.join(d,'cmp'),'--run',`A=${a}`).status,0);});
