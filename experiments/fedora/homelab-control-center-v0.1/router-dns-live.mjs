// V0.4 optional manual-local Blackbox router-DNS tile, no automatic polling.
import {normalizeRouterDns} from './router-dns-model.mjs';
const root=document.getElementById('live-router-dns');
if(!root)throw Error('V0.4 router-DNS root missing');
const el=(tag,cls,text='')=>{const n=document.createElement(tag);if(cls)n.className=cls;n.textContent=text;return n;};
const header=el('div','live-head');
const title=el('div');
title.append(el('h2','','DNS przez router · Blackbox'),el('div','live-source',
 'ODCZYT LOKALNY · Jeden test UDP A / example.com · NIE oznacza zdrowia Pi-hole/Unbound'));
const controls=el('div','live-actions');
const flag=el('span','status unknown','UNKNOWN');
const button=el('button','','Odśwież test DNS');button.type='button';
controls.append(flag,button);header.append(title,controls);
const summary=el('div','live-numbers');
const value=el('div','live-count','—');
const hint=el('div','live-meta','Brak zweryfikowanego testu DNS');
summary.append(value,hint);
const source=el('div','live-meta','Źródło: VictoriaMetrics / Blackbox internet_dns · brak automatycznych zapytań');
root.replaceChildren(header,summary,source);
let pending=false,latest=null,timer=null;
function draw(input){
 const d=normalizeRouterDns(input,new Date());
 flag.textContent=d.status;flag.className='status '+d.status.toLowerCase();
 value.textContent=d.status==='OK'?'SUKCES':d.status==='DEGRADED'?'BŁĄD':'—';
 hint.textContent=d.status==='OK'?'Jedno zapytanie Blackbox zakończone sukcesem': 
   d.status==='DEGRADED'?'Jedno zapytanie Blackbox nie powiodło się; to nie dowodzi awarii routera':
   d.status==='STALE'?'Przeterminowana próbka; wcześniejszy wynik jest ukryty':
   'Brak wiarygodnej pojedynczej próbki';
 source.textContent='Źródło: VictoriaMetrics / Blackbox internet_dns'+
  ' · Odczyt: '+(d.observed_at??'brak')+
  ' · Wiek próbki: '+(d.sample_age_seconds===null?'brak':d.sample_age_seconds.toFixed(1)+' s')+
  ' · TTL: '+(d.ttl_seconds===null?'brak':d.ttl_seconds+' s')+
  ' · '+d.reason_code+' · Jeden test UDP A / example.com';
}
function stopTimer(){if(timer!==null)clearTimeout(timer);timer=null;}
async function refresh(){
 if(pending)return;
 pending=true;button.disabled=true;button.textContent='Odczyt…';
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),10000);
 try{
   const response=await fetch('/api/router-dns',{method:'GET',cache:'no-store',
      credentials:'omit',redirect:'error',signal:controller.signal});
   if(!response.ok)throw Error('source unavailable');
   if(Number(response.headers.get('Content-Length')||0)>2048)throw Error('oversize');
   const body=await response.text();if(body.length>2048)throw Error('oversize');
   latest=JSON.parse(body);draw(latest);stopTimer();
   const d=normalizeRouterDns(latest,new Date());
   if(['OK','DEGRADED'].includes(d.status)){
     const remaining=Date.parse(d.observed_at)+(120-latest.sample_age_seconds)*1000-Date.now()+80;
     timer=setTimeout(()=>draw(latest),Math.max(10,Math.min(remaining,125000)));
   }
 }catch(_){latest=null;stopTimer();draw(null);}
 finally{clearTimeout(timeout);pending=false;button.disabled=false;button.textContent='Odśwież test DNS';}
}
button.addEventListener('click',refresh);
document.addEventListener('visibilitychange',()=>{if(latest)draw(latest);});
refresh();
