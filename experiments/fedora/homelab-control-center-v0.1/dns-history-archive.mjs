// Separate archive view for one verified date, never called automatically.
import {normalizeHistory} from './dns-history-archive-model.mjs';
const root=document.getElementById('dns-history-archive');
if(!root)throw Error('V0.5 archive root missing');
const el=(tag,cls,text='')=>{const e=document.createElement(tag);if(cls)e.className=cls;e.textContent=text;return e;};
const top=el('div','live-head');
const heading=el('div');
heading.append(el('div','history-kicker','ARCHIWUM 27.10.2026 · NIE LIVE'),
 el('h2','','Ostatnie zaobserwowane przełączenia DNS Guard'),
 el('div','history-description','Historyczna migawka z siedmiu metryk. Każde zdarzenie ma przedział obserwacji, nie gwarantowaną chwilę przełączenia.'));
const controls=el('div','live-actions');
const badge=el('span','status offline','ARCHIWUM');
const button=el('button','','Odczytaj archiwum');button.type='button';
controls.append(badge,button);top.append(heading,controls);
const count=el('div','history-count','Dane nie zostały jeszcze odczytane');
const list=el('ol','history-list');
const footer=el('div','history-footer','Źródło: lokalne VictoriaMetrics · 27.10.2026 · Odczyt wyłącznie na żądanie · Bez powiadomień i automatycznego odświeżania.');
root.replaceChildren(top,count,list,footer);
let pending=false;
function clearEvents(){list.replaceChildren();}
function render(raw){
 const data=normalizeHistory(raw);
 clearEvents();
 if(data.status!=='ARCHIVE_VERIFIED'){
  badge.className='status unknown';badge.textContent='UNKNOWN';
  count.textContent='Archiwum niedostępne lub niespójne. Nie pokazujemy poprzedniego wyniku.';
  return;
 }
 badge.className='status offline';badge.textContent='ZWERYFIKOWANE ARCHIWUM';
 count.textContent='Zaobserwowane zmiany: '+data.events.length+' · Próbki na serię: '+data.sample_count;
 for(const entry of data.events){
  const item=el('li');
  const direction=entry.type==='LOCAL_TO_BOOTSTRAP'?'LOCAL → BOOTSTRAP':'BOOTSTRAP → LOCAL';
  item.append(el('strong','',direction),
    el('span','','Przedział obserwacji: '+entry.window_start_local+' — '+entry.window_end_local),
    el('span','','Czas zgłoszony przez DNS Guard: '+(entry.reported_at_local??'brak potwierdzonego znacznika')),
    el('span','','Odstęp próbek: '+entry.gap_seconds.toFixed(3)+' s · Wiarygodność: przedział obserwacji'));
  list.append(item);
 }
 footer.textContent='Stałe archiwum 27.10.2026 · Nie obejmuje kolejnych dni ani ukrytych krótkich przełączeń. Nie dowodzi ciągłej dostępności DNS. Bez automatycznego odświeżania i wysyłania powiadomień.';
}
async function readArchive(){
 if(pending)return;
 pending=true;button.disabled=true;button.textContent='Odczyt…';
 const ctrl=new AbortController();
 const timeout=setTimeout(()=>ctrl.abort(),40000);
 try{
  const response=await fetch('/api/dns-guard-history-archive',{
   method:'GET',cache:'no-store',credentials:'omit',redirect:'error',signal:ctrl.signal});
  if(!response.ok)throw Error('source unavailable');
  if(Number(response.headers.get('Content-Length')||0)>8192)throw Error('oversize');
  const text=await response.text();
  if(text.length>8192)throw Error('oversize');
  render(JSON.parse(text));
 }catch(_){render(null);}
 finally{clearTimeout(timeout);pending=false;button.disabled=false;button.textContent='Odczytaj archiwum';}
}
button.addEventListener('click',readArchive);
// No readArchive() on initial page load; no intervals, timers for polling,
// external URLs, session persistence, or notification transport.
