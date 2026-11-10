// Copyright (C) 2026 Recreate 101 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
// Drive comfy-chain.mjs against a fake ComfyUI HTTP server.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import {spawn,spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const chain=fileURLToPath(new URL('../scripts/comfy-chain.mjs',import.meta.url));
const host=fileURLToPath(new URL('../scripts/host.mjs',import.meta.url));
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'recreate-comfy-'));
const image=(name,spec,fmt='png',...more)=>{const p=path.join(tmp,`${name}.${fmt}`);if(!fs.existsSync(p))assert.equal(spawnSync('convert',['-size','20x20',spec,...more,p]).status,0);return fs.readFileSync(p);};
const good=k=>image(`good${k%20}`,'gradient:white-black','png','-fill','red','-draw',`point ${k%20},${k%20}`);

// Fake server. `opt` steers each scenario: result (png|uniform|copy|jpeg|empty|two|error|never),
// prompt (ok|http|noid|text), polls before the history entry appears.
function fake(opt={}){const s={prompts:[],uploads:[],last:null};const server=http.createServer((req,res)=>{let body=[];req.on('data',c=>body.push(c));req.on('end',()=>{body=Buffer.concat(body);const u=new URL(req.url,'http://x');const send=(code,x,type='application/json')=>{res.writeHead(code,{'content-type':type});res.end(typeof x==='string'||Buffer.isBuffer(x)?x:JSON.stringify(x));};
 if(u.pathname==='/system_stats')return send(200,{system:{comfyui_version:'test'}});
 if(u.pathname==='/upload/image'){const i=body.indexOf('\r\n\r\n')+4;s.last=body.subarray(i,body.indexOf('\r\n--',i));s.uploads.push(s.last);return send(200,{name:'x.png',subfolder:'recreate101',type:'input'});}
 if(u.pathname==='/prompt'){const p=JSON.parse(body);s.prompts.push(p.prompt);if(opt.prompt==='http')return send(400,{error:'bad graph'});if(opt.prompt==='noid')return send(200,{});if(opt.prompt==='text')return send(200,'not json','text/plain');return send(200,{prompt_id:`p${s.prompts.length}`});}
 if(u.pathname.startsWith('/history/')){const id=u.pathname.slice(9);s.polls=(s.polls||0)+1;if(opt.result==='never'||s.polls<=(opt.polls||0))return send(200,{});if(opt.result==='error')return send(200,{[id]:{status:{status_str:'error',completed:false,messages:[['execution_error',{}]]},outputs:{}}});const img={filename:`${id}.png`,subfolder:'',type:'temp'};return send(200,{[id]:{status:{status_str:'success',completed:true},outputs:{output:{images:opt.result==='two'?[img,img]:[img]}}}});}
 if(u.pathname==='/view'){const r=opt.result;return send(200,r==='uniform'?image('flat','xc:black'):r==='copy'?s.last:r==='jpeg'?image('jpg','gradient:red-blue','jpg'):r==='empty'?'':good(s.views=(s.views||0)+1),'image/png');}
 send(404,'missing','text/plain');});});
 return new Promise(r=>server.listen(0,'127.0.0.1',()=>{s.url=`http://127.0.0.1:${server.address().port}`;s.close=()=>server.close();r(s);}));}
function init(target){const d=fs.mkdtempSync(path.join(tmp,'run-'));const r=spawnSync(process.execPath,[host,'init','--input',path.join(tmp,'src.png'),'--iterations',String(target),'--output-dir',d,'--provider','comfyui-test'],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);return r.stdout.trim();}
image('src','gradient:red-blue');
function go(dir,url,extra={}){return new Promise(r=>{const c=spawn(process.execPath,[chain,...(dir?[dir]:[])],{env:{...process.env,COMFY_URL:url,COMMIT_CHECKPOINTS:'0',POLL_MS:'5',...extra}});let out='';c.stdout.on('data',d=>out+=d);c.stderr.on('data',d=>out+=d);c.on('close',status=>r({status,out}));});}
const manifest=d=>JSON.parse(fs.readFileSync(path.join(d,'manifest.json')));
const ledger=d=>fs.readFileSync(path.join(d,'comfy.jsonl'),'utf8').trim().split('\n').map(l=>JSON.parse(l));

test('chain uploads the previous frame, sends the fixed prompt and books each result',async()=>{const s=await fake({polls:2});const d=init(2);const r=await go(d,s.url,{COMFY_SEED:'7'});s.close();assert.equal(r.status,0,r.out);const m=manifest(d);assert.equal(m.frames.length,3);assert.equal(m.provider,'comfyui-test');assert.equal(m.frames[1].threadId,'p1');assert.deepEqual(s.uploads[0],fs.readFileSync(path.join(d,'frames/0000.png')));assert.deepEqual(s.uploads[1],fs.readFileSync(path.join(d,'frames/0001.png')));const p=s.prompts[0];assert.match(p.prompt.inputs.text,/^Recreate the provided image as faithfully as possible\./);assert.equal(p.noise.inputs.noise_seed,7);assert.equal(p.load.inputs.image,'recreate101/x.png');const l=ledger(d);assert.deepEqual(l.map(e=>e.event),['queued','result','queued','result']);assert.ok(l[1].seconds>=0);assert.match(fs.readFileSync(path.join(d,'report.md'),'utf8'),/Provider: comfyui-test/);});

test('chain resumes a queued prompt and cancels an unsent request',async()=>{const s=await fake();const d=init(2);spawnSync(process.execPath,[host,'next','--run-dir',d]);fs.writeFileSync(path.join(d,'comfy.jsonl'),JSON.stringify({event:'queued',iteration:1,promptId:'old'})+'\n');let r=await go(d,s.url,{COMFY_SEED:'1'});assert.equal(r.status,0,r.out);assert.match(r.out,/resume queued prompt old/);assert.equal(manifest(d).frames[1].threadId,'old');
 const e=init(1);spawnSync(process.execPath,[host,'next','--run-dir',e]);r=await go(e,s.url);s.close();assert.equal(r.status,0,r.out);assert.match(r.out,/cancelled an unsent request/);assert.match(fs.readFileSync(path.join(e,'usage.jsonl'),'utf8'),/cancelled/);assert.equal(manifest(e).frames.length,2);});

test('chain commits each tenth frame in the run directory and waits for a busy index lock',async()=>{const s=await fake();const repo=fs.mkdtempSync(path.join(tmp,'repo-'));for(const a of [['init','-q'],['config','user.email','t@example.invalid'],['config','user.name','t']])spawnSync('git',['-C',repo,...a]);const d=spawnSync(process.execPath,[host,'init','--input',path.join(tmp,'src.png'),'--iterations','10','--output-dir',repo],{encoding:'utf8'}).stdout.trim();fs.writeFileSync(path.join(repo,'.git/index.lock'),'');setTimeout(()=>fs.rmSync(path.join(repo,'.git/index.lock')),300);
 const r=await go(d,s.url,{COMMIT_CHECKPOINTS:'1',LOCK_WAIT_MS:'100',LOCK_RETRIES:'50'});assert.equal(r.status,0,r.out);assert.match(r.out,/checkpoint 10: committed/);assert.equal(r.out.match(/checkpoint 10:/g).length,1);assert.match(spawnSync('git',['-C',repo,'log','--oneline'],{encoding:'utf8'}).stdout,/checkpoint 10 generations/);assert.ok(fs.existsSync(path.join(d,'checkpoints/0010.gif')));
 fs.writeFileSync(path.join(repo,'.git/index.lock'),'');spawnSync(process.execPath,[host,'target','--run-dir',d,'--iterations','20']);const r2=await go(d,s.url,{COMMIT_CHECKPOINTS:'1',LOCK_WAIT_MS:'1',LOCK_RETRIES:'1'});s.close();assert.equal(r2.status,3,r2.out);assert.match(r2.out,/STOP: git add/);assert.equal(manifest(d).frames.length,21);fs.rmSync(path.join(repo,'.git/index.lock'));const r3=await go(d,'http://127.0.0.1:9',{COMMIT_CHECKPOINTS:'1'});assert.equal(r3.status,3);const s3=await fake();const r4=await go(d,s3.url,{COMMIT_CHECKPOINTS:'1'});const r5=await go(d,s3.url,{COMMIT_CHECKPOINTS:'1'});s3.close();assert.match(r4.out,/checkpoint 20: committed/);assert.match(r5.out,/checkpoint 20: nothing new/);});

test('chain stops on invalid results and keeps the queued request pending',async()=>{for(const [result,why] of [['uniform',/uniform/],['copy',/unchanged copy/],['jpeg',/not a PNG/],['empty',/empty image read/],['two',/returned 2 images/],['error',/failed/],['never',/no result after/]]){const s=await fake({result});const d=init(1);const r=await go(d,s.url,{CALL_TIMEOUT:'0.05'});s.close();assert.equal(r.status,3,`${result}: ${r.out}`);assert.match(r.out,why);const m=manifest(d);assert.ok(m.pending,result);assert.equal(m.frames.length,1);}});

test('chain stops on server and argument failures without booking a frame',async()=>{let r=await go(null,'http://127.0.0.1:9');assert.equal(r.status,3);assert.match(r.out,/RUN_DIR/);const d=init(1);r=await go(d,'http://127.0.0.1:9');assert.equal(r.status,3);assert.match(r.out,/server unreachable/);assert.equal(manifest(d).pending,null);
 for(const [prompt,why] of [['http',/HTTP 400/],['noid',/no prompt_id/],['text',/SyntaxError|JSON/]]){const s=await fake({prompt});const e=init(1);r=await go(e,s.url);s.close();assert.equal(r.status,3,r.out);assert.match(r.out,why);assert.equal(manifest(e).frames.length,1);}
 const s=await fake();r=await go(d,s.url,{COMFY_WORKFLOW:path.join(tmp,'none.json')});s.close();assert.equal(r.status,3);assert.match(r.out,/ENOENT/);});
