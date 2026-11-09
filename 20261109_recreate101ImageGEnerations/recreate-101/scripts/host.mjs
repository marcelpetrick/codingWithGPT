#!/usr/bin/env node
// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Checkpoint host-tool image generations. The host agent performs the tool calls.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const frame=n=>`frames/${String(n).padStart(4,'0')}.png`;
const fail=m=>{throw Error(m);};
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const save=(p,x)=>{const t=`${p}.${crypto.randomUUID()}.tmp`;fs.writeFileSync(t,JSON.stringify(x,null,2)+'\n',{mode:0o600});fs.renameSync(t,p);};
const call=(name,args)=>{const r=spawnSync(name,args,{encoding:'utf8'});if(r.status!==0)fail(`${name}: ${r.stderr||r.error?.message}`);return r.stdout.trim();};
const validate=p=>call('identify',['-regard-warnings',p]);
const args=process.argv.slice(2);const command=args.shift();const flags={};while(args.length){const k=args.shift();if(!k.startsWith('--')||!args.length)fail('Expected --option value');flags[k.slice(2)]=args.shift();}
function integer(v){const n=Number(v);if(!Number.isSafeInteger(n)||n<1)fail('Iterations must be a positive integer');return n;}
function lock(dir,fn){const p=path.join(dir,'.lock');fs.mkdirSync(p);try{return fn();}finally{fs.rmdirSync(p);}}
function checked(dir,m){if(digest(path.join(dir,m.original))!==m.originalSha256)fail('Original hash mismatch');for(const f of m.frames){const p=path.join(dir,f.path);if(digest(p)!==f.sha256)fail(`Frame ${f.index} hash mismatch`);validate(p);}}
function log(dir,e){fs.appendFileSync(path.join(dir,'usage.jsonl'),JSON.stringify(e)+'\n');}
function encode(dir,m){const files=m.frames.map(f=>path.join(dir,f.path));const first=call('identify',['-format','%w %h',files[0]]).split(' ').map(Number);const scale=768/Math.max(...first);const w=Math.max(1,Math.round(first[0]*scale)),h=Math.max(1,Math.round(first[1]*scale));const output=path.join(dir,'evolution.tmp.gif');const a=[];for(let i=0;i<files.length;i++)a.push('-delay',i===0||i===files.length-1?'100':'25','(',files[i],'-resize',`${w}x${h}`,'-background','white','-gravity','center','-extent',`${w}x${h}`,')');a.push('-loop','0',output);call('convert',a);call('ffprobe',['-v','error',output]);fs.renameSync(output,path.join(dir,'evolution.gif'));}
function report(dir,m){fs.writeFileSync(path.join(dir,'report.md'),`# Host-tool run\n\nStatus: ${m.pending?'awaiting result':m.frames.length-1===m.target?'complete':'ready'}.\n\nCompleted generations: ${m.frames.length-1} / ${m.target}.\n\nProvider: Codex host image tool. Model, image settings, tokens, request charges, and account balance: unavailable unless the host exposes them. API cost: not applicable; no direct API calls were made. Agent session overhead: unavailable.\n\nOriginal SHA-256: ${m.originalSha256}. See manifest.json and usage.jsonl for frame lineage.\n`);}
try{
 if(command==='init'){
  const input=path.resolve(flags.input||fail('--input is required'));validate(input);const target=integer(flags.iterations||3);const parent=flags['output-dir']?path.resolve(flags['output-dir']):path.dirname(input);const dir=fs.mkdtempSync(path.join(parent,`${path.basename(input,path.extname(input))}.recreate-101.`));fs.mkdirSync(path.join(dir,'frames'));const original=`original${path.extname(input).toLowerCase()||'.image'}`;fs.copyFileSync(input,path.join(dir,original));call('convert',[input,'-auto-orient',path.join(dir,frame(0))]);const m={version:1,provider:'codex-host-image-tool',target,original,originalSha256:digest(input),preparation:'EXIF orientation, lossless PNG conversion',frames:[{index:0,path:frame(0),sha256:digest(path.join(dir,frame(0)))}],pending:null,created:new Date().toISOString()};save(path.join(dir,'manifest.json'),m);fs.writeFileSync(path.join(dir,'usage.jsonl'),'');report(dir,m);console.log(dir);
 }else{
  const dir=path.resolve(flags['run-dir']||fail('--run-dir is required'));lock(dir,()=>{const file=path.join(dir,'manifest.json'),m=read(file);checked(dir,m);
   if(command==='next'){if(m.pending)fail('A request is already pending; reconcile it before continuing');if(m.frames.length-1>=m.target)fail('Target already complete');const previous=m.frames.at(-1);m.pending={iteration:previous.index+1,inputSha256:previous.sha256,started:new Date().toISOString()};save(file,m);log(dir,{event:'intent',...m.pending});report(dir,m);console.log(path.join(dir,previous.path));}
   else if(command==='accept'){if(!m.pending)fail('No request is pending');const input=path.resolve(flags.image||fail('--image is required'));validate(input);if(!call('identify',['-format','%m',input]).startsWith('PNG'))fail('Expected a PNG result');const dest=frame(m.pending.iteration);const bytes=fs.readFileSync(input);const output=path.join(dir,dest);if(fs.existsSync(output)){if(digest(output)!==digest(input))fail('Existing pending frame differs from the supplied result');}else fs.writeFileSync(output,bytes,{flag:'wx'});const result={index:m.pending.iteration,path:dest,sha256:digest(path.join(dir,dest)),inputSha256:m.pending.inputSha256,started:m.pending.started,ended:new Date().toISOString(),usage:null,requestId:null};m.frames.push(result);m.pending=null;save(file,m);log(dir,{event:'result',...result});encode(dir,m);report(dir,m);console.log(path.join(dir,dest));}
   else if(command==='encode'){encode(dir,m);report(dir,m);console.log(path.join(dir,'evolution.gif'));}
   else fail('Unknown command');
  });
 }
}catch(e){console.error(`Error: ${e.message}`);process.exitCode=1;}
