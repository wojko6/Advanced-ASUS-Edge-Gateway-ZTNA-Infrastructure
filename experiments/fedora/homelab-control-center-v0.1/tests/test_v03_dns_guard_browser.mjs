import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {normalizeDnsGuard} from '../dns-guard-model.mjs';

const OBS='2026-10-26T10:55:33Z';
const NOW=new Date('2026-10-26T10:55:34Z');
const VALID={
 schema_version:'0.3',kind:'dns-guard-telemetry',mode:'manual-local-vm-readonly',
 observed_at:OBS,status:'OK',reason_code:'LOCAL_MODE_REPORTED',
 dns_mode:'LOCAL',collection_age_seconds:53.4,ttl_seconds:180,
 breakglass_active:false,watchdog_present:true
};
test('fresh explicit local telemetry is OK but remains a DNS mode observation',()=>{
 const r=normalizeDnsGuard(VALID,NOW);
 assert.equal(r.status,'OK');
 assert.equal(r.reason_code,'LOCAL_MODE_REPORTED');
 assert.equal(r.collection_age_seconds,53.4);
 assert.ok(!('dns_queries_ok' in r));
});
test('bootstrap/breakglass/watchdog signals display DEGRADED only with internally consistent flags',()=>{
 const scenarios=[
  {...VALID,status:'DEGRADED',dns_mode:'BOOTSTRAP',reason_code:'BOOTSTRAP_MODE'},
  {...VALID,status:'DEGRADED',breakglass_active:true,reason_code:'BREAKGLASS_ACTIVE'},
  {...VALID,status:'DEGRADED',watchdog_present:false,reason_code:'WATCHDOG_NOT_PRESENT'}
 ];
 for(const sample of scenarios)assert.equal(normalizeDnsGuard(sample,NOW).status,'DEGRADED');
});
test('old sample and time elapsed since summary cannot keep green state',()=>{
 const old={...VALID,status:'STALE',reason_code:'COLLECTION_TOO_OLD',dns_mode:'UNVERIFIED',
   breakglass_active:null,watchdog_present:null,collection_age_seconds:181};
 assert.equal(normalizeDnsGuard(old,NOW).status,'STALE');
 assert.equal(normalizeDnsGuard(VALID,new Date('2026-10-26T10:58:00Z')).status,'STALE');
});
test('unknown remains unknown and does not expose stale last good data',()=>{
 const payload={...VALID,status:'UNKNOWN',dns_mode:'UNVERIFIED',reason_code:'SOURCE_UNAVAILABLE_OR_INVALID',
   collection_age_seconds:null,breakglass_active:null,watchdog_present:null};
 assert.equal(normalizeDnsGuard(payload,NOW).status,'UNKNOWN');
 assert.equal(normalizeDnsGuard(null,NOW).status,'UNKNOWN');
});
test('malformed, mislabeled, inconsistent, future or mixed status is rejected',()=>{
 const samples=[
 {...VALID,schema_version:'0.2'},
 {...VALID,status:'UP'},
 {...VALID,mode:'demo'},
 {...VALID,observed_at:'2026-10-26T10:55:33.001Z'},
 {...VALID,observed_at:'2026-10-26T12:55:33Z'},
 {...VALID,ttl_seconds:600},
 {...VALID,collection_age_seconds:NaN},
 {...VALID,collection_age_seconds:-1},
 {...VALID,breakglass_active:true},
 {...VALID,watchdog_present:false},
 {...VALID,dns_mode:'BOOTSTRAP'},
 {...VALID,status:'DEGRADED',reason_code:'LOCAL_MODE_REPORTED'},
 {...VALID,status:'STALE',reason_code:'COLLECTION_TOO_OLD'},
 {...VALID,status:'UNKNOWN'},
];
 for(const input of samples)assert.equal(normalizeDnsGuard(input,NOW).status,'UNKNOWN');
});
test('separate V0.3 frontend uses same-origin bounded GET and no auto poll',()=>{
 const root=resolve(import.meta.dirname,'..');
 const page=readFileSync(resolve(root,'index-v03.html'),'utf8');
 const js=readFileSync(resolve(root,'dns-guard-live.mjs'),'utf8');
 const old=readFileSync(resolve(root,'index-live.html'),'utf8');
 assert.match(page,/id="live-dns-guard"/);
 assert.match(page,/dns-guard-live\.mjs/);
 assert.match(page,/pozostają fikcyjne/);
 assert.doesNotMatch(old,/dns-guard-live\.mjs/);
 assert.match(js,/fetch\('\/api\/dns-guard'/);
 assert.match(js,/credentials:'omit'/);
 assert.match(js,/redirect:'error'/);
 assert.match(js,/controller\.abort\(\),10000/);
 assert.match(js,/document\.addEventListener\('visibilitychange'/);
 assert.doesNotMatch(js,/setInterval\(/);
 assert.doesNotMatch(js,/\.innerHTML\s*=/);
});
