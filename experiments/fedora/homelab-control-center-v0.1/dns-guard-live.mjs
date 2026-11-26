// V0.3 manual local DNS Guard telemetry. Not a DNS query availability probe.
import {normalizeDnsGuard} from './dns-guard-model.mjs';
const root=document.getElementById('live-dns-guard');
if(!root)throw Error('V0.3 root missing');
const el=(tag,cls,text='')=>{const n=document.createElement(tag);if(cls)n.className=cls;n.textContent=text;return n;};
const head=el('div','live-head');
const desc=el('div');
desc.append(el('h2','','DNS Guard · Telemetria trybu'),el('div','live-source','ODCZYT LOKALNY · VictoriaMetrics · nie testuje działania DNS'));
const controls=el('div','live-actions');
const flag=el('span','status unknown','UNKNOWN');
const button=el('button','','Odśwież DNS Guard');button.type='button';
controls.append(flag,button);head.append(desc,controls);
const summary=el('div','live-numbers');
const mode=el('div','live-count','—');
const hint=el('div','live-meta','Brak zweryfikowanego pomiaru');
summary.append(mode,hint);
const details=el('div','live-meta','Watchdog: — · Break-glass: —');
const source=el('div','live-meta','Źródło: DNS Guard telemetry via local VictoriaMetrics /api/dns-guard · brak automatycznych zapytań');
root.replaceChildren(head,summary,details,source);
let pending=false,latest=null,timer=null;
const yn=v=>v===null?'brak danych':v?'TAK':'NIE';
function draw(input){
 const data=normalizeDnsGuard(input,new Date());
 flag.textContent=data.status;flag.className='status '+data.status.toLowerCase();
 mode.textContent=data.dns_mode==='UNVERIFIED'?'—':data.dns_mode;
 hint.textContent=data.status==='OK'?'Zgłoszony tryb lokalny (nie potwierdza poprawności zapytań DNS)':
   data.status==='DEGRADED'?'Telemetria wskazuje zmianę trybu lub ograniczenie ochrony':
   data.status==='STALE'?'Pomiar eksportera jest nieaktualny — brak potwierdzenia':'Brak zweryfikowanego odczytu';
 details.textContent='Watchdog: '+yn(data.watchdog_present)+' · Break-glass: '+yn(data.breakglass_active);
 source.textContent='Źródło: VictoriaMetrics / sześć stałych metryk DNS Guard'+
  ' · Odczyt: '+(data.observed_at??'brak')+
  ' · Wiek kolekcji: '+(data.collection_age_seconds===null?'brak':data.collection_age_seconds.toFixed(1)+' s')+
  ' · TTL: '+(data.ttl_seconds===null?'brak':data.ttl_seconds+' s')+
  ' · '+data.reason_code;
}
function stopTimer(){if(timer!==null)clearTimeout(timer);timer=null;}
async function refresh(){
 if(pending)return;
 pending=true;button.disabled=true;button.textContent='Odczyt…';
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),10000);
 try{
   const response=await fetch('/api/dns-guard',{method:'GET',cache:'no-store',credentials:'omit',redirect:'error',signal:controller.signal});
   if(!response.ok)throw Error('source unavailable');
   if(Number(response.headers.get('Content-Length')||0)>2048)throw Error('oversize');
   const payload=await response.text();if(payload.length>2048)throw Error('oversize');
   latest=JSON.parse(payload);draw(latest);stopTimer();
   const valid=normalizeDnsGuard(latest,new Date());
   if(['OK','DEGRADED'].includes(valid.status)){
      const at=Date.parse(valid.observed_at);
      const age=valid.collection_age_seconds;
      const remaining=at+((valid.ttl_seconds-age)*1000)-Date.now()+80;
      timer=setTimeout(()=>draw(latest),Math.max(10,Math.min(remaining,185000)));
   }
 }catch(_){latest=null;stopTimer();draw(null);}
 finally{clearTimeout(timeout);pending=false;button.disabled=false;button.textContent='Odśwież DNS Guard';}
}
button.addEventListener('click',refresh);
document.addEventListener('visibilitychange',()=>{if(latest)draw(latest);}); // redraw only, never query
refresh();
