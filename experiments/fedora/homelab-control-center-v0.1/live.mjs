// Manual, same-origin read-only V0.2 aggregate tile. Demo scenario cards remain independent.
import {normalizeLive} from './live-model.mjs';
const root=document.getElementById('live-vm');
const fixtureMode=root.dataset.fixtureMode==='true';
const el=(tag,css,text='')=>{const n=document.createElement(tag);if(css)n.className=css;n.textContent=text;return n;};
const cap=(value)=>value===null?'—':String(value);
const button=el('button','','Odśwież pomiar');button.type='button';
const header=el('div','live-head');const about=el('div');about.append(el('h2','','VictoriaMetrics · Cele scrape'),el('div','live-source',fixtureMode?'SYMULACJA BEZ DANYCH RZECZYWISTYCH · 127.0.0.1:8789':'ODCZYT LOKALNY · zagregowane up, bez etykiet'));
const actions=el('div','live-actions');const indicator=el('span','status unknown','UNKNOWN');actions.append(indicator,button);header.append(about,actions);
const nums=el('div','live-numbers');const big=el('div','live-count','— / —');const label=el('div','live-meta','Brak zweryfikowanego pomiaru');nums.append(big,label);
const track=el('div','live-track');const fill=el('div','live-fill unknown');fill.style.width='0%';track.append(fill);
const metadata=el('div','live-meta',fixtureMode?'Źródło: SYNTHETIC FIXTURE · żadnych zapytań VictoriaMetrics':'Źródło: VictoriaMetrics · API /api/summary · bez automatycznego odświeżania');
root.replaceChildren(header,nums,track,metadata);
let pending=false;
let lastData=null;
let expiryTimer=null;
function draw(data){
 const v=normalizeLive(data,new Date());
 indicator.textContent=v.status;indicator.className='status '+v.status.toLowerCase();
 big.textContent=v.healthy===null?'— / —':cap(v.healthy)+' / '+cap(v.total);
 label.textContent=v.status==='OK'?'Wszystkie cele scrape UP (nie dowodzi zdrowia aplikacji)':
   v.status==='DEGRADED'?'Część celów scrape nie odpowiada':
   v.status==='DOWN'?'Żaden cel scrape nie odpowiada':
   v.status==='STALE'?'Próbki są zbyt stare — brak bieżącego potwierdzenia':'Brak wiarygodnego pomiaru';
 const ratio=v.total && v.healthy!==null?100*v.healthy/v.total:0;
 fill.style.width=String(Math.max(0,Math.min(100,ratio)))+'%';fill.className='live-fill '+v.status.toLowerCase();
 metadata.textContent=(fixtureMode?'Źródło: DANE TESTOWE / bez połączeń z VictoriaMetrics':'Źródło: VictoriaMetrics / fixed count(up), sum(up), age')+' · Odczyt: '+(v.observed_at??'brak')+
  ' · Najstarsza próbka: '+(v.oldest_sample_age_seconds===null?'brak':String(v.oldest_sample_age_seconds)+' s')+
  ' · TTL: '+(v.ttl_seconds??'nieznany')+' s · '+v.reason_code;
}
async function refresh(){
 if(pending)return;pending=true;button.disabled=true;button.textContent='Odczyt…';
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),8500); // bound a hung same-origin request
 try{
   const response=await fetch('/api/summary',{method:'GET',cache:'no-store',credentials:'omit',redirect:'error',signal:controller.signal});
   if(!response.ok)throw Error('no summary');
   const contentLength=Number(response.headers.get('Content-Length')||0);
   if(contentLength>2048)throw Error('oversized response');
   const raw=await response.text();if(raw.length>2048)throw Error('oversized response');
   lastData=JSON.parse(raw);
   draw(lastData);
   if(expiryTimer!==null)clearTimeout(expiryTimer);
   const t=Date.parse(lastData?.observed_at||'');
   const ttl=lastData?.ttl_seconds;
   if(Number.isFinite(t)&&Number.isSafeInteger(ttl)&&ttl>0&&ttl<=600){
     const delay=Math.max(10,Math.min(615000,t+(ttl+15)*1000-Date.now()+50));
     expiryTimer=setTimeout(()=>draw(lastData),delay); // visual expiry, no network request
   }
 }catch(_){lastData=null;if(expiryTimer!==null)clearTimeout(expiryTimer);draw(null);}
 finally{clearTimeout(timeout);pending=false;button.disabled=false;button.textContent='Odśwież pomiar';}
}
button.addEventListener('click',refresh);
document.addEventListener('visibilitychange',()=>{if(lastData)draw(lastData);}); // never query on wake
refresh();
