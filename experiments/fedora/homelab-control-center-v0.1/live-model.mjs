const STATUSES=new Set(['OK','DEGRADED','DOWN','STALE','UNKNOWN']);
export function normalizeLive(x,now){
 const unknown={status:'UNKNOWN',healthy:null,total:null,oldest_sample_age_seconds:null,ttl_seconds:null,observed_at:null,reason_code:'SOURCE_UNAVAILABLE_OR_INVALID'};
 if(!x||typeof x!=='object'||x.schema_version!=='0.2'||x.mode!=='live-readonly'||!STATUSES.has(x.status)||
    typeof x.observed_at!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(x.observed_at)||
    typeof x.reason_code!=='string'||!/^[A-Z_]{2,50}$/.test(x.reason_code)||
    !Number.isSafeInteger(x.ttl_seconds)||x.ttl_seconds<1||x.ttl_seconds>600) return unknown;
 const t=Date.parse(x.observed_at);
 if(!Number.isFinite(t)||new Date(t).toISOString().replace('.000Z','Z')!==x.observed_at)return unknown;
 const age=(now.getTime()-t)/1000;
 if(age < -5||age > x.ttl_seconds+15)return {...unknown,status:'STALE',reason_code:'SUMMARY_EXPIRED',observed_at:x.observed_at};
 if(x.status==='UNKNOWN')return {...unknown,observed_at:x.observed_at,reason_code:x.reason_code};
 if(!Number.isSafeInteger(x.total)||!Number.isSafeInteger(x.healthy)||x.total<1||x.total>10000||x.healthy<0||x.healthy>x.total||
    typeof x.oldest_sample_age_seconds!=='number'||!Number.isFinite(x.oldest_sample_age_seconds)||x.oldest_sample_age_seconds<0||x.oldest_sample_age_seconds>86400)return unknown;
 if(x.status!=='STALE'&&x.oldest_sample_age_seconds>x.ttl_seconds)return {...unknown,status:'STALE',reason_code:'SCRAPE_SAMPLES_TOO_OLD',observed_at:x.observed_at};
 if(x.status==='OK'&&x.healthy!==x.total)return unknown;
 if(x.status==='STALE'&&x.oldest_sample_age_seconds<=x.ttl_seconds)return unknown;
 if(x.status==='DOWN'&&x.healthy!==0)return unknown;
 if(x.status==='DEGRADED'&&(x.healthy===0||x.healthy===x.total))return unknown;
 return {status:x.status,total:x.total,healthy:x.healthy,observed_at:x.observed_at,oldest_sample_age_seconds:x.oldest_sample_age_seconds,ttl_seconds:x.ttl_seconds,reason_code:x.reason_code};
}
