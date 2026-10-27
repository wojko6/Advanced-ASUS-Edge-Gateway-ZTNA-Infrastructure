import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normalizeRouterDns} from '../router-dns-model.mjs';

const at=new Date('2026-10-27T14:00:02Z');
const ok={
 schema_version:'0.4',kind:'router-dns-probe',mode:'manual-local-vm-readonly',
 source:'VictoriaMetrics / Blackbox internet_dns / fixed aggregates',
 observed_at:'2026-10-27T14:00:00Z',status:'OK',
 reason_code:'ONE_DNS_PROBE_SUCCEEDED',probe_success:true,
 sample_age_seconds:1.5,ttl_seconds:120,
 limitation:'One Blackbox UDP A-record query for example.com via the configured router DNS resolver; not Pi-hole/Unbound health, DNSSEC, all clients, the router\'s overall uptime, or continuous DNS availability.'
};
const status=(data,now=at)=>normalizeRouterDns(data,now);
const fail={...ok,status:'DEGRADED',reason_code:'ONE_DNS_PROBE_FAILED',probe_success:false};

test('V0.4 one fresh scoped probe is OK; one failed probe is only DEGRADED',()=>{
 assert.equal(status(ok).status,'OK');
 assert.equal(status(ok).probe_success,true);
 assert.equal(status(fail).status,'DEGRADED');
 assert.equal(status(fail).probe_success,false);
 assert.notEqual(status(fail).status,'DOWN');
});

test('expiry invalidates previous green AND previous failure with no re-query',()=>{
 for(const state of [ok,fail]){
  const got=status(state,new Date('2026-10-27T14:02:01Z'));
  assert.equal(got.status,'STALE');
  assert.equal(got.probe_success,null);
 }
});

test('server-side contradictory status, reason, value and timestamp never survive',()=>{
 const candidates=[
  {...ok,status:'DEGRADED'},
  {...ok,reason_code:'ONE_DNS_PROBE_FAILED'},
  {...ok,probe_success:false},
  {...fail,reason_code:'ONE_DNS_PROBE_SUCCEEDED'},
  {...fail,probe_success:true},
  {...ok,sample_age_seconds:-0.1},
  {...ok,sample_age_seconds:Number.NaN},
  {...ok,ttl_seconds:99999},
  {...ok,kind:'any-metric'},
  {...ok,observed_at:'2026-02-30T14:00:00Z'},
  {...ok,observed_at:'2026-10-27T15:00:00Z'},
  {...ok,source:'raw router private source'},
  {...ok,limitation:'DNS healthy'},
  null,[],
 ];
 for(const val of candidates)
  assert.equal(status(val).status,'UNKNOWN',JSON.stringify(val));
});

test('valid STALE and UNKNOWN server states remain neutral',()=>{
 const stale={...ok,status:'STALE',reason_code:'DNS_PROBE_SAMPLE_TOO_OLD',
              probe_success:null,sample_age_seconds:121};
 assert.equal(status(stale).status,'STALE');
 const unknown={...ok,status:'UNKNOWN',reason_code:'EVIDENCE_NOT_VERIFIED',
                probe_success:null,sample_age_seconds:null};
 assert.equal(status(unknown).status,'UNKNOWN');
 assert.equal(status({...unknown,probe_success:true}).status,'UNKNOWN');
 assert.equal(status({...stale,probe_success:true}).status,'UNKNOWN');
});

test('V0.4 is a separate opt-in page with three LIVE regions, V0.3 DEMO untouched',()=>{
 const html=readFileSync(new URL('../index-v04.html',import.meta.url),'utf8');
 const previous=readFileSync(new URL('../index-v03.html',import.meta.url),'utf8');
 const live=readFileSync(new URL('../router-dns-live.mjs',import.meta.url),'utf8');
 for(const token of ['data-demo-gate="opt-in"','id="demo-toggle"',
                     'id="live-vm"','id="live-dns-guard"','id="live-router-dns"'])
  assert.ok(html.includes(token),token);
 assert.ok(html.includes('connect-src \'self\''));
 assert.ok(html.includes('pozostają fikcyjne'));
 assert.ok(!previous.includes('live-router-dns'));
 assert.ok(live.includes("fetch('/api/router-dns'"));
 assert.ok(live.includes('credentials:\'omit\''));
 assert.ok(live.includes('textContent'));
 assert.ok(!live.includes('innerHTML'));
 assert.ok(!live.includes('setInterval'));
});

test('V0.4 DNS parser rejects cross-scope or stale labels without leaking data',()=>{
 const other={...ok,source:'Pi-hole query log: PRIVATE'};
 assert.equal(status(other).status,'UNKNOWN');
 assert.equal(status({...ok,observed_at:'2026-10-27T13:50:00Z'}).status,'STALE');
});
