// V0.4 Blackbox router-DNS observation: one DNS probe, not Pi-hole/Unbound health.
const REASONS=new Set(['ONE_DNS_PROBE_SUCCEEDED','ONE_DNS_PROBE_FAILED',
 'DNS_PROBE_SAMPLE_TOO_OLD','EVIDENCE_NOT_VERIFIED']);
const bad=()=>({
 status:'UNKNOWN',reason_code:'EVIDENCE_NOT_VERIFIED',
 probe_success:null,sample_age_seconds:null,observed_at:null,ttl_seconds:null
});
export function normalizeRouterDns(x,now){
 const unknown=bad();
 if(!x||typeof x!=='object'||Array.isArray(x)||!now||!Number.isFinite(now.getTime())||
    x.schema_version!=='0.4'||x.kind!=='router-dns-probe'||
    x.mode!=='manual-local-vm-readonly'||x.source!=='VictoriaMetrics / Blackbox internet_dns / fixed aggregates'||
    x.ttl_seconds!==120||!REASONS.has(x.reason_code)||
    typeof x.limitation!=='string'||!x.limitation.includes('not Pi-hole/Unbound health')||
    !['OK','DEGRADED','STALE','UNKNOWN'].includes(x.status)||
    typeof x.observed_at!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(x.observed_at))return unknown;
 const when=Date.parse(x.observed_at);
 if(!Number.isFinite(when)||new Date(when).toISOString().replace('.000Z','Z')!==x.observed_at)return unknown;
 const elapsed=(now.getTime()-when)/1000;
 if(elapsed < -5)return unknown;
 if(x.status==='UNKNOWN'){
    if(x.reason_code!=='EVIDENCE_NOT_VERIFIED'||x.probe_success!==null||
       x.sample_age_seconds!==null)return unknown;
    return {...unknown,observed_at:x.observed_at};
 }
 if(typeof x.sample_age_seconds!=='number'||!Number.isFinite(x.sample_age_seconds)||
    x.sample_age_seconds<0||x.sample_age_seconds>86400)return unknown;
 const age=x.sample_age_seconds+Math.max(0,elapsed);
 if(x.status==='STALE'){
    if(x.reason_code!=='DNS_PROBE_SAMPLE_TOO_OLD'||x.probe_success!==null||
       x.sample_age_seconds<=120)return unknown;
    return {status:'STALE',reason_code:'DNS_PROBE_SAMPLE_TOO_OLD',
      probe_success:null,sample_age_seconds:age,
      observed_at:x.observed_at,ttl_seconds:120};
 }
 if(x.probe_success!==true&&x.probe_success!==false)return unknown;
 if(x.status==='OK'&&!(x.probe_success===true&&x.reason_code==='ONE_DNS_PROBE_SUCCEEDED'))return unknown;
 if(x.status==='DEGRADED'&&!(x.probe_success===false&&x.reason_code==='ONE_DNS_PROBE_FAILED'))return unknown;
 if(age>120)return {status:'STALE',reason_code:'DNS_PROBE_SAMPLE_TOO_OLD',
      probe_success:null,sample_age_seconds:age,
      observed_at:x.observed_at,ttl_seconds:120};
 return {status:x.status,reason_code:x.reason_code,probe_success:x.probe_success,
   sample_age_seconds:age,observed_at:x.observed_at,ttl_seconds:120};
}
