import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {normalizeLive} from '../live-model.mjs';
const NOW=new Date('2026-10-25T13:01:00Z');
const value={schema_version:'0.2',mode:'live-readonly',source:'VictoriaMetrics / 127.0.0.1:8428 / fixed PromQL',
 observed_at:'2026-10-25T13:00:59Z',status:'OK',reason_code:'ALL_SCRAPE_TARGETS_UP',total:7,healthy:7,
 oldest_sample_age_seconds:29.7,ttl_seconds:120};
test('valid fresh aggregate only reflects scrape status',()=>{
 const r=normalizeLive(value,NOW);assert.equal(r.status,'OK');assert.equal(r.healthy,7);assert.equal(r.total,7);
});
test('missing, malformed, stale or contradictory data cannot look OK',()=>{
 const cases=[null,{}, {...value,healthy:8},{...value,healthy:'7'},
 {...value,oldest_sample_age_seconds:300}, {...value,observed_at:'2026-10-25T12:57:00Z'},
 {...value,observed_at:'2026-02-31T13:00:00Z'}, {...value,status:'BOGUS'},
 {...value,mode:'demo'}, {...value,reason_code:'<script>'}];
 for(const c of cases)assert.notEqual(normalizeLive(c,NOW).status,'OK');
});
test('stale or partial signal retains explicit verdict',()=>{
 assert.equal(normalizeLive({...value,status:'STALE',reason_code:'SCRAPE_SAMPLES_TOO_OLD',oldest_sample_age_seconds:150},NOW).status,'STALE');
 assert.equal(normalizeLive({...value,status:'DEGRADED',reason_code:'SOME_SCRAPE_TARGETS_DOWN',healthy:6},NOW).status,'DEGRADED');
 assert.equal(normalizeLive({...value,status:'DOWN',reason_code:'ALL_SCRAPE_TARGETS_DOWN',healthy:0},NOW).status,'DOWN');
});
test('live widget isolated from demo fixtures and uses safe DOM updates',()=>{
 const root=resolve(import.meta.dirname,'..');const html=readFileSync(resolve(root,'index-live.html'),'utf8');
 const code=readFileSync(resolve(root,'live.mjs'),'utf8');
 assert.match(html,/connect-src 'self'/);assert.match(html,/DEMO/);
 assert.match(code,/fetch\('\/api\/summary'/);assert.doesNotMatch(code,/\.innerHTML\s*=/);
 assert.doesNotMatch(code,/setInterval/);
});


test('hybrid copy identifies local API; offline V0.1 keeps its original wording',()=>{
 const root=resolve(import.meta.dirname,'..');
 const app=readFileSync(resolve(root,'app.mjs'),'utf8');
 assert.match(app,/Boolean\(document\.getElementById\('live-vm'\)\)/);
 assert.match(app,/Górny kafelek pobiera wyłącznie zbiorcze metryki/);
 assert.match(app,/Nie ma odpytywania serwerów/);
 const hybrid=readFileSync(resolve(root,'index-live.html'),'utf8');
 assert.match(hybrid,/Lokalny odczyt \+ DEMO/);
 const fixture=readFileSync(resolve(root,'index-fixture.html'),'utf8');
 assert.match(fixture,/data-fixture-mode="true"/);
 assert.match(fixture,/ZERO DANYCH RZECZYWISTYCH/);
});

test('visual fault scenarios: fresh partial/down; stale and expired green never stay OK',()=>{
 const input=(changed)=>({...value,...changed});
 assert.equal(normalizeLive(input({status:'DEGRADED',healthy:5,reason_code:'SOME_SCRAPE_TARGETS_DOWN'}),NOW).status,'DEGRADED');
 assert.equal(normalizeLive(input({status:'DOWN',healthy:0,reason_code:'ALL_SCRAPE_TARGETS_DOWN'}),NOW).status,'DOWN');
 assert.equal(normalizeLive(input({status:'STALE',oldest_sample_age_seconds:155,reason_code:'SCRAPE_SAMPLES_TOO_OLD'}),NOW).status,'STALE');
 assert.equal(normalizeLive(input({observed_at:'2026-10-25T12:57:00Z'}),NOW).status,'STALE');
 assert.equal(normalizeLive(input({status:'UNKNOWN',healthy:null,total:null,oldest_sample_age_seconds:null,reason_code:'SIMULATED_UNAVAILABLE'}),NOW).status,'UNKNOWN');
});

test('browser refresh has a bounded timeout and fail-closed recovery',()=>{
 const root=resolve(import.meta.dirname,'..');
 const code=readFileSync(resolve(root,'live.mjs'),'utf8');
 assert.match(code,/setTimeout\(\(\)=>controller\.abort\(\),8500\)/);
 assert.match(code,/finally\{clearTimeout\(timeout\);/);
 assert.match(code,/catch\(_\)\{lastData=null;/);
 assert.match(code,/draw\(null\)/);
});
