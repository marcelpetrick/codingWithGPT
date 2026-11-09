#!/usr/bin/env node
// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const PROMPT = 'Recreate the provided image as faithfully as possible. Preserve its composition, subjects, shapes, colors, lighting, textures, background, framing, and any visible text. Make no intentional additions, removals, improvements, or stylistic changes. Return one image.';
const rates = JSON.parse(fs.readFileSync(new URL('../references/pricing.json', import.meta.url)));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const now = () => new Date().toISOString();
const frame = n => `frames/${String(n).padStart(4,'0')}.png`;
function fail(s) { throw Error(s); }
function atomic(p, data) { const t = `${p}.${crypto.randomUUID()}.tmp`; fs.writeFileSync(t,data,{mode:0o600}); fs.renameSync(t,p); }
function save(dir,m) { atomic(path.join(dir,'manifest.json'),JSON.stringify(m,null,2)+'\n'); }
function cmd(name,args) { const r=spawnSync(name,args,{encoding:'utf8'}); if(r.error || r.status!==0) fail(`${name} failed: ${r.error?.message || r.stderr}`); return r.stdout.trim(); }
function verifyImage(p) { cmd('identify',['-regard-warnings',p]); }
function parse(argv) { const op=argv.shift(); const a={}; while(argv.length){const k=argv.shift(); if(!k.startsWith('--')) fail(`Unexpected argument ${k}`); const name=k.slice(2); if(name==='accept-estimated-reserve'){a[name]=true;continue;} if(!argv.length||argv[0].startsWith('--')) fail(`Missing value for ${k}`); a[name]=argv.shift();} return [op,a]; }
function number(a,k,def,integer=false) { const v=a[k]===undefined?def:Number(a[k]); if(!Number.isFinite(v)||v<0||(integer&&!Number.isInteger(v))) fail(`Invalid --${k}`); return v; }
function configure(a) {
 const input=path.resolve(a.input||fail('--input is required')); if(!fs.statSync(input).isFile()) fail('Input must be a file'); verifyImage(input);
 const iterations=number(a,'iterations',101,true); if(!iterations) fail('Iterations must be positive');
 const provider=a.provider||'openai'; if(!['openai','mock'].includes(provider)) fail('Unknown provider');
 const model=a.model||'gpt-image-2'; const quality=a.quality||'medium'; if(!['low','medium','high'].includes(quality)) fail('Unsupported quality');
 const size=a.size||'1024x1024'; if(!['1024x1024','1536x1024','1024x1536'].includes(size)) fail('Unsupported size');
 const budget=number(a,'budget-usd',provider==='mock'?0:NaN); const reserve=number(a,'reserve-usd',provider==='mock'?0:NaN); if(provider==='openai' && (!rates.per_million_tokens[model]||!reserve)) fail('Paid runs require a priced model and a positive --reserve-usd');
 return {input,iterations,provider,model,quality,size,budget,reserve,accepted:!!a['accept-estimated-reserve'],prompt:PROMPT};
}
function cost(u,model) { const r=rates.per_million_tokens[model], d=u?.input_tokens_details; if(!r||!d||![d.text_tokens,d.image_tokens,u.output_tokens,u.input_tokens].every(Number.isFinite)||d.text_tokens+d.image_tokens!==u.input_tokens||u.output_tokens<0||d.text_tokens<0||d.image_tokens<0) return null; return (d.text_tokens*r.text_input+d.image_tokens*r.image_input+u.output_tokens*r.image_output)/1e6; }
function report(dir,m) { const sum=m.attempts.reduce((v,x)=>v+(x.cost??0),0); const reserved=m.attempts.reduce((v,x)=>v+(x.cost===null?x.reserve:0),0); const done=m.attempts.filter(x=>x.outcome==='success'); const elapsed=done.reduce((v,x)=>v+(x.elapsedMs||0),0); const measured=done.filter(x=>x.cost!==null); const projection=measured.length===done.length && done.length ? `Pilot mean projection for 101 calls: USD ${(sum/done.length*101).toFixed(6)}. High estimate with 50% headroom: USD ${(Math.max(...measured.map(x=>x.cost))*101*1.5).toFixed(6)}. This small sample may not predict later costs.` : 'Cost projection: unavailable because usage is incomplete.'; const body=`# Recreate 101 report\n\nStatus: ${m.status}\n\nCompleted generations: ${m.completed} / ${m.config.iterations}\n\nProvider: ${m.config.provider}; model: ${m.config.model}; size: ${m.config.size}; quality: ${m.config.quality}.\n\nCalculated known cost: USD ${sum.toFixed(6)}. Outstanding reservations: USD ${reserved.toFixed(6)}. Lifetime allowance: USD ${m.config.budget.toFixed(6)}.\n\nRates: ${rates.source}, snapshot ${rates.date}. This calculation is not an invoice. A reservation is not an enforceable billing ceiling.\n\nSuccessful call time: ${elapsed} ms. ${projection}\n\nAgent session tokens and cost: unavailable. Account balance: unavailable. Raw usage and request IDs are in usage.jsonl and manifest.json.\n\n${m.config.provider==='mock'?'Mock frames change one pixel. No visual recreation occurred.\n':''}`; atomic(path.join(dir,'report.md'),body); }
function encode(dir,m) { const files=[]; for(let i=0;i<=m.completed;i++){const p=path.join(dir,frame(i)); verifyImage(p); files.push(p);} const tmp=path.join(dir,'evolution.tmp.gif'); const args=[]; for(let i=0;i<files.length;i++){args.push('-delay',i===0||i===files.length-1?'100':'25',files[i],'-resize','768x768>','-background','white','-gravity','center','-extent','768x768');} args.push('-loop','0',tmp); cmd('convert',args); cmd('ffprobe',['-v','error','-show_entries','format=duration','-of','default=nw=1',tmp]); fs.renameSync(tmp,path.join(dir,'evolution.gif')); }
function validate(dir,m) { for(let i=0;i<=m.completed;i++){const p=path.join(dir,frame(i)); if(!fs.existsSync(p)||sha(p)!==m.frames[i].sha256) fail(`Frame ${i} missing or changed`); verifyImage(p);} if(sha(path.join(dir,m.original))!==m.originalSha256) fail('Original changed'); }
function ledger(dir,e){fs.appendFileSync(path.join(dir,'usage.jsonl'),JSON.stringify(e)+'\n',{mode:0o600});}
async function request(m,input) { if(m.config.provider==='mock') { const result=spawnSync('convert',[input,'-fill',`rgb(${(m.completed+1)%256},0,0)`,'-draw','point 0,0','png:-'],{maxBuffer:50*1024*1024}); if(result.status!==0) fail('Mock image conversion failed'); return {bytes:result.stdout,usage:{input_tokens:0,input_tokens_details:{text_tokens:0,image_tokens:0},output_tokens:0},id:'mock'}; }
 const f=new FormData(); f.append('model',m.config.model); f.append('prompt',PROMPT); f.append('size',m.config.size); f.append('quality',m.config.quality); f.append('output_format','png'); f.append('n','1'); f.append('image',new Blob([fs.readFileSync(input)],{type:'image/png'}),'input.png');
 const res=await fetch('https://api.openai.com/v1/images/edits',{method:'POST',headers:{Authorization:`Bearer ${process.env.OPENAI_API_KEY}`},body:f,signal:AbortSignal.timeout(600000)}); const id=res.headers.get('x-request-id'); const j=await res.json(); if(!res.ok) throw Error(`HTTP ${res.status}, request ${id||'unavailable'}: ${j.error?.message||'request failed'}`); if(!j.data?.[0]?.b64_json) throw Error(`No image returned; request ${id||'unavailable'}`); return {bytes:Buffer.from(j.data[0].b64_json,'base64'),usage:j.usage||null,id}; }
async function advance(dir,m) {
 if(m.attempts.some(x=>x.outcome==='pending')) fail('Unresolved request: reconcile it before any further generation');
 if(m.config.provider==='openai'&&!m.config.accepted) fail('Strict mode cannot establish a maximum request cost; use --accept-estimated-reserve only with user acceptance');
 if(m.config.provider==='openai'&&!process.env.OPENAI_API_KEY) fail('OPENAI_API_KEY is required');
 let interrupted=false; const stop=()=>{interrupted=true;}; process.on('SIGINT',stop); process.on('SIGTERM',stop);
 while(m.completed<m.config.iterations&&!interrupted){
  const used=m.attempts.reduce((v,x)=>v+(x.cost===null?x.reserve:x.cost),0); if(used+m.config.reserve>m.config.budget+1e-10){m.status='budget stopped';break;}
  const n=m.completed+1, input=path.join(dir,frame(n-1)); const a={iteration:n,attemptId:crypto.randomUUID(),started:now(),inputSha256:sha(input),reserve:m.config.reserve,cost:null,outcome:'pending',model:m.config.model,settings:{size:m.config.size,quality:m.config.quality},provider:m.config.provider}; m.attempts.push(a); m.status='request pending'; save(dir,m); ledger(dir,{event:'intent',...a});
  let result;
  try { result=await request(m,input); }
  catch(e){a.error=String(e.message); a.ended=now(); m.status='unresolved request'; save(dir,m); ledger(dir,{event:'unresolved',...a}); break;}
  const dest=path.join(dir,frame(n)), staged=`${dest}.${crypto.randomUUID()}.tmp.png`;
  try { fs.writeFileSync(staged,result.bytes,{mode:0o600,flag:'wx'}); verifyImage(staged); if(!cmd('identify',['-format','%m',staged]).startsWith('PNG')) fail('Generated output is not PNG'); fs.renameSync(staged,dest); }
  catch(e){try{fs.rmSync(staged,{force:true});}catch{} a.error=String(e.message); a.ended=now(); m.status='unresolved request'; save(dir,m); ledger(dir,{event:'unresolved',...a}); break;}
  a.ended=now(); a.elapsedMs=Date.parse(a.ended)-Date.parse(a.started); a.requestId=result.id; a.rawUsage=result.usage; a.cost=m.config.provider==='mock'?0:cost(result.usage,m.config.model); a.outputSha256=sha(dest); a.outcome='success'; m.frames.push({index:n,sha256:a.outputSha256,inputSha256:a.inputSha256}); m.completed=n; m.status='running'; save(dir,m); ledger(dir,{event:'result',...a});
 }
 if(interrupted) m.status='cancelled'; else if(m.completed===m.config.iterations) m.status='complete';
 save(dir,m); try{encode(dir,m);} finally{report(dir,m);} process.removeListener('SIGINT',stop);process.removeListener('SIGTERM',stop);
}
async function main(){const [op,a]=parse(process.argv.slice(2)); if(!op||op==='--help'||op==='help'){console.log('Usage: recreate.mjs plan|run --input IMAGE [--iterations N] [--provider mock|openai] [--budget-usd N] [--reserve-usd N] [--accept-estimated-reserve]\n       recreate.mjs resume|encode --run-dir DIR [--iterations TOTAL] [--budget-usd TOTAL]');return;}
 if(op==='plan'){const c=configure(a);console.log(JSON.stringify({...c,originalSha256:sha(c.input),networkCalls:0,note:'The reserve is an estimate, not a billing ceiling.'},null,2));return;}
 let dir,m;
 if(op==='run'){const c=configure(a); if(c.provider==='openai'&&!c.accepted) fail('Strict mode cannot establish a maximum request cost. No request sent.'); if(c.provider==='openai'&&!process.env.OPENAI_API_KEY) fail('OPENAI_API_KEY is required'); const base=path.basename(c.input,path.extname(c.input)); const parent=a['output-dir']?path.resolve(a['output-dir']):path.dirname(c.input); dir=fs.mkdtempSync(path.join(parent,`${base}.recreate-101.`)); fs.mkdirSync(path.join(dir,'frames')); const ext=path.extname(c.input).toLowerCase()||'.image'; const original='original'+ext; fs.copyFileSync(c.input,path.join(dir,original),fs.constants.COPYFILE_EXCL); cmd('convert',[path.join(dir,original),'-auto-orient','-resize',`${c.size.replace('x','x')}`, '-background','white','-gravity','center','-extent',c.size,path.join(dir,frame(0))]); verifyImage(path.join(dir,frame(0))); m={version:1,created:now(),config:c,original,originalSha256:sha(c.input),preparation:'auto-orient, proportional resize, white padding to canvas',completed:0,frames:[{index:0,sha256:sha(path.join(dir,frame(0)))}],attempts:[],status:'created'}; save(dir,m); fs.writeFileSync(path.join(dir,'usage.jsonl'),''); console.log(`Run directory: ${dir}`);}
 else if(['resume','encode'].includes(op)){dir=path.resolve(a['run-dir']||fail('--run-dir is required')); m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));}
 else fail('Unknown command');
 const lock=path.join(dir,'.lock'); try{fs.mkdirSync(lock);}catch{fail('Run is locked; verify the owner before removing .lock');}
 try{validate(dir,m); if(op==='encode'){encode(dir,m);report(dir,m);} else {if(op==='resume'){const target=number(a,'iterations',m.config.iterations,true), budget=number(a,'budget-usd',m.config.budget); if(target<m.completed) fail('Target cannot be less than completed generations'); if(budget<m.config.budget) fail('Lifetime budget cannot be reduced'); m.config.iterations=target;m.config.budget=budget;save(dir,m);} await advance(dir,m);} } finally{fs.rmdirSync(lock);} console.log(`Status: ${m.status}; generations: ${m.completed}/${m.config.iterations}`);
}
main().catch(e=>{console.error(`Error: ${e.message}`);process.exitCode=1;});
