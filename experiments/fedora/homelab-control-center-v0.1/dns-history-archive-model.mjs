// V0.5 fixed historical archive; never a rolling LIVE DNS incident stream.
const FIXED_SOURCE='FEDORA_VM_SEVEN_FIXED_DNS_GUARD_RAW_EXPORTS';
const START='2026-10-27T14:40:00Z',END='2026-10-27T16:43:00Z';
const TYPES=new Map([
 ['LOCAL_TO_BOOTSTRAP',['LOCAL','BOOTSTRAP']],
 ['BOOTSTRAP_TO_LOCAL',['BOOTSTRAP','LOCAL']],
]);
const iso=s=>typeof s==='string'&&/^2026-10-27T\d\d:\d\d:\d\d\.\d{3}\+01:00$/.test(s)
 ? new Date(s).getTime() : Number.NaN;
export function normalizeHistory(raw){
 const none={status:'UNKNOWN',sample_count:null,events:[],
  message:'Nie udało się zweryfikować stałego archiwum.'};
 if(!raw||typeof raw!=='object'||Array.isArray(raw)||
    raw.schema_version!=='0.5'||raw.kind!=='dns-guard-history-archive'||
    raw.mode!=='manual-fixed-archive-readonly'||
    raw.source!==FIXED_SOURCE||raw.archive_start!==START||raw.archive_end!==END)
  return none;
 if(raw.status==='UNKNOWN'&&raw.reason_code==='ARCHIVE_EVIDENCE_NOT_VERIFIED'&&
    raw.event_count===0&&Array.isArray(raw.events)&&raw.events.length===0)
  return none;
 if(raw.status!=='ARCHIVE_VERIFIED'||raw.reason_code!=='SAMPLED_TRANSITIONS_CORROBORATED'||
    !Number.isInteger(raw.sample_count)||raw.sample_count<2||raw.sample_count>200||
    !Number.isInteger(raw.event_count)||raw.event_count<0||raw.event_count>8||
    !Array.isArray(raw.events)||raw.events.length!==raw.event_count)
  return none;
 const clean=[];
 let prevEnd=-Infinity;
 for(const e of raw.events){
  if(!e||typeof e!=='object'||Array.isArray(e)||!TYPES.has(e.type)||
     e.from!==TYPES.get(e.type)[0]||e.to!==TYPES.get(e.type)[1]||
     e.confidence!=='BOUNDED_OBSERVATION')return none;
  const start=iso(e.window_start_local),end=iso(e.window_end_local);
  if(!Number.isFinite(start)||!Number.isFinite(end)||start>=end||start<prevEnd)return none;
  const gap=(end-start)/1000;
  if(gap>180||typeof e.gap_seconds!=='number'||!Number.isFinite(e.gap_seconds)||
    Math.abs(gap-e.gap_seconds)>0.005)return none;
  let reported=null;
  if(e.reported_at_local!==null){
   const at=iso(e.reported_at_local);
   if(!Number.isFinite(at)||at<start||at>end)return none;
   reported=e.reported_at_local;
  }
  clean.push({type:e.type,from:e.from,to:e.to,window_start_local:e.window_start_local,
   window_end_local:e.window_end_local,reported_at_local:reported,gap_seconds:gap});
  prevEnd=end;
 }
 return {status:'ARCHIVE_VERIFIED',sample_count:raw.sample_count,events:clean,
  message:'Archiwum z 27.10.2026. Okna obserwacji, nie dokładne chwile zmian.'};
}
