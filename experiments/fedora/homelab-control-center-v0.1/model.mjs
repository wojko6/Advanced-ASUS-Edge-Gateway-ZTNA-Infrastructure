// Pure, deterministic projection of an *offline fixture*, not live monitoring.
export const STATUSES = Object.freeze(['OK','DEGRADED','DOWN','STALE','UNKNOWN','OFFLINE']);
const valid = new Set(STATUSES);
const parseTime = (s) => {\n  if(typeof s!=='string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s)) return NaN;\n  const t=Date.parse(s);\n  return Number.isFinite(t) && new Date(t).toISOString()===s ? t : NaN;\n};
export function evaluate(signal, generatedAt) {
  const fallback = {status:'UNKNOWN',reason:'Brak wiarygodnych danych',ageSeconds:null};
  if (!signal || typeof signal !== 'object' || !Number.isFinite(parseTime(generatedAt))) return fallback;
  if (signal.explicitPlannedOffline === true) {
    return {status:'OFFLINE',reason:signal.reason || 'Zaplanowane wyłączenie (dane demonstracyjne)',ageSeconds:null};
  }
  if (signal.sourceAvailable === false || !signal.observedAt) return { ...fallback,reason:'Źródło niedostępne lub brak obserwacji' };
  const at=parseTime(signal.observedAt), base=parseTime(generatedAt);
  if (!Number.isFinite(at) || at > base || !Number.isFinite(signal.ttlSeconds) || signal.ttlSeconds <= 0) {
    return {...fallback,reason:'Nieprawidłowy znacznik czasu lub TTL'};
  }
  const ageSeconds = Math.floor((base-at)/1000);
  if (ageSeconds > signal.ttlSeconds) return {status:'STALE',reason:'Dane starsze niż deklarowany TTL',ageSeconds};
  if (signal.conflicting === true) return {status:'DEGRADED',reason:'Sprzeczne obserwacje — wymaga przeglądu',ageSeconds};
  if (!valid.has(signal.measuredStatus) || ['UNKNOWN','STALE','OFFLINE'].includes(signal.measuredStatus)) {
    return {status:'UNKNOWN',reason:'Nieprawidłowy lub nierozstrzygnięty werdykt źródła',ageSeconds};
  }
  return {status:signal.measuredStatus,reason:String(signal.reason || 'Odczyt testowy'),ageSeconds};
}
export function validateScenario(scene) {
  if (!scene || scene.mode !== 'demo' || scene.schemaVersion !== '1.0' || !Number.isFinite(parseTime(scene.generatedAt))) return false;
  if (!Array.isArray(scene.signals) || scene.signals.length<1 || scene.signals.length>30) return false;
  if(!Array.isArray(scene.events) || scene.events.length>100 ||
     !scene.events.every(e=>e && typeof e.at==='string' && /^\d{2}:\d{2}$/.test(e.at) &&
       +e.at.slice(0,2)<24 && +e.at.slice(3,5)<60 &&
       ['healthy','warning','critical'].includes(e.severity) &&
       typeof e.title==='string' && e.title.length>0 && e.title.length<=150 &&
       typeof e.note==='string' && e.note.length<=300)) return false;
  if(!Array.isArray(scene.recovery) || scene.recovery.length>20 ||
     !scene.recovery.every(r=>r && ['key','value','hint'].every(k=>
       typeof r[k]==='string' && r[k].length>0 && r[k].length<=250))) return false;
  const ids=new Set();
  for(const s of scene.signals){
    if(!s || typeof s.id!=='string' || !/^[a-z0-9-]{2,45}$/.test(s.id) || ids.has(s.id) ||
       typeof s.name!=='string' || s.name.length>100 || typeof s.source!=='string' || s.source.length>100 ||
       (s.sourceAvailable!==undefined && typeof s.sourceAvailable!=='boolean') ||\n       (s.explicitPlannedOffline!==undefined && typeof s.explicitPlannedOffline!=='boolean') ||\n       (s.conflicting!==undefined && typeof s.conflicting!=='boolean') ||\n       (s.observedAt!==undefined && s.observedAt!==null && !Number.isFinite(parseTime(s.observedAt))) ||\n       (s.measuredStatus !== undefined && !valid.has(s.measuredStatus)) ||
       (s.ttlSeconds!==undefined && (!Number.isFinite(s.ttlSeconds) || s.ttlSeconds<=0 || s.ttlSeconds>86400))) return false;
    ids.add(s.id);
  }
  return true;
}
export function project(scene) {
  if (!validateScenario(scene)) throw Error('Invalid offline fixture schema');
  return scene.signals.map(s=>({...s,...evaluate(s,scene.generatedAt)}));
}
export function summary(rows){
  const counts=Object.fromEntries(STATUSES.map(x=>[x,0]));
  for(const row of rows){counts[row.status]=(counts[row.status]||0)+1;}
  return counts;
}
