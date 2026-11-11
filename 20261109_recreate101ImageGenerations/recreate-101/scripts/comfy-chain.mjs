#!/usr/bin/env node
// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Drive a host run with a local ComfyUI server: one API prompt per generation, ledger in host.mjs.
// Usage: comfy-chain.mjs RUN_DIR
// Env: COMFY_URL (http://127.0.0.1:8188), COMFY_SEED (42), CALL_TIMEOUT (600 s), POLL_MS (1000),
//      COMFY_WORKFLOW (references/comfy-flux2-klein-edit.json), COMMIT_CHECKPOINTS (1: commit RUN_DIR at
//      each tenth frame; a busy .git/index.lock is retried LOCK_RETRIES (12) times, LOCK_WAIT_MS (5000) apart)
// Exit: 0 target reached, 3 failure (stopped; a queued request stays pending for review).
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const env=process.env;
const base=(env.COMFY_URL||'http://127.0.0.1:8188').replace(/\/$/,'');
const seed=Number(env.COMFY_SEED||42);
const timeoutMs=Number(env.CALL_TIMEOUT||600)*1000;
const pollMs=Number(env.POLL_MS||1000);
const workflow=env.COMFY_WORKFLOW||path.join(here,'../references/comfy-flux2-klein-edit.json');
let prompt=(fs.readFileSync(path.join(here,'../SKILL.md'),'utf8').match(/^> (.+)$/m)||[])[1];
class Stop extends Error{}
const say=m=>console.log(`${new Date().toISOString()} ${m}`);
const run=(cmd,args)=>{const r=spawnSync(cmd,args,{encoding:'utf8'});if(r.status!==0)throw new Stop(`${cmd} ${args[0]}: ${(r.stderr||r.error?.message||'').trim()}`);return r.stdout.trim();};
const host=(...a)=>run(process.execPath,[path.join(here,'host.mjs'),...a]);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function http(method,route,body){let r;try{r=await fetch(base+route,{method,body,signal:AbortSignal.timeout(60000)});}catch(e){throw new Stop(`${method} ${route}: server unreachable (${e.cause?.code||e.message})`);}if(!r.ok)throw new Stop(`${method} ${route}: HTTP ${r.status} ${(await r.text()).slice(0,300)}`);return r;}
const json=async(method,route,body)=>(await http(method,route,body)).json();
function graph(image){const g=JSON.parse(fs.readFileSync(workflow,'utf8'));g.load.inputs.image=image;g.prompt.inputs.text=prompt;g.noise.inputs.noise_seed=seed;return g;}
async function wait(id){const end=Date.now()+timeoutMs;for(;;){const h=(await json('GET',`/history/${id}`))[id];if(h?.status?.completed||h?.status?.status_str==='error'){if(h.status.status_str!=='success')throw new Stop(`prompt ${id} failed: ${JSON.stringify(h.status.messages||[]).slice(-400)}`);const images=Object.values(h.outputs||{}).flatMap(o=>o.images||[]);if(images.length!==1)throw new Stop(`prompt ${id} returned ${images.length} images`);return images[0];}if(Date.now()>end)throw new Stop(`prompt ${id}: no result after ${timeoutMs/1000} s`);await pause(pollMs);}}
function check(file,input){if(run('identify',['-format','%m',file])!=='PNG')throw new Stop('result is not a PNG');const sd=Number(run('identify',['-format','%[fx:standard_deviation]',file]));if(!(sd>0.01))throw new Stop(`result is uniform (standard deviation ${sd})`);if(sha(fs.readFileSync(file))===sha(fs.readFileSync(input)))throw new Stop('result is an unchanged copy of the input');return sd;}
const ledger=dir=>path.join(dir,'comfy.jsonl');
const record=(dir,e)=>fs.appendFileSync(ledger(dir),JSON.stringify(e)+'\n');
const queued=(dir,iteration)=>(fs.existsSync(ledger(dir))?fs.readFileSync(ledger(dir),'utf8').split('\n').filter(Boolean).map(l=>JSON.parse(l)):[]).filter(e=>e.event==='queued'&&e.iteration===iteration).at(-1);
async function finish(dir,work,iteration,id,input,t0){const out=await wait(id);const bytes=Buffer.from(await (await http('GET',`/view?${new URLSearchParams({filename:out.filename,subfolder:out.subfolder||'',type:out.type||'output'})}`)).arrayBuffer());if(!bytes.length)throw new Stop(`prompt ${id}: empty image read`);const file=path.join(work,`${String(iteration).padStart(4,'0')}.png`);fs.writeFileSync(file,bytes);const sd=check(file,input);const seconds=t0?Math.round((Date.now()-t0)/100)/10:null;host('accept','--run-dir',dir,'--image',file,'--thread-id',id);record(dir,{event:'result',iteration,promptId:id,seconds,stddev:sd,ended:new Date().toISOString()});fs.rmSync(file);return seconds;}
function git(dir,args){for(let i=0;;i++){const r=spawnSync('git',['-C',dir,...args],{encoding:'utf8'});if(r.status===0||!/index\.lock/.test(r.stderr)||i>=Number(env.LOCK_RETRIES||12))return r;Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,Number(env.LOCK_WAIT_MS||5000));}}
let published=-1;
function publish(dir,n){if((env.COMMIT_CHECKPOINTS||'1')!=='1'||published===n)return;const a=git(dir,['add','--','.']);if(a.status!==0)throw new Stop(`git add: ${a.stderr.trim()}`);const c=git(dir,['commit','-q','-m',`docs: checkpoint ${n} generations of the ComfyUI chain ${path.basename(dir)}`,'--','.']);const quiet=c.status!==0&&/nothing (added )?to commit|no changes added/.test(`${c.stdout||''}${c.stderr||''}`);if(c.status===0||quiet)published=n;say(`checkpoint ${n}: ${c.status===0?'committed':quiet?'nothing new to commit':`commit failed: ${(c.stderr||'').trim().slice(0,200)}`}`);}
async function main(){
 const dir=path.resolve(process.argv[2]||'');if(!process.argv[2]||!fs.existsSync(path.join(dir,'manifest.json')))throw new Stop('RUN_DIR with a manifest.json is required');prompt=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8')).prompt||prompt;if(!prompt)throw new Stop('No fixed prompt found in SKILL.md');
 const work=fs.mkdtempSync(path.join(os.tmpdir(),'recreate101-comfy-'));
 try{
  await json('GET','/system_stats');
  say(`start: run ${dir}, server ${base}, seed ${seed}`);
  for(;;){
   const s=JSON.parse(host('status','--run-dir',dir));
   if(s.pending){const q=queued(dir,s.next);if(!q){host('cancel','--run-dir',dir,'--reason','no ComfyUI prompt was queued for this request');say(`gen ${s.next}: cancelled an unsent request`);continue;}say(`gen ${s.next}: resume queued prompt ${q.promptId}`);await finish(dir,work,s.next,q.promptId,path.join(dir,'frames',`${String(s.next-1).padStart(4,'0')}.png`),null);if(s.next%10===0)publish(dir,s.next);continue;}
   if(s.completed>=s.target){if(s.completed%10===0)publish(dir,s.completed);say(`DONE: ${s.completed} / ${s.target}`);return 0;}
   const n=s.next,t0=Date.now();
   const input=host('next','--run-dir',dir);
   const form=new FormData();form.append('image',new Blob([fs.readFileSync(input)],{type:'image/png'}),`recreate101-${sha(fs.readFileSync(input)).slice(0,16)}.png`);form.append('subfolder','recreate101');form.append('overwrite','true');
   const up=await json('POST','/upload/image',form);
   const r=await json('POST','/prompt',JSON.stringify({prompt:graph(up.subfolder?`${up.subfolder}/${up.name}`:up.name),client_id:'recreate-101'}));
   if(!r.prompt_id)throw new Stop(`POST /prompt: no prompt_id (${JSON.stringify(r).slice(0,300)})`);
   record(dir,{event:'queued',iteration:n,promptId:r.prompt_id,input:path.basename(input),seed,queued:new Date().toISOString()});
   const seconds=await finish(dir,work,n,r.prompt_id,input,t0);
   say(`gen ${n}: accepted in ${seconds} s (prompt ${r.prompt_id})`);
   if(n%10===0)publish(dir,n);
  }
 }finally{fs.rmSync(work,{recursive:true,force:true});}
}
main().then(c=>{process.exitCode=c;},e=>{say(`STOP: ${e.message}`);if(!(e instanceof Stop))console.error(e.stack);process.exitCode=3;});
