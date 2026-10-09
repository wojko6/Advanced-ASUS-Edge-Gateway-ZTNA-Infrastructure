# Dokumentacja po polsku — ASUS Edge Gateway

**Status:** indeks bieżących instrukcji i dokumentów pomocniczych  
**Aktualizacja:** 2026-10-09

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

Dokumenty scalono w [PR #205](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/205). Polska instrukcja jest **rozszerzoną adaptacją dla operatora**, nie oficjalnym przekładem zdanie po zdaniu. Próby z 2026-10-09 potwierdziły trwałość działających usług po restarcie, **nie** pełne odtworzenie routera i pakietów od pustego urządzenia.

## Inne materiały po polsku

- [Przegląd architektury — migawka z 2026-10-08](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-08.md) — datowany opis, nie automatycznie aktualizowana dokumentacja.
- Polska nakładka językowa ASUS WebUI i polski interfejs RouterCloud są elementami **lokalizacji produktu**, a nie polską kopią całego repozytorium.

## Zasady korzystania

1. Przed wdrożeniem lub przywracaniem sprawdź bieżący stan projektu i **datę potwierdzonych testów**.
2. Komendy, adresy ścieżek, nazwy zmiennych `EDGE_*`, nazwy testów i komunikaty `PASS/FAIL` zapisujemy w oryginale.
3. Przy rozbieżności PL/EN zatrzymaj zmianę i porównaj obie procedury z dowodami produkcyjnymi — nie zgaduj.
4. Przegląd lub tłumaczenie dokumentu **nie stanowi testu** poprawności odbudowy infrastruktury.

Wszelkie zmiany zasad należy zgłaszać w [Issue #206](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/206).
