// Pure, deterministic projection of an *offline fixture*, not live monitoring.
export const STATUSES = Object.freeze(['OK','DEGRADED','DOWN','STALE','UNKNOWN','OFFLINE']);
const valid = new Set(STATUSES);
const parseTime = (s) => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s) ? Date.parse(s) : NaN;
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
  const ids=new Set();
  for(const s of scene.signals){
    if(!s || typeof s.id!=='string' || !/^[a-z0-9-]{2,45}$/.test(s.id) || ids.has(s.id) ||
       typeof s.name!=='string' || s.name.length>100 || typeof s.source!=='string' || s.source.length>100 ||
       (s.measuredStatus !== undefined && !valid.has(s.measuredStatus)) ||
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
