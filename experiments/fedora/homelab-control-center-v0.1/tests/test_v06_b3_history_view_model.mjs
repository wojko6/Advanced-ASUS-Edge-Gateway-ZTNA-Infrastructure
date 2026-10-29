import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normalizeCoverage,formatWarsawUtc} from '../dns-history-coverage-model.mjs';

const START='2026-10-28T12:00:00.000Z';
const END='2026-10-29T12:00:00.000Z';
const FIRST='2026-10-29T11:00:00.000Z';
const sec=(a,b)=>(Date.parse(b)-Date.parse(a))/1000;
const gap=(position,a,b)=>({kind:'TELEMETRY_GAP',position,
 start_utc:a,end_utc:b,duration_seconds:sec(a,b),cause:'NOT_DETERMINED'});
const segment=(a,b,n)=>({kind:'OBSERVED_TELEMETRY_SEGMENT',
 start_utc:a,end_utc:b,sample_count:n,
 interpretation:'SAMPLED_TELEMETRY_NOT_DNS_UPTIME'});
function sample(){
 return {
  schema_version:'hcc-dns-guard-coverage/0.6-b1',
  source_adapter:'hcc-dns-guard-history-source/0.6-b2',
  source:'FEDORA_VM_SEVEN_DNS_GUARD_SERIES',
  mode:'OFFLINE_EVIDENCE_ONLY',deployment_gate:'HOLD',
  status:'COVERAGE_OBSERVED_WITH_UNCERTAINTY',
  reason_code:'SAMPLED_COVERAGE_ONLY',window:'24h',
  window_start_utc:START,window_end_utc:END,sample_count:1,
  invalid_sample_count:0,max_cross_series_skew_ms:0,
  gaps:[gap('LEADING',START,FIRST),gap('TRAILING',FIRST,END)],
  segments:[segment(FIRST,FIRST,1)]
 };
}
const clone=x=>structuredClone(x);

test('B3A accepts sanitized sampled evidence, without inventing DNS health',()=>{
 const source=sample();
 source.private_router='DO_NOT_EXPOSE';
 const data=normalizeCoverage(source,'24h');
 assert.equal(data.status,'COVERAGE_OBSERVED_WITH_UNCERTAINTY');
 assert.equal(data.sample_count,1);
 assert.deepEqual(data.gaps.map(g=>g.position),['LEADING','TRAILING']);
 assert.equal(data.gaps[0].cause,'NOT_DETERMINED');
 assert.equal(data.segments[0].interpretation,'SAMPLED_TELEMETRY_NOT_DNS_UPTIME');
 assert.ok(!JSON.stringify(data).includes('DO_NOT_EXPOSE'));
 assert.ok(!JSON.stringify(data).includes('DNS_OUTAGE'));
});

test('complete 1h sampled stream remains sampled evidence, never uptime proof',()=>{
 const start='2026-10-29T11:00:00.000Z',end='2026-10-29T12:00:00.000Z';
 const source={...sample(),status:'COVERAGE_OBSERVED',window:'1h',
   window_start_utc:start,window_end_utc:end,sample_count:31,
   gaps:[],segments:[segment(start,end,31)]};
 const data=normalizeCoverage(source,'1h');
 assert.equal(data.status,'COVERAGE_OBSERVED');
 assert.equal(data.message.includes('brak dowodu ciągłości DNS'),true);
});

test('wrong request/provenance/status cannot be displayed as observed history',()=>{
 for(const override of [
  {schema_version:'0.5'},{source:'untrusted'},
  {source_adapter:'unverified'},{deployment_gate:'OPEN'},
  {mode:'LIVE'},{window:'7d'}, {status:'DNS_OK'},
  {reason_code:'UPTIME_VERIFIED'}, {sample_count:12001},
  {invalid_sample_count:2},{max_cross_series_skew_ms:5001},
  {window_end_utc:'2026-10-29T11:59:00.000Z'},
  {window_start_utc:'2026-02-30T12:00:00.000Z'},
  {segments:[]}
 ]){
  assert.equal(normalizeCoverage({...sample(),...override},'24h').status,'UNKNOWN',
    JSON.stringify(override));
 }
 assert.equal(normalizeCoverage(sample(),'7d').status,'UNKNOWN');
 assert.equal(normalizeCoverage(sample(),'__proto__').status,'UNKNOWN');
});

test('gaps cannot assert a cause, be reordered, forged or overlap segments',()=>{
 const src=sample();
 const failures=[
  {gaps:[{...src.gaps[0],cause:'PLANNED_SHUTDOWN'},src.gaps[1]]},
  {gaps:[src.gaps[1],src.gaps[0]]},
  {gaps:[{...src.gaps[0],duration_seconds:123},src.gaps[1]]},
  {gaps:[{...src.gaps[0],position:'INTERNAL'},src.gaps[1]]},
  {gaps:[{...src.gaps[0],end_utc:'2026-10-29T11:30:00.000Z',
     duration_seconds:sec(START,'2026-10-29T11:30:00.000Z')},src.gaps[1]]},
  {gaps:[{...src.gaps[0],start_utc:'INVALID'},src.gaps[1]]},
  {gaps:Array.from({length:129},()=>src.gaps[0])}
 ];
 for(const override of failures){
  assert.equal(normalizeCoverage({...clone(src),...override},'24h').status,'UNKNOWN');
 }
});

test('mismatched segment/sample arithmetic and impossible ranges fail closed',()=>{
 const src=sample();
 const cases=[
  {segments:[{...src.segments[0],sample_count:2}]},
  {segments:[{...src.segments[0],start_utc:END}]},
  {segments:[src.segments[0],src.segments[0]]},
  {status:'COVERAGE_OBSERVED'},
  {invalid_sample_count:1},
 ];
 for(const override of cases)
  assert.equal(normalizeCoverage({...clone(src),...override},'24h').status,'UNKNOWN');
});

test('real B1 internal gap starting exactly at window boundary is valid',()=>{
 const start='2026-10-29T11:00:00.000Z';
 const second='2026-10-29T11:05:00.000Z';
 const end='2026-10-29T12:00:00.000Z';
 const source={...sample(),window:'1h',window_start_utc:start,window_end_utc:end,
  sample_count:2,gaps:[gap('INTERNAL',start,second),gap('TRAILING',second,end)],
  segments:[segment(start,start,1),segment(second,second,1)]};
 const result=normalizeCoverage(source,'1h');
 assert.equal(result.status,'COVERAGE_OBSERVED_WITH_UNCERTAINTY');
 assert.deepEqual(result.gaps.map(g=>g.position),['INTERNAL','TRAILING']);
});

test('omitted boundary or internal gap cannot fake continuous coverage',()=>{
 const source=sample();
 const missingLeading={...source,gaps:[source.gaps[1]]};
 assert.equal(normalizeCoverage(missingLeading,'24h').status,'UNKNOWN');
 const early='2026-10-29T10:00:00.000Z';
 const late='2026-10-29T11:00:00.000Z';
 const missingInternal={...source,sample_count:2,
  gaps:[gap('LEADING',START,early),gap('TRAILING',late,END)],
  segments:[segment(early,early,1),segment(late,late,1)]};
 assert.equal(normalizeCoverage(missingInternal,'24h').status,'UNKNOWN');
 const missingTrailing={...source,gaps:[source.gaps[0]]};
 assert.equal(normalizeCoverage(missingTrailing,'24h').status,'UNKNOWN');
});

test('single-sample segment cannot claim hours of continuous observations',()=>{
 const start='2026-10-29T11:00:00.000Z';
 const end='2026-10-29T12:00:00.000Z';
 const source={...sample(),window:'1h',window_start_utc:start,window_end_utc:end,
  status:'COVERAGE_OBSERVED',sample_count:1,gaps:[],
  segments:[segment(start,end,1)]};
 assert.equal(normalizeCoverage(source,'1h').status,'UNKNOWN');
});

test('UNKNOWN, malformed, absent input never retain previous success',()=>{
 const once=normalizeCoverage(sample(),'24h');
 assert.equal(once.sample_count,1);
 const missing=normalizeCoverage(null,'24h');
 assert.equal(missing.status,'UNKNOWN');
 assert.deepEqual(missing.gaps,[]);
 const fromSource={...sample(),status:'UNKNOWN',reason_code:'SOURCE_UNAVAILABLE_OR_INVALID',
  sample_count:null,gaps:[],segments:[]};
 const unknown=normalizeCoverage(fromSource,'24h');
 assert.equal(unknown.status,'UNKNOWN');
 assert.deepEqual(unknown.segments,[]);
});

test('Warsaw fall DST repeated local 02:30 is distinguished by GMT offset',()=>{
 const before=formatWarsawUtc('2026-10-25T00:30:00.000Z');
 const after=formatWarsawUtc('2026-10-25T01:30:00.000Z');
 assert.match(before,/GMT\+2/);
 assert.match(after,/GMT\+1/);
 assert.notEqual(before,after);
 assert.equal(formatWarsawUtc('INVALID'),'NIEZWERYFIKOWANY CZAS');
});

test('B3A code remains a pure opt-in contract, not a source fetcher or runtime page',()=>{
 const code=readFileSync(new URL('../dns-history-coverage-model.mjs',import.meta.url),'utf8');
 const old=readFileSync(new URL('../index-v05.html',import.meta.url),'utf8');
 assert.ok(!code.includes('fetch('));
 assert.ok(!code.includes('XMLHttpRequest'));
 assert.ok(!code.includes('setInterval'));
 assert.ok(!code.includes('document.'));
 assert.ok(!code.includes('innerHTML'));
 assert.ok(!old.includes('dns-history-coverage-model.mjs'));
});
