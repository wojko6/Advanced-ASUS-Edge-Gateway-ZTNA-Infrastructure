// All example observations are fictional and deliberately fixed in time.
const clock='2026-10-25T14:00:00Z';
const names=[
  ['fedora','Fedora 44','System','systemd / fixture','▤'],
  ['asus','ASUS Edge Gateway','Sieć','router / fixture','⌘'],
  ['dns','DNS Guard / Pi-hole','DNS','blackbox / fixture','◈'],
  ['tailscale','Tailscale','VPN','tailnet / fixture','◇'],
  ['monitoring','Grafana / Loki / Alloy','Monitoring','telemetria / fixture','▥'],
  ['recovery','Fedora Recovery','Backup','restic / fixture','▣']
];
const defaultReasons={fedora:'Usługi hosta odpowiadają (symulacja).',asus:'Router dostępny w syntetycznym teście.',dns:'Wynik DNS zgodny z oczekiwaniami (fikcyjny).',tailscale:'Testowa łączność tunelu.',monitoring:'Próbki i logi świeże w scenariuszu.',recovery:'Test kontrolny archiwum zakończony pomyślnie.'};
function base(){return names.map(([id,name,category,source,icon])=>({id,name,category,source,icon,observedAt:'2026-10-25T13:59:45Z',sourceAvailable:true,ttlSeconds:90,measuredStatus:'OK',reason:defaultReasons[id]}));}
function make(id,label,desc,changes={}){
 const signals=base();
 for(const [signalId,props] of Object.entries(changes)){const row=signals.find(s=>s.id===signalId);if(!row)throw Error('Invalid demo scenario');Object.assign(row,props);}
 return Object.freeze({id,label,description:desc,schemaVersion:'1.0',mode:'demo',generatedAt:clock,signals,events:[
  {at:'13:57',severity:'healthy',title:'Testowa synchronizacja monitoringu',note:'Wygenerowane zdarzenie lokalne; nie pochodzi z Loki.'},
  {at:'13:42',severity:'warning',title:'Przykładowy przegląd statusu DNS',note:'Oś czasu demonstracyjna — Black Box #304 będzie osobnym modułem.'},
  {at:'13:20',severity:'healthy',title:'Testowy odczyt kopii zapasowej',note:'Brak rzeczywistego sprawdzenia archiwum lub procesu Restic.'}
 ],recovery:[
   {key:'Ostatnia udana kopia',value:'Przykład: 25.10, 09:00',hint:'Demo — znacznik syntetyczny, nie odczyt Restic.'},
   {key:'Kontrola integralności',value:'Przykład: PASS',hint:'Dane przykładowe. PASS nie oznacza odtwarzalności.'},
   {key:'Izolowany restore root',value:'Przykład: PASS',hint:'Kategoria osobna od pełnego przywrócenia systemu.'},
   {key:'Boot odtworzonej Fedory',value:'UNKNOWN / NOT TESTED',hint:'Nie należy oznaczać systemu jako w pełni odzyskiwalnego.'}
 ]});
}
export const SCENARIOS=Object.freeze([
 make('healthy','Wszystkie sygnały OK','Syntetyczny stan poprawny.'),
 make('dns-degraded','DNS zdegradowany','Symulacja problemu DNS przy sprawnej łączności IP.',{dns:{measuredStatus:'DEGRADED',reason:'Syntetyczny błąd rozwiązywania nazw; dostęp IP zachowany.'}}),
 make('stale','Przestarzała telemetria','Monitoring ma pozytywny, ale zbyt stary pomiar.',{monitoring:{observedAt:'2026-10-25T13:54:00Z'}}),
 make('router-offline','Planowo wyłączony ASUS','OFFLINE tylko przy jawnym oznaczeniu planowanego wyłączenia.',{asus:{explicitPlannedOffline:true,reason:'Planowane wyłączenie potwierdzone tylko w fikcyjnym scenariuszu.'},dns:{sourceAvailable:false,observedAt:null}}),
 make('source-down','Brak źródła danych','Brak odczytu = UNKNOWN, a nie DOWN.',{monitoring:{sourceAvailable:false,observedAt:null}}),
 make('conflict','Sprzeczne pomiary','Rozbieżne sygnały nie pozwalają na zielony status.',{dns:{conflicting:true,reason:'Syntetycznie sprzeczne źródła.'}})
]);
