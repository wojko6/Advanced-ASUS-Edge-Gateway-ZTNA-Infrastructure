// Strict V0.3 DNS Guard telemetry display model: never re-use old green state.
const STATES=new Set(['OK','DEGRADED','STALE','UNKNOWN']);
const REASONS=new Set([
 'LOCAL_MODE_REPORTED','BOOTSTRAP_MODE','BREAKGLASS_ACTIVE','WATCHDOG_NOT_PRESENT',
 'COLLECTION_TOO_OLD','SOURCE_UNAVAILABLE_OR_INVALID','TELEMETRY_NOT_VERIFIED',
 'STATE_NOT_VALID','MODE_FLAGS_INVALID'
]);
const fallback=(reason='SOURCE_UNAVAILABLE_OR_INVALID',status='UNKNOWN')=>({
 status,dns_mode:'UNVERIFIED',breakglass_active:null,watchdog_present:null,
 collection_age_seconds:null,observed_at:null,ttl_seconds:null,reason_code:reason
});
export function normalizeDnsGuard(x,now){
 const unknown=fallback();
 if(!x||typeof x!=='object'||Array.isArray(x)||
    x.schema_version!=='0.3'||x.kind!=='dns-guard-telemetry'||
    x.mode!=='manual-local-vm-readonly'||!STATES.has(x.status)||
    !REASONS.has(x.reason_code)||x.ttl_seconds!==180||
    typeof x.observed_at!=='string'||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(x.observed_at))return unknown;
 const timestamp=Date.parse(x.observed_at);
 if(!Number.isFinite(timestamp)||
    new Date(timestamp).toISOString().replace('.000Z','Z')!==x.observed_at)return unknown;
 const secondsSince=(now.getTime()-timestamp)/1000;
 if(!Number.isFinite(secondsSince)||secondsSince < -5)return unknown;
 if(x.status==='UNKNOWN'){
   if(x.dns_mode!=='UNVERIFIED'||x.breakglass_active!==null||
      x.watchdog_present!==null||![
        'SOURCE_UNAVAILABLE_OR_INVALID','TELEMETRY_NOT_VERIFIED',
        'STATE_NOT_VALID','MODE_FLAGS_INVALID'
      ].includes(x.reason_code))return unknown;
   return {...unknown,reason_code:x.reason_code,observed_at:x.observed_at};
 }
 if(typeof x.collection_age_seconds!=='number'||
    !Number.isFinite(x.collection_age_seconds)||x.collection_age_seconds<0||
    x.collection_age_seconds>86400)return unknown;
 const effectiveAge=x.collection_age_seconds+Math.max(0,secondsSince);
 if(x.status==='STALE'){
    if(x.reason_code!=='COLLECTION_TOO_OLD'||
       x.collection_age_seconds<=x.ttl_seconds||
       x.dns_mode!=='UNVERIFIED'||x.breakglass_active!==null||
       x.watchdog_present!==null)return unknown;
    return {...fallback('COLLECTION_TOO_OLD','STALE'),observed_at:x.observed_at,
            collection_age_seconds:x.collection_age_seconds,ttl_seconds:x.ttl_seconds};
 }
 if(effectiveAge>180){
    return {...fallback('COLLECTION_TOO_OLD','STALE'),observed_at:x.observed_at,
            collection_age_seconds:effectiveAge,ttl_seconds:x.ttl_seconds};
 }
 if(!['LOCAL','BOOTSTRAP'].includes(x.dns_mode)||
    typeof x.breakglass_active!=='boolean'||
    typeof x.watchdog_present!=='boolean')return unknown;
 const ok=x.status==='OK'&&x.reason_code==='LOCAL_MODE_REPORTED'&&
          x.dns_mode==='LOCAL'&&!x.breakglass_active&&x.watchdog_present;
 const degraded=x.status==='DEGRADED'&&(
   (x.reason_code==='BREAKGLASS_ACTIVE'&&x.breakglass_active)||
   (x.reason_code==='WATCHDOG_NOT_PRESENT'&&!x.breakglass_active&&!x.watchdog_present)||
   (x.reason_code==='BOOTSTRAP_MODE'&&x.dns_mode==='BOOTSTRAP'&&
    !x.breakglass_active&&x.watchdog_present)
 );
 if(!ok&&!degraded)return unknown;
 return {status:x.status,dns_mode:x.dns_mode,
   breakglass_active:x.breakglass_active,watchdog_present:x.watchdog_present,
   collection_age_seconds:x.collection_age_seconds,observed_at:x.observed_at,
   ttl_seconds:x.ttl_seconds,reason_code:x.reason_code};
}
