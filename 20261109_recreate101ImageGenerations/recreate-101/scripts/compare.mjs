#!/usr/bin/env node
// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Build a step-by-step comparison of several runs: thumbnails every STEP generations and a summary table.
// Usage: compare.mjs --readme README.md --out comparison [--step 10] [--block comparison] --run "Label=run-dir" [--run ...]
// The README section between <!-- BLOCK:start --> and <!-- BLOCK:end --> is replaced.
import fs from 'node:fs';
import path from 'node:path';
import {distance, frameFile, replaceBlock, thumbnail} from './drift.mjs';
const fail=m=>{throw Error(m);};
const args=process.argv.slice(2);const runs=[];const flags={};
while(args.length){const k=args.shift();if(!k.startsWith('--')||!args.length)fail('Expected --option value');const v=args.shift();if(k==='--run')runs.push(v);else flags[k.slice(2)]=v;}
const median=a=>{if(!a.length)return null;const s=[...a].sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;};
const seconds=f=>f.started&&f.ended?(Date.parse(f.ended)-Date.parse(f.started))/1000:null;
function summary(label,m){const done=m.frames.length-1;const secs=m.frames.slice(1).map(seconds).filter(x=>Number.isFinite(x)&&x>0);const med=median(secs);const refusals=(m.refusals||[]).length;const status=m.pending?'request pending':done>=m.target?'complete':'running or stopped';return `| ${label} | \`${m.provider}\` | ${m.promptId||'v1'} | ${done} / ${m.target} | ${refusals} | ${med===null?'Unavailable':`${med.toFixed(1)} s (${secs.length} timed)`} | ${status} |`;}
try{
 const readme=path.resolve(flags.readme||fail('--readme is required'));const out=path.resolve(flags.out||fail('--out is required'));const step=Number(flags.step||10);
 if(!Number.isSafeInteger(step)||step<1)fail('--step must be a positive integer');if(!runs.length)fail('At least one --run is required');
 const base=path.dirname(readme);fs.mkdirSync(out,{recursive:true});
 const loaded=runs.map(r=>{const i=r.indexOf('=');if(i<1)fail(`Bad --run ${r}`);const dir=path.resolve(r.slice(i+1));return {label:r.slice(0,i),dir,m:JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'))};});
 const max=Math.max(...loaded.map(r=>r.m.target));const rel=p=>path.relative(base,p).split(path.sep).join('/');
 const lines=['| Run | Provider | Prompt | Generations | Refusals | Median time per generation | Status |','| --- | --- | --- | --- | --- | --- | --- |',...loaded.map(r=>summary(r.label,r.m)),'',`| Generation | ${loaded.map(r=>r.label).join(' | ')} |`,`| --- | ${loaded.map(()=>'---').join(' | ')} |`];
 for(let g=0;g<=max;g+=step){const cells=loaded.map((r,k)=>{const f=r.m.frames.find(x=>x.index===g);if(!f)return '—';const thumb=path.join(out,`${path.basename(r.dir)}-${String(g).padStart(4,'0')}.jpg`);const src=frameFile(r.dir,f.path);thumbnail(src,thumb);return `<img src="${rel(thumb)}" width="200" alt="${r.label}, generation ${g}"><br>d = ${g===0?'0.000':distance(frameFile(r.dir,r.m.frames[0].path),src)}`;});if(cells.every(c=>c==='—'))continue;lines.push(`| ${g} | ${cells.join(' | ')} |`);}
 const text=fs.readFileSync(readme,'utf8');fs.writeFileSync(readme,replaceBlock(text,flags.block||'comparison',lines));console.log(readme);
}catch(e){console.error(`Error: ${e.message}`);process.exitCode=1;}
