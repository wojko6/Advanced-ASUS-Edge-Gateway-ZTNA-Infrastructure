# Dokumentacja po polsku — ASUS Edge Gateway

**Status:** indeks bieżących instrukcji i dokumentów pomocniczych  
**Aktualizacja:** 2026-10-16 (przegląd spójności indeksu; bez nowego testu produkcyjnego ASUS-a)

Ten katalog ułatwia znalezienie polskich instrukcji administracyjnych. Nie jest osobną kopią całej dokumentacji projektu. **Techniczny stan infrastruktury i zasady bezpieczeństwa** pozostają opisane w [PROJECT-STATUS.md](../../PROJECT-STATUS.md), [modelu dokumentacji](../documentation-model.md) i [polityce językowej](../language-policy.md).

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

Punkt startowy: [indeks Disaster Recovery](../disaster-recovery-index.md) — wskazuje, **który dokument otworzyć**, które testy przeszły i czego nadal nie udowodniono. Materiały operacyjne scalono w [PR #205](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/205). Polska instrukcja jest **rozszerzoną adaptacją dla operatora**, nie tłumaczeniem zdanie po zdaniu. Testy z 2026-10-09 potwierdziły zarówno **restart istniejącego routera**, jak i **instalację 65 pakietów Pi-hole/Entware przez opkg w odizolowanym kontenerze ARMv7** ([dowód EN](../../evidence/2026-10-09/issue-129-offline-pihole-opkg-cleanroom.md)). **Nie** potwierdziły pełnego odtworzenia pustego routera, konfiguracji usług ani DNS/DHCP po awarii.

## Aktualne informacje i granice wdrożenia — 16 października 2026

- [Bieżący stan projektu (EN)](../../PROJECT-STATUS.md) i [dziennik prac 16 października (EN)](../worklog/2026-10-16.md) — najnowsze wyniki badań, z wyraźnym oddzieleniem testów Fedory/QEMU od stanu ASUS-a.
- [Architektura produkcyjna ASUS v1.2 (Markdown, EN)](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.md) oraz [PDF v1.2](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.pdf) — **datowany** stan z 15 października; nie jest to świeży test całej infrastruktury.
- [Issue #235 — bezpieczeństwo RouterCloud i uprawnienia SSD](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) pozostaje **OTWARTE / `DEPLOYMENT_GATE=HOLD`**. [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) dotyczy eksperymentalnej naprawy uprawnień po montowaniu; **nie został wdrożony**. Native SSD Trust Helper v1 był testowany lokalnie na ARMv7/QEMU (12/12 negatywnych przypadków PASS), ale nie działa na produkcyjnym ASUS-ie i nie upoważnia do `chmod`.
- [Projekt przyszłej architektury Flint 4 + ASUS (EN)](../architecture/Flint4-ASUS-Future-Architecture-2026-10-15.md) jest **wariantem planistycznym**, a nie aktualnym sprzętem. OPNsense pozostaje możliwą, nieokreśloną w czasie alternatywą; nie ma zatwierdzonej migracji.
- [Odporność DNS klientów — Issue #212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212) pozostaje wstrzymana do czasu niezależnego sprzętu. [Transfer dużych plików RouterCloud — Issue #254](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/254) jest w fazie pomysłu, **bez wdrożonego wznawiania transferów**.
- Odtwarzanie routera od zera ([Issue #129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)) nadal **nie ma pełnego testu bare-metal**; pozytywny test pakietów w kontenerze ARMv7 i restart istniejącego routera nie są takim odtworzeniem.

## Inne materiały po polsku

- [Końcowy audyt uprawnień katalogów #200 — wyniki i ograniczenia (EN)](../../evidence/2026-10-09/issue-200-final-permissions-acceptance.md) — 698 obiektów, jeden wyjątek Pi-hole, testy regresji PR #209, zgłoszenie zamknięte; **bez testu awaryjnego rollbacku na produkcji**.
- [Dziennik prac 9 października (EN)](../worklog/2026-10-09.md) — bieżący stan DR #129, wdrożenia BusyBox i zamknięcia #200.
- [Przegląd architektury — migawka z 2026-10-08](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-08.md) — datowany opis, nie automatycznie aktualizowana dokumentacja.
- Polska nakładka językowa ASUS WebUI i polski interfejs RouterCloud są elementami **lokalizacji produktu**, a nie polską kopią całego repozytorium.

## Zasady korzystania

1. Przed wdrożeniem lub przywracaniem sprawdź bieżący stan projektu i **datę potwierdzonych testów**.
2. Komendy, adresy ścieżek, nazwy zmiennych `EDGE_*`, nazwy testów i komunikaty `PASS/FAIL` zapisujemy w oryginale.
3. Przy rozbieżności PL/EN zatrzymaj zmianę i porównaj obie procedury z dowodami produkcyjnymi — nie zgaduj.
4. Przegląd lub tłumaczenie dokumentu **nie stanowi testu** poprawności odbudowy infrastruktury.

Wszelkie zmiany zasad należy zgłaszać w [Issue #206](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/206).
