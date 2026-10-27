import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normalizeHistory} from '../dns-history-archive-model.mjs';
const fixture={
 schema_version:'0.5',kind:'dns-guard-history-archive',
 mode:'manual-fixed-archive-readonly',
 status:'ARCHIVE_VERIFIED',reason_code:'SAMPLED_TRANSITIONS_CORROBORATED',
 source:'FEDORA_VM_SEVEN_FIXED_DNS_GUARD_RAW_EXPORTS',
 archive_start:'2026-10-27T14:40:00Z',archive_end:'2026-10-27T16:43:00Z',
 sample_count:113,event_count:2,
 events:[
  {type:'LOCAL_TO_BOOTSTRAP',from:'LOCAL',to:'BOOTSTRAP',
   window_start_local:'2026-10-27T17:01:35.572+01:00',
   window_end_local:'2026-10-27T17:02:39.162+01:00',
   reported_at_local:'2026-10-27T17:02:11.000+01:00',
   gap_seconds:63.59,confidence:'BOUNDED_OBSERVATION'},
  {type:'BOOTSTRAP_TO_LOCAL',from:'BOOTSTRAP',to:'LOCAL',
   window_start_local:'2026-10-27T17:04:48.836+01:00',
   window_end_local:'2026-10-27T17:05:55.563+01:00',
   reported_at_local:'2026-10-27T17:05:01.000+01:00',
   gap_seconds:66.727,confidence:'BOUNDED_OBSERVATION'}
 ]};
test('archive contract presents two observed transition windows, not LIVE uptime',()=>{
 const result=normalizeHistory(fixture);
 assert.equal(result.status,'ARCHIVE_VERIFIED');
 assert.equal(result.sample_count,113);
 assert.equal(result.events.length,2);
 assert.equal(result.events[0].from,'LOCAL');
 assert.equal(result.events[1].to,'LOCAL');
 assert.equal(result.events[0].gap_seconds,63.59);
});
test('malformed provenance, reinterpreted source or arbitrary dates fail closed',()=>{
 const changes=[
  {status:'OK'}, {kind:'live-dns'}, {source:'raw private'},
  {mode:'live-stream'},{archive_start:'2026-10-01T00:00:00Z'},
  {event_count:3}, {sample_count:201},
  {events:[{type:'evil'}]}, {events:null}
 ];
 for(const change of changes)assert.equal(normalizeHistory({...fixture,...change}).status,'UNKNOWN');
});
test('malformed, overlapping or impossible event windows are rejected',()=>{
 const original=fixture.events[0];
 for(const entry of [
  {...original,from:'BOOTSTRAP'},
  {...original,confidence:'CERTAIN_ROOT_CAUSE'},
  {...original,gap_seconds:-1},
  {...original,gap_seconds:100},
  {...original,reported_at_local:'2026-10-27T17:00:00.000+01:00'},
  {...original,window_end_local:'2026-10-27T17:01:00.000+01:00'},
  {...original,window_start_local:'2026-10-28T17:01:35.572+01:00'},
  {...original,reported_at_local:'PRIVATE_VALUE'},
 ]){
  assert.equal(normalizeHistory({...fixture,event_count:1,events:[entry]}).status,'UNKNOWN');
 }
 const reverse={...fixture,events:[fixture.events[1],fixture.events[0]]};
 assert.equal(normalizeHistory(reverse).status,'UNKNOWN');
});
test('UNKNOWN does not revive a previous successful result',()=>{
 const invalid={...fixture,status:'UNKNOWN',reason_code:'ARCHIVE_EVIDENCE_NOT_VERIFIED',
  event_count:0,events:[],sample_count:null};
 assert.equal(normalizeHistory(invalid).status,'UNKNOWN');
 assert.equal(normalizeHistory(null).events.length,0);
});
test('page preserves all three LIVE panels and clearly separates historical archive',()=>{
 const html=readFileSync(new URL('../index-v05.html',import.meta.url),'utf8');
 const old=readFileSync(new URL('../index-v04.html',import.meta.url),'utf8');
 for(const token of ['id="live-vm"','id="live-dns-guard"','id="live-router-dns"',
                     'id="dns-history-archive"','ARCHIWUM','data-demo-gate="opt-in"',
                     'dns-history-archive.mjs','dns-history-archive.css']){
  assert.ok(html.includes(token),token);
 }
 assert.ok(!old.includes('dns-history-archive'));
 assert.ok(html.includes("connect-src 'self'"));
});
test('archive view is manual only and uses textContent without dangerous DOM writes',()=>{
 const js=readFileSync(new URL('../dns-history-archive.mjs',import.meta.url),'utf8');
 assert.ok(js.includes("fetch('/api/dns-guard-history-archive'"));
 assert.ok(js.includes("button.addEventListener('click',readArchive)"));
 assert.ok(!js.includes('readArchive();'));
 assert.ok(js.includes("credentials:'omit'"));
 assert.ok(js.includes("redirect:'error'"));
 assert.ok(js.includes('textContent'));
 assert.ok(!js.includes('innerHTML'));
 assert.ok(!js.includes('setInterval'));
 assert.ok(!js.includes('localStorage'));
});
