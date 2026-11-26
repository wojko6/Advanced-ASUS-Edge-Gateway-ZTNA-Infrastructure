import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
const dir=resolve(import.meta.dirname,'..');
const text=(name)=>readFileSync(resolve(dir,name),'utf8');
test('strict CSP prevents arbitrary network connections, remote scripts and forms',()=>{
 const page=text('index.html');
 assert.match(page,/default-src 'none'/);
 assert.match(page,/connect-src 'none'/);
 assert.match(page,/script-src 'self'/);
 assert.match(page,/form-action 'none'/);
 assert.doesNotMatch(page,/<script[^>]*src=["']https?:/i);
});
test('no active remote URLs or fetch in application source',()=>{
 for(const filename of ['index.html','app.mjs','data.mjs','model.mjs','styles.css']){
   const source=text(filename);
   assert.doesNotMatch(source,/\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\s*\(/);
   assert.doesNotMatch(source,/(?:src|href)=["']https?:\/\//i);
 }
});
test('app only uses textContent for input-bearing labels',()=>{
 const source=text('app.mjs');
 assert.doesNotMatch(source,/\.innerHTML\s*=/);
 assert.match(source,/\.textContent\s*=/);
});
test('no privileged or network-changing commands in runner',()=>{
 const source=text('run-lab.sh');
 assert.match(source,/--bind 127\.0\.0\.1/);
 assert.doesNotMatch(source,/\bsudo\s|\bssh\s|\bnft\s|\btailscale\s+(up|set|down)/i);
});
