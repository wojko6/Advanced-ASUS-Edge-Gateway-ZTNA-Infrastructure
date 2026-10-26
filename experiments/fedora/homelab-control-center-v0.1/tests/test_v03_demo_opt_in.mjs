import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const root=resolve(import.meta.dirname,'..');
class FakeElement {
 constructor(tag='div'){
  this.tagName=tag;this.children=[];this.className='';this._text='';
  this.dataset={};this.attrs={};this.listeners={};this.hidden=false;
  this.classList={toggle:(name,enabled)=>{
   const tokens=new Set(this.className.split(/\s+/).filter(Boolean));
   if(enabled)tokens.add(name);else tokens.delete(name);
   this.className=[...tokens].join(' ');
  }};
 }
 set textContent(value){this._text=String(value);this.children=[];}
 get textContent(){return this._text+this.children.map(x=>x.textContent||'').join('');}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this._text='';this.children=[...items];}
 setAttribute(key,value){this.attrs[key]=String(value);}
 removeAttribute(key){delete this.attrs[key];}
 addEventListener(name,fn){this.listeners[name]=fn;}
 click(){this.listeners.click?.();}
}
function fixtureDoc(gate){
 const keys=['scenario','view','page-title','page-subtitle','breadcrumb','snapshot-info'];
 if(gate)keys.push('demo-toggle','demo-controls');
 const ids=Object.fromEntries(keys.map(k=>[k,new FakeElement()]));
 const nav=['overview','services','incidents','recovery'].map(page=>{
  const e=new FakeElement('button');e.dataset.page=page;return e;
 });
 return {body:{dataset:gate?{demoGate:'opt-in'}:{}},ids,nav,
  getElementById:id=>ids[id]??null,
  createElement:tag=>new FakeElement(tag),
  querySelectorAll:selector=>selector==='[data-page]'?nav:[]
 };
}
function all(root,match){
 const acc=[];const walk=e=>{if(match(e))acc.push(e);for(const c of e.children)walk(c);};
 walk(root);return acc;
}

test('V0.3 hides synthetic counters and services until explicit opt-in and hides again',async()=>{
 const doc=fixtureDoc(true);globalThis.document=doc;
 try{
  await import('../app.mjs?fixture-v03-opt-in');
  assert.equal(doc.ids['demo-controls'].hidden,true);
  assert.equal(doc.ids['demo-toggle'].attrs['aria-expanded'],'false');
  assert.equal(doc.ids['snapshot-info'].textContent,'DEMO ukryte');
  assert.equal(all(doc.ids.view,e=>e.className==='stat-card').length,0);
  assert.equal(all(doc.ids.view,e=>e.className==='service-card').length,0);
  assert.match(doc.ids.view.textContent,/Fikcyjne liczniki/);

  doc.ids['demo-toggle'].click();
  assert.equal(doc.ids['demo-controls'].hidden,false);
  assert.equal(doc.ids['demo-toggle'].attrs['aria-expanded'],'true');
  assert.equal(all(doc.ids.view,e=>e.className==='stat-card').length,4);
  assert.equal(all(doc.ids.view,e=>e.className==='service-card').length,6);
  const statuses=all(doc.ids.view,e=>e.className.includes('demo-status'));
  assert.equal(statuses.length,6);
  assert.ok(statuses.every(e=>e.textContent.endsWith(' · DEMO')));
  assert.ok(all(doc.ids.view,e=>e.className==='metric-label').every(e=>e.textContent.includes('DEMO')));

  doc.nav.find(e=>e.dataset.page==='services').onclick();
  assert.ok(all(doc.ids.view,e=>e.className==='service-card').every(card=>
   all(card,e=>e.className.includes('demo-status')).length===1));
  doc.ids['demo-toggle'].click();
  assert.equal(doc.ids['demo-controls'].hidden,true);
  assert.equal(all(doc.ids.view,e=>e.className==='service-card').length,0);
  assert.equal(doc.ids['snapshot-info'].textContent,'DEMO ukryte');
 }finally{delete globalThis.document;}
});

test('V0.1 and V0.2 shared renderer keep their existing demo behaviour',async()=>{
 const doc=fixtureDoc(false);globalThis.document=doc;
 try{
  await import('../app.mjs?fixture-legacy-render');
  assert.equal(all(doc.ids.view,e=>e.className==='stat-card').length,4);
  const statuses=all(doc.ids.view,e=>e.className.startsWith('status '));
  assert.equal(statuses.length,6);
  assert.ok(statuses.every(e=>!e.textContent.includes(' · DEMO')));
  assert.match(doc.ids['snapshot-info'].textContent,/Migawka przykładowa/);
 }finally{delete globalThis.document;}
});

test('V0.3 page opt-in is explicit, accessible, isolated from live source styles',()=>{
 const html=readFileSync(resolve(root,'index-v03.html'),'utf8');
 const v02=readFileSync(resolve(root,'index-live.html'),'utf8');
 const app=readFileSync(resolve(root,'app.mjs'),'utf8');
 const css=readFileSync(resolve(root,'styles.css'),'utf8');
 assert.match(html,/data-demo-gate="opt-in"/);
 assert.match(html,/id="demo-toggle"[^>]*aria-controls="view"[^>]*aria-expanded="false"/);
 assert.match(html,/id="demo-controls" hidden/);
 assert.match(html,/id="live-vm"/);
 assert.match(html,/id="live-dns-guard"/);
 assert.doesNotMatch(v02,/data-demo-gate="opt-in"/);
 assert.match(app,/if\(v03DemoGate&&!state\.showDemo\)/);
 assert.match(css,/\.hcc-v03 #view \.service-card \.status\.demo-status/);
 assert.match(css,/\.hcc-v03 #view \.stat-card \.metric/);
 assert.match(css,/\.hcc-v03 #view \.event-marker/);
 assert.doesNotMatch(css,/\.hcc-v03 \.live-panel \.status/);
});
