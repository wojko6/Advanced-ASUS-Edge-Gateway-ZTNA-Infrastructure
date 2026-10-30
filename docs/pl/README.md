# Dokumentacja po polsku — ASUS Edge Gateway

**Status:** indeks bieżących instrukcji i dokumentów pomocniczych  
**Aktualizacja:** 2026-10-30 (dodanie izolowanego laboratorium HCC V0.14.5A–B; bez wdrożenia ani walidacji produkcyjnej)

Ten katalog ułatwia znalezienie polskich instrukcji administracyjnych. Nie jest osobną kopią całej dokumentacji projektu. **Techniczny stan infrastruktury i zasady bezpieczeństwa** pozostają opisane w [PROJECT-STATUS.md](../../PROJECT-STATUS.md), [modelu dokumentacji](../documentation-model.md) i [polityce językowej](../language-policy.md).

## Pierwsza wizyta — od czego zacząć?

Laboratorium robocze: [HCC V0.14.5A–E — odtwarzanie, tożsamość i atomowy zapis ID/treści](hcc-v0145-offline-lab.md), Draft #338 / `DEPLOYMENT_GATE=HOLD`. Osobne wyniki operatora na Fedorze: A–B 59/59 i oba laboratoria PASS, C 28/28 i laboratorium PASS. D 31 i E 34 testy Work, bez akceptacji na Fedorze i rzeczywistej integracji. Nie obejmuje to Alloy/SELinux ani wdrożenia.

**Nowy czytelnik?** Otwórz **[Zacznij tutaj — przewodnik na 15–20 minut](START-HERE.md)** ([English](../START-HERE.md)). To bezpieczna ścieżka poznania projektu: od celu i diagramu architektury po aktualny stan, ograniczenia i dobór dalszych materiałów. **Nie wymaga instalacji ani poleceń na routerze.**

Jeżeli szukasz konkretnej procedury operatora, przejdź do poniższych indeksów; status produkcyjny nadal wyznaczają [PROJECT-STATUS.md](../../PROJECT-STATUS.md) i datowane dowody.

## Dostępne instrukcje administracyjne

| Temat | Dokument po polsku | Dokumentacja techniczna EN |
|---|---|---|
| Pierwsze wdrożenie ASUS Edge Gateway | [Wdrożenie routera](../deployment-pl.md) | [Deployment/operations reference](../operations.md) |
| Dodatkowy BusyBox ARMv7 (bez wymiany firmware'u) | [Bezpieczne używanie BusyBox 1.36.1](busybox-armv7.md) | [Custom BusyBox deployment and recovery](../custom-busybox-armv7.md) |
| Drukarka w sieci lokalnej | [Instrukcja LAN](../printer-setup-lan-pl.md) | [Zasady bezpieczeństwa drukarki](../PRINTER-HARDENING.md) |
| Drukarka przez Tailscale | [Instrukcja zdalna](../printer-setup-tailscale-pl.md) | [Firewall policy](../firewall-policy.md) |

**Ważne:** kolumna EN wskazuje dokumenty technicznie powiązane, **nie** gwarantuje przekładu rozdział po rozdziale. Nie należy zakładać, że dwie procedury opisują dokładnie ten sam zakres testów.

## Odtwarzanie routera od zera

- [Procedura awaryjna od pustego ASUS-a i SSD (PL)](../router-bare-metal-recovery-pl.md) — opis odtworzenia etapami, z warunkami PASS/STOP. **To procedura przygotowana, ale nieprzetestowana w pełnym scenariuszu bare-metal**.
- [Kanoniczna dokumentacja Disaster Recovery (EN)](../router-disaster-recovery.md) oraz [sekwencyjny runbook odbudowy Pi-hole (EN)](../pihole-dr-rebuild-runbook.md) — kontrakt techniczny, zależności, ograniczenia i walidacja.

**Uzupełnienie DR 24 października:** aktualne procedury uwzględniają Unbound `1.26.2-1` (5 IPK) i wydzielony katalog RFC 5011 `dnssec-auto`. Pełne odtworzenie pustego SSD/routera nadal **nie jest zaliczone**. Tryb `0666` aktywnego `root.key` z testu po restarcie **nie jest docelową polityką**, a #298/#299 pozostają OPEN/HOLD. [Aktualny kontrakt odtwarzania EN](../router-disaster-recovery.md#unbound-runtime-ownership-reconstruction).

Punkt startowy: [indeks Disaster Recovery](../disaster-recovery-index.md) — wskazuje, **który dokument otworzyć**, które testy przeszły i czego nadal nie udowodniono. Materiały operacyjne scalono w [PR #205](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/205). Polska instrukcja jest **rozszerzoną adaptacją dla operatora**, nie tłumaczeniem zdanie po zdaniu. Testy z 2026-10-09 potwierdziły zarówno **restart istniejącego routera**, jak i **instalację 65 pakietów Pi-hole/Entware przez opkg w odizolowanym kontenerze ARMv7** ([dowód EN](../../evidence/2026-10-09/issue-129-offline-pihole-opkg-cleanroom.md)). **Nie** potwierdziły pełnego odtworzenia pustego routera, konfiguracji usług ani DNS/DHCP po awarii.

## Aktualne informacje i granice wdrożenia — przegląd 28 października 2026

- **Granica źródeł (stan przeglądu 28 października):** `main` i [PROJECT-STATUS.md (EN)](../../PROJECT-STATUS.md) mają pierwszeństwo przed niescalonymi propozycjami. Na ASUS-ie 25 października operator potwierdził [ograniczoną aktualizację trzech plików WebUI #283](../worklog/2026-10-25.md), bez zmian DNS i firewalla. Nowsze obserwacje Tailscale z 28 października są już opublikowane w [dzienniku](../worklog/2026-10-28.md) po [scaleniu PR #326](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/326); są dowodem operatora w określonym zakresie, nie pełnym testem cold boot/IPv6.
- **Fedora monitoring (27 października):** [Scalone PR #324](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/324) i [datowane dowody Grafana 13.3.0 / Loki](../../evidence/2026-10-27/fedora-grafana-1330-loki-series-cap.md) obejmują ograniczone testy monitoringu. Oddzielny opis VictoriaMetrics 1.155.0 i HCC znajduje się w [dzienniku 27 października](../worklog/2026-10-27.md) ([scalone PR #325](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/325)); wcześniejszy, częściowy [Draft PR #317](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/317) został zastąpiony pełniejszym dziennikiem. Wyniki nie dowodzą pełnej dostępności systemu ani trwałego wdrożenia HCC.
- **Homelab Control Center:** tylko V0.1–V0.3 są scalone do `main`; V0.4 ([Draft #318](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/318)), V0.5 ([Draft #323](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/323), zależny od #318) i modele historii DNS Guard ([#319](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/319)) pozostają odrębnymi pracami Fedora-only. Archiwum nie jest LIVE, a nieprzerwanego DNS klientów nie potwierdzono. **Stałe uruchamianie, dostęp z sieci i wdrożenie pozostają HOLD.**
- **RouterCloud Metro:** interaktywna mapa zajętości dysku [#327](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/327) jest propozycją laboratoryjną, nie wdrożoną funkcją interfejsu.
- **Stan produkcyjny na 24 października:** [PROJECT-STATUS.md (EN)](../../PROJECT-STATUS.md) i [dziennik 24 października (EN)](../worklog/2026-10-24.md). Na ASUS-ie po nieudanej pierwszej próbie i osobnym, udanym wdrożeniu R2 działa **Unbound 1.26.2-1 (5/5 pakietów)**. Sprawdzenia DNSSEC AD/SERVFAIL bezpośrednio przez UDP i TCP, dnsmasq oraz Pi-hole przeszły w ustalonym zakresie. [Raport operacyjny (EN)](../operations/unbound-1.26.2-production-deployment-2026-10-24.md) i [opis awarii (EN)](../case-studies/unbound-dnssec-autotrust-opkg-incident-2026-10-24.md) zachowują także historię błędnej pierwszej próby.
- **Dalszy restart ASUS-a:** po rzeczywistym restarcie pakiety, procesy, nasłuchy, DNSSEC i ścieżki klientów przeszły ograniczoną kontrolę. Jednocześnie aktywny plik RFC 5011 `root.key` miał tryb **`0666`** w katalogu **`0700`**. Utwardzanie [#298](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/298) i zgodność PID/Manager [#299](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/299) pozostają **OTWARTE / HOLD**, bez wdrożonej poprawki. Nie potwierdzono zaniku zasilania (cold boot), nieprzerwanego DNS podczas startu ani długotrwałego testu.
- **DNS Guard / powiadomienia:** odczyt dzienników potwierdził **spontaniczne** przejście routerowego resolvera na DNS WAN i powrót do Pi-hole podczas wcześniejszej awarii. Nie jest to test kontrolowanego wymuszenia błędu ani dowód automatycznego failover DNS klientów LAN. Grafana miała opóźnione doręczenia alarmów przy błędach DNS; [analiza incydentu (EN)](../case-studies/dns-guard-grafana-alert-delivery-dns-failure-2026-10-24.md). Problem timera [#287](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/287) pozostaje **laboratoryjny / HOLD**.
- **Starsze punkty odniesienia:** [dziennik 17 października](../worklog/2026-10-17.md) i [dziennik 18 października](../worklog/2026-10-18.md) opisują wcześniejsze działania, a nie bieżącą wersję Unbound. Raporty Fedora/QEMU i odczyty z ASUS-a nie są zamiennymi dowodami wdrożenia.
- [Architektura produkcyjna ASUS v1.2 (Markdown, EN)](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.md) oraz [PDF v1.2](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.pdf) — **datowany** stan z 15 października; nie jest to świeży test całej infrastruktury.
- [Issue #235 — bezpieczeństwo RouterCloud i uprawnienia SSD](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) pozostaje **OTWARTE / `DEPLOYMENT_GATE=HOLD`**. [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) dotyczy eksperymentalnej naprawy uprawnień po montowaniu; **nie został wdrożony**. Native SSD Trust Helper v1 był testowany lokalnie na ARMv7/QEMU (12/12 negatywnych przypadków PASS), ale nie działa na produkcyjnym ASUS-ie i nie upoważnia do `chmod`.
- **Ustalenie Issue #235 z 18 października (historyczny punkt kontrolny):** zatwierdzony audyt **tylko do odczytu** wykazał, że plik DNS Guard wykonywany przez root z Cron ma nie-rootowego właściciela/grupę i uprawnienie zapisu dla właściciela. Zawartość SHA-256 odpowiadała przejrzanej wersji v3.2, lecz zgodność treści **nie rozwiązuje problemu zaufania do uprawnień**. Testy naprawy na Fedorze były syntetyczne; produkcyjne `chown`, podmiana pliku, edycja Cron lub użycie instalatora pozostają **HOLD**. Szczegóły: [operacje (EN)](../operations.md#dns-guard-privileged-cron-target-ownership--review-hold-2026-10-18), [worklog (EN)](../worklog/2026-10-18.md) i [polska instrukcja wdrożenia](../deployment-pl.md).
- [Issue #263 — audyt uprawnień obiektów SSD](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/263) pozostaje **OTWARTE / AUDIT-ONLY**: zidentyfikowano 12 plików `0666` i 3 katalogi `0777` pierwszego poziomu. Nie jest to potwierdzenie wykorzystania podatności i nie upoważnia do masowego `chmod`/`chown`.
- [Projekt przyszłej architektury Flint 4 + ASUS (EN)](../architecture/Flint4-ASUS-Future-Architecture-2026-10-15.md) jest **wariantem planistycznym**, a nie aktualnym sprzętem. OPNsense pozostaje możliwą, nieokreśloną w czasie alternatywą; nie ma zatwierdzonej migracji.
- [Odporność DNS klientów — Issue #212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212) pozostaje wstrzymana do czasu niezależnego sprzętu. [Transfer dużych plików RouterCloud — Issue #254](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/254) jest w fazie pomysłu, **bez wdrożonego wznawiania transferów**.
- Odtwarzanie routera od zera ([Issue #129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)) nadal **nie ma pełnego testu bare-metal**. Zestaw 65 pakietów IPK oraz Pi-hole `2026.09.20-1` jest **historycznym wynikiem testu z 9 października**, nie automatycznie zgodnym zestawem dla każdej późniejszej wersji pakietu. Przed odtworzeniem należy ponownie sprawdzić wersje binariów, pakiety, manifesty i zależności; zobacz [polską procedurę DR](../router-bare-metal-recovery-pl.md).

## Powiązane materiały i historia prac

- [Końcowy audyt uprawnień katalogów #200 — wyniki i ograniczenia (EN)](../../evidence/2026-10-09/issue-200-final-permissions-acceptance.md) — 698 obiektów, jeden wyjątek Pi-hole, testy regresji PR #209, zgłoszenie zamknięte; **bez testu awaryjnego rollbacku na produkcji**.
- [Dziennik prac 9 października (EN)](../worklog/2026-10-09.md) — bieżący stan DR #129, wdrożenia BusyBox i zamknięcia #200.
- [Przegląd architektury — migawka z 2026-10-08](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-08.md) — datowany opis, nie automatycznie aktualizowana dokumentacja.
- Polska nakładka językowa ASUS WebUI i polski interfejs RouterCloud są elementami **lokalizacji produktu**, a nie polską kopią całego repozytorium.

## Zasady korzystania

1. Przed wdrożeniem lub przywracaniem sprawdź bieżący stan projektu i **datę potwierdzonych testów**.
2. Komendy, adresy ścieżek, nazwy zmiennych `EDGE_*`, nazwy testów i komunikaty `PASS/FAIL` zapisujemy w oryginale.
3. Przy rozbieżności PL/EN zatrzymaj zmianę i porównaj obie procedury z dowodami produkcyjnymi — nie zgaduj.
4. Przegląd lub tłumaczenie dokumentu **nie stanowi testu** poprawności odbudowy infrastruktury.

Polityka językowa została przyjęta i [Issue #206](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/206) jest **zamknięte**. Nowe rozbieżności między instrukcjami PL i kontraktami EN wymagają osobnego przeglądu dokumentacji i kontrolowanego PR; nie traktuj zamkniętego zgłoszenia jako bieżącej listy zadań.
