import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const script=fileURLToPath(new URL('../scripts/recreate.mjs',import.meta.url));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function run(...args){return spawnSync(process.execPath,[script,...args],{encoding:'utf8'});}
function fixture(){const dir=fs.mkdtempSync(path.join(os.tmpdir(),'recreate-test-'));const input=path.join(dir,'input.png');assert.equal(spawnSync('convert',['-size','30x20','xc:blue',input]).status,0);return {dir,input};}
function manifest(dir){return JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));}
function runDir(dir){return path.join(dir,fs.readdirSync(dir).find(x=>x.includes('.recreate-101.')));}
test('three frames follow the previous committed image and survive resume',()=>{const {dir,input}=fixture();const original=sha(input);const r=run('run','--input',input,'--provider','mock','--iterations','3','--budget-usd','0');assert.equal(r.status,0,r.stderr);const d=runDir(dir), m=manifest(d);assert.equal(m.completed,3);assert.equal(sha(input),original);assert.equal(sha(path.join(d,m.original)),original);for(let i=1;i<=3;i++){assert.equal(m.attempts[i-1].inputSha256,m.frames[i-1].sha256);assert.notEqual(m.frames[i].sha256,m.frames[i-1].sha256);}assert.equal(spawnSync('ffprobe',['-v','error',path.join(d,'evolution.gif')]).status,0);const next=run('resume','--run-dir',d,'--iterations','4');assert.equal(next.status,0,next.stderr);assert.equal(manifest(d).completed,4);});
test('strict paid mode refuses before creating a run or sending a request',()=>{const {dir,input}=fixture();const r=run('run','--input',input,'--iterations','1','--budget-usd','1','--reserve-usd','0.1');assert.notEqual(r.status,0);assert.match(r.stderr,/Strict mode/);assert.equal(fs.readdirSync(dir).length,1);});
test('budget refusal sends no request',()=>{const {dir,input}=fixture();const r=spawnSync(process.execPath,[script,'run','--input',input,'--iterations','1','--budget-usd','0.1','--reserve-usd','1','--accept-estimated-reserve'],{encoding:'utf8',env:{...process.env,OPENAI_API_KEY:'test'}});assert.equal(r.status,0,r.stderr);const m=manifest(runDir(dir));assert.equal(m.status,'budget stopped');assert.equal(m.attempts.length,0);});
test('pending request and changed frame block resume',()=>{const {dir,input}=fixture();assert.equal(run('run','--input',input,'--provider','mock','--iterations','1').status,0);const d=runDir(dir),p=path.join(d,'manifest.json'),m=manifest(d);m.attempts.push({outcome:'pending',cost:null,reserve:1});fs.writeFileSync(p,JSON.stringify(m));let r=run('resume','--run-dir',d,'--iterations','2');assert.notEqual(r.status,0);assert.match(r.stderr,/Unresolved request/);m.attempts.pop();fs.writeFileSync(p,JSON.stringify(m));fs.appendFileSync(path.join(d,'frames/0001.png'),'changed');r=run('resume','--run-dir',d,'--iterations','2');assert.notEqual(r.status,0);assert.match(r.stderr,/missing or changed/);});
