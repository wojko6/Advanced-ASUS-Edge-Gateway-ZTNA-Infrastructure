import {test} from 'node:test';
import assert from 'node:assert/strict';
import {SCENARIOS} from '../data.mjs';
import {evaluate,project,summary,validateScenario} from '../model.mjs';
const by=(scene,id)=>project(scene).find(x=>x.id===id);
test('six valid, uniquely named fixture scenarios',()=>{
 assert.equal(SCENARIOS.length,6);
 assert.equal(new Set(SCENARIOS.map(x=>x.id)).size,6);
 for(const s of SCENARIOS)assert.equal(validateScenario(s),true);
});
test('healthy fixture is six OK components',()=>{
 const rows=project(SCENARIOS[0]); assert.equal(summary(rows).OK,6);
 assert.equal(rows.every(x=>x.ageSeconds===15),true);
});
test('DNS degradation does not overwrite availability of other services',()=>{
 assert.equal(by(SCENARIOS[1],'dns').status,'DEGRADED');
 assert.equal(by(SCENARIOS[1],'asus').status,'OK');
});
test('old telemetry is STALE, not OK',()=>assert.equal(by(SCENARIOS[2],'monitoring').status,'STALE'));
test('planned outage is OFFLINE but absent DNS telemetry stays UNKNOWN',()=>{
 assert.equal(by(SCENARIOS[3],'asus').status,'OFFLINE');
 assert.equal(by(SCENARIOS[3],'dns').status,'UNKNOWN');
});
test('unavailable source is UNKNOWN, not DOWN',()=>assert.equal(by(SCENARIOS[4],'monitoring').status,'UNKNOWN'));
test('conflicting fresh evidence is DEGRADED',()=>assert.equal(by(SCENARIOS[5],'dns').status,'DEGRADED'));
test('future and malformed timestamps fail closed',()=>{
 const ref=SCENARIOS[0]; const s={...ref.signals[0],observedAt:'2099-01-01T00:00:00Z'};
 assert.equal(evaluate(s,ref.generatedAt).status,'UNKNOWN');
 assert.equal(evaluate({...s,observedAt:'unparseable'},ref.generatedAt).status,'UNKNOWN');
});
test('negative TTL, duplicate IDs and invalid schema fail closed',()=>{
 const s=SCENARIOS[0];
 assert.equal(validateScenario({...s,signals:[{...s.signals[0],ttlSeconds:-1}]}),false);
 assert.equal(validateScenario({...s,signals:[s.signals[0],s.signals[0]]}),false);
 assert.equal(validateScenario({...s,schemaVersion:'999'}),false);
 assert.throws(()=>project({...s,mode:'live'}));
});
test('source can report DOWN only with fresh evidence',()=>{
 const s=SCENARIOS[0],row={...s.signals[0],measuredStatus:'DOWN'};
 assert.equal(evaluate(row,s.generatedAt).status,'DOWN');
 assert.equal(evaluate({...row,sourceAvailable:false},s.generatedAt).status,'UNKNOWN');
});
