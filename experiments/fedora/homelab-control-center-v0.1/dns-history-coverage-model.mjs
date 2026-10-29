// HCC V0.6-B3A — PURE, offline projection of B1/B2 sampled coverage.
// This module makes no network requests, never reconstructs router/DNS events,
// and is not imported into any existing HCC runtime page.
const WINDOW_MS=Object.freeze({ '1h':3600000,'6h':21600000,
 '24h':86400000,'7d':604800000 });
const COVERAGE_SCHEMA='hcc-dns-guard-coverage/0.6-b1';
const ADAPTER_SCHEMA='hcc-dns-guard-history-source/0.6-b2';
const SOURCE='FEDORA_VM_SEVEN_DNS_GUARD_SERIES';
const LIMIT=128;

function neutral(){
 return {status:'UNKNOWN',window:null,sample_count:null,
  invalid_sample_count:null,max_cross_series_skew_ms:null,
  gaps:[],segments:[],message:'Brak zweryfikowanej historii telemetrii.'};
}
function object(v){return v!==null&&typeof v==='object'&&!Array.isArray(v);}
function integer(v,lo,hi){return Number.isSafeInteger(v)&&v>=lo&&v<=hi;}
function instant(s){
 if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(s))
  return NaN;
 const ms=Date.parse(s);
 return Number.isFinite(ms)&&new Date(ms).toISOString()===s?ms:NaN;
}

/** Projection of one explicit fixed-window, sanitized B2 source response. */
export function normalizeCoverage(raw,expectedWindow){
 const bad=neutral();
 if(!Object.hasOwn(WINDOW_MS,expectedWindow)||!object(raw)||
    raw.schema_version!==COVERAGE_SCHEMA||
    raw.source_adapter!==ADAPTER_SCHEMA||raw.source!==SOURCE||
    raw.mode!=='OFFLINE_EVIDENCE_ONLY'||raw.deployment_gate!=='HOLD')
  return bad;
 // UNKNOWN must never retain or redisplay previous green/observed data.
 if(raw.status==='UNKNOWN')return bad;
 if(!['COVERAGE_OBSERVED','COVERAGE_OBSERVED_WITH_UNCERTAINTY'].includes(raw.status)||
    raw.reason_code!=='SAMPLED_COVERAGE_ONLY'||raw.window!==expectedWindow||
    !integer(raw.sample_count,1,12000)||
    !integer(raw.invalid_sample_count,0,raw.sample_count)||
    !integer(raw.max_cross_series_skew_ms,0,5000)||
    !Array.isArray(raw.gaps)||!Array.isArray(raw.segments)||
    raw.gaps.length>LIMIT||raw.segments.length>LIMIT)
  return bad;
 const start=instant(raw.window_start_utc),end=instant(raw.window_end_utc);
 if(!Number.isFinite(start)||!Number.isFinite(end)||end-start!==WINDOW_MS[expectedWindow])
  return bad;
 const gaps=[];
 let lastGapEnd=-Infinity,leading=0,trailing=0;
 for(const g of raw.gaps){
  if(!object(g)||g.kind!=='TELEMETRY_GAP'||g.cause!=='NOT_DETERMINED'||
     !['LEADING','INTERNAL','TRAILING'].includes(g.position))
   return bad;
  const a=instant(g.start_utc),b=instant(g.end_utc);
  if(!Number.isFinite(a)||!Number.isFinite(b)||a<start||b>end||
     b-a<=180000||a<lastGapEnd||!Number.isFinite(g.duration_seconds)||
     Math.abs((b-a)/1000-g.duration_seconds)>0.001)
   return bad;
  if(g.position==='LEADING'&&(a!==start||++leading!==1))return bad;
  if(g.position==='TRAILING'&&(b!==end||++trailing!==1))return bad;
  // An INTERNAL gap may legitimately start at the window boundary when the
  // very first sample sits exactly there; it is not a LEADING gap.
  if(g.position==='INTERNAL'&&trailing!==0)return bad;
  gaps.push({kind:'TELEMETRY_GAP',position:g.position,start_utc:g.start_utc,
   end_utc:g.end_utc,duration_seconds:(b-a)/1000,cause:'NOT_DETERMINED'});
  lastGapEnd=b;
 }
 if((leading&&gaps[0].position!=='LEADING')||
    (trailing&&gaps[gaps.length-1].position!=='TRAILING'))
  return bad;
 const segments=[];
 let lastSegEnd=-Infinity,sum=0;
 for(const s of raw.segments){
  if(!object(s)||s.kind!=='OBSERVED_TELEMETRY_SEGMENT'||
     s.interpretation!=='SAMPLED_TELEMETRY_NOT_DNS_UPTIME'||
     !integer(s.sample_count,1,raw.sample_count))
   return bad;
  const a=instant(s.start_utc),b=instant(s.end_utc);
  if(!Number.isFinite(a)||!Number.isFinite(b)||a<start||b>end||
     a>b||a<=lastSegEnd)return bad;
  if(gaps.some(g=>Date.parse(g.start_utc)<b&&a<Date.parse(g.end_utc)))
   return bad;
  sum+=s.sample_count;
  if(sum>raw.sample_count)return bad;
  segments.push({kind:'OBSERVED_TELEMETRY_SEGMENT',
   start_utc:s.start_utc,end_utc:s.end_utc,sample_count:s.sample_count,
   interpretation:'SAMPLED_TELEMETRY_NOT_DNS_UPTIME'});
  lastSegEnd=b;
 }
 if(sum!==raw.sample_count-raw.invalid_sample_count)return bad;
 // With zero invalid rows B1 emits all sampled runs, and every long
 // between-sample gap exactly separates two runs. Enforce that relationship
 // so a forged/missing gap cannot imply continuous telemetry. With invalid
 // samples, B1 intentionally omits invalid rows from runs: exact alignment
 // cannot be reconstructed from sanitized evidence alone.
 if(raw.invalid_sample_count===0){
  const internal=gaps.filter(g=>g.position==='INTERNAL');
  if(segments.length!==internal.length+1)return bad;
  const first=Date.parse(segments[0].start_utc);
  const last=Date.parse(segments[segments.length-1].end_utc);
  const leadingGap=gaps.find(g=>g.position==='LEADING');
  const trailingGap=gaps.find(g=>g.position==='TRAILING');
  if(leadingGap?Date.parse(leadingGap.end_utc)!==first:
     first-start>180000)return bad;
  if(trailingGap?Date.parse(trailingGap.start_utc)!==last:
     end-last>180000)return bad;
  for(let i=0;i<internal.length;i++){
   if(Date.parse(internal[i].start_utc)!==Date.parse(segments[i].end_utc)||
      Date.parse(internal[i].end_utc)!==Date.parse(segments[i+1].start_utc))
    return bad;
  }
  for(const seg of segments){
   const span=Date.parse(seg.end_utc)-Date.parse(seg.start_utc);
   if(span<seg.sample_count-1||span>(seg.sample_count-1)*180000)
    return bad;
  }
 }
 const uncertain=gaps.length>0||raw.invalid_sample_count>0;
 if(raw.status!==(uncertain?'COVERAGE_OBSERVED_WITH_UNCERTAINTY':'COVERAGE_OBSERVED'))
  return bad;
 return {status:raw.status,window:expectedWindow,
  window_start_utc:raw.window_start_utc,window_end_utc:raw.window_end_utc,
  sample_count:raw.sample_count,
  invalid_sample_count:raw.invalid_sample_count,
  max_cross_series_skew_ms:raw.max_cross_series_skew_ms,
  gaps,segments,
  message:'Wyłącznie zaobserwowana telemetria; brak dowodu ciągłości DNS i przyczyn luk.'};
}

/** UTC evidence -> Warsaw wall time with visible GMT offset, including DST. */
export function formatWarsawUtc(utc){
 const ms=instant(utc);
 if(!Number.isFinite(ms))return 'NIEZWERYFIKOWANY CZAS';
 return new Intl.DateTimeFormat('pl-PL',{
  timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit',
  hour:'2-digit',minute:'2-digit',second:'2-digit',
  hourCycle:'h23',timeZoneName:'shortOffset'
 }).format(new Date(ms));
}
