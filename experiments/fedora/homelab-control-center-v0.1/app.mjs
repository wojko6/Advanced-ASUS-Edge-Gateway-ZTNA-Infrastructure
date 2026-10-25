import {SCENARIOS} from './data.mjs';
import {project,summary} from './model.mjs';

const $ = (id)=>document.getElementById(id);
const state={page:'overview',scenario:SCENARIOS[0],filter:'ALL'};
const labels={overview:['Centrum dowodzenia','Jeden widok. Jasny status. Żadnych zgadywanek.','PRZEGLĄD'],services:['Katalog usług','Komponenty i ich źródła obserwacji.','USŁUGI'],incidents:['Historia zdarzeń','Incydenty demonstracyjne; analiza Black Box należy do Issue #304.','INCYDENTY'],recovery:['Recovery Center','Kopie, integralność i testy odtworzenia to oddzielne dowody.','RECOVERY']};
const cls=(x)=>String(x).toLowerCase();
function node(tag,classes='',text='') {const e=document.createElement(tag);if(classes)e.className=classes;if(text!==null)e.textContent=String(text);return e;}
function add(parent,...children){for(const c of children)parent.append(c);return parent;}
function header(title,right=''){const el=node('div','section-header');add(el,node('h2','',title),node('div','small-note',right));return el;}
function badge(status){return node('span',`status ${cls(status)}`,status);}
function statusCard(s){
 const el=node('article','service-card');const head=node('div','service-head');const nw=node('div','name-wrap');
 add(nw,node('div','service-icon',s.icon||'•'),node('span','service-name',s.name)); add(head,nw,badge(s.status));
 const reason=node('div','service-reason',s.reason);const foot=node('div','service-bottom');
 const age=s.ageSeconds===null?'brak aktualnej próbki':`${s.ageSeconds} s od obserwacji`;
 add(foot,node('span','',s.source),node('span','',age));return add(el,head,reason,foot);
}
function events(scene){const e=node('div');for(const entry of scene.events){const row=node('div','event');const marker=node('span',`event-marker ${entry.severity}`);marker.setAttribute('aria-hidden','true');const desc=node('div','event-text');add(desc,node('div','event-title',entry.title),node('div','event-desc',entry.note));add(row,marker,desc,node('span','event-time',entry.at));e.append(row);}return e;}
function statCard(label,value,sub,color){const el=node('div','stat-card');add(el,node('div','metric-label',label),node('div',`metric ${color}`,value),node('div','metric-sub',sub));return el;}
function overview(rows){
 const c=summary(rows);const view=node('div');const stats=node('section','stat-grid');
 add(stats,statCard('Stan prawidłowy',String(c.OK),'Sygnały w normie (demo)','green'),statCard('Wymaga uwagi',String(c.DEGRADED+c.DOWN),'Degradacja lub awaria','amber'),statCard('Brak pewności',String(c.STALE+c.UNKNOWN),'Nieaktualne lub nieznane','blue'),statCard('Planowo offline',String(c.OFFLINE),'Tylko jawna deklaracja','white'));
 add(view,stats,header('Usługi infrastruktury','STATUSY WYŁĄCZNIE Z DANYCH TESTOWYCH'));
 const cards=node('div','cards-grid');for(const s of rows)cards.append(statusCard(s));view.append(cards);
 const panels=node('div','lower-grid'),timeline=node('section','panel'),facts=node('section','panel');
 add(timeline,node('h2','','Ostatnie zdarzenia · DEMO'),events(state.scenario));
 const hybrid = Boolean(document.getElementById('live-vm'));
 add(facts,node('h2','','Jakość danych'),node('p','fineprint','Każdy stan ma nazwę źródła, znacznik czasu i uzasadnienie. Wartości STALE i UNKNOWN nie są traktowane jak sukces.'),node('div','callout',hybrid?'Górny kafelek pobiera wyłącznie zbiorcze metryki z lokalnego API VictoriaMetrics (127.0.0.1). Karty usług, zdarzenia i Recovery pozostają DEMO. Nie ma połączeń z ASUS-em ani wykonywania poleceń administracyjnych.':'To makieta działającego interfejsu. Nie ma odpytywania serwerów, routera, Tailscale ani usług DNS. Realne adaptery wymagają osobnej zgody.'));
 add(panels,timeline,facts);view.append(panels);return view;
}
function services(rows){const view=node('div');const chips=node('div','chipbar');
 const filters=[['ALL','Wszystkie'],['PROBLEM','Wymagające uwagi'],['OK','Prawidłowe'],['UNKNOWN','Niepewne / offline']];
 for(const [id,label] of filters){const btn=node('button','chip',label);btn.type='button';btn.setAttribute('aria-pressed',String(state.filter===id));btn.onclick=()=>{state.filter=id;render();};chips.append(btn);}view.append(chips);
 const filtered=rows.filter(x=>state.filter==='ALL'||state.filter==='OK'&&x.status==='OK'||state.filter==='PROBLEM'&&['DOWN','DEGRADED'].includes(x.status)||state.filter==='UNKNOWN'&&['STALE','UNKNOWN','OFFLINE'].includes(x.status));
 const grid=node('div','cards-grid');for(const x of filtered)grid.append(statusCard(x));
 if(!filtered.length)grid.append(node('div','empty','Brak komponentów spełniających ten filtr w wybranym scenariuszu.'));
 view.append(grid);return view;
}
function incidents(){const v=node('div','lower-grid');const left=node('section','panel'),right=node('section','panel');
 add(left,node('h2','','Przykładowa oś czasu'),events(state.scenario));
 add(right,node('h2','','Black Box — następny moduł'),node('p','fineprint','Issue #304 przewiduje odtwarzanie awarii z dowodami i oznaczaniem niepewności. Dzisiejszy ekran wyświetla wyłącznie fikcyjne zdarzenia z modułu danych demonstracyjnych.'),node('div','callout','Nie wyznaczamy automatycznie przyczyny źródłowej. Korelacja w czasie nie oznacza związku przyczynowego.'));
 return add(v,left,right);
}
function recovery(){const root=node('div'),panel=node('section','panel');panel.append(header('Granice dowodów odtwarzania','DANE PRZYKŁADOWE'));
 const grid=node('div','recovery-list');for(const r of state.scenario.recovery){const item=node('article','recovery-item');add(item,node('div','key',r.key),node('div','value',r.value),node('div','hint',r.hint));grid.append(item);}panel.append(grid,node('div','callout','Ukończone sprawdzenie Restic lub odtworzenie Btrfs root nie dowodzi możliwości uruchomienia kompletnego systemu. Ten prototyp nie ma dostępu do archiwów.'));return add(root,panel);
}
function render(){
 const [title,sub,crumb]=labels[state.page];$('page-title').textContent=title;$('page-subtitle').textContent=sub;$('breadcrumb').textContent=crumb;
 $('snapshot-info').textContent='Migawka przykładowa: '+state.scenario.generatedAt.replace('T',' ').replace('Z',' UTC');
 for(const b of document.querySelectorAll('[data-page]')){const selected=b.dataset.page===state.page;b.classList.toggle('active',selected);if(selected)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
 const rows=project(state.scenario);const v=$('view');v.replaceChildren(state.page==='overview'?overview(rows):state.page==='services'?services(rows):state.page==='incidents'?incidents():recovery());
}
for(const scene of SCENARIOS){const o=node('option','',scene.label);o.value=scene.id;$('scenario').append(o);}
$('scenario').onchange=(e)=>{const found=SCENARIOS.find(x=>x.id===e.target.value);if(found){state.scenario=found;state.filter='ALL';render();}};
for(const b of document.querySelectorAll('[data-page]'))b.onclick=()=>{state.page=b.dataset.page;state.filter='ALL';render();};
render();
