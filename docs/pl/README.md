# Dokumentacja po polsku — ASUS Edge Gateway

**Status:** indeks bieżących instrukcji i dokumentów pomocniczych  
**Aktualizacja:** 2026-10-09

Ten katalog ułatwia znalezienie polskich instrukcji administracyjnych. Nie jest osobną kopią całej dokumentacji projektu. **Techniczny stan infrastruktury i zasady bezpieczeństwa** pozostają opisane w [PROJECT-STATUS.md](../../PROJECT-STATUS.md), [modelu dokumentacji](../documentation-model.md) i [polityce językowej](../language-policy.md).

## Dostępne instrukcje administracyjne

| Temat | Dokument po polsku | Dokumentacja techniczna EN |
|---|---|---|
| Pierwsze wdrożenie ASUS Edge Gateway | [Wdrożenie routera](../deployment-pl.md) | [Deployment/operations reference](../operations.md) |
| Drukarka w sieci lokalnej | [Instrukcja LAN](../printer-setup-lan-pl.md) | [Zasady bezpieczeństwa drukarki](../PRINTER-HARDENING.md) |
| Drukarka przez Tailscale | [Instrukcja zdalna](../printer-setup-tailscale-pl.md) | [Firewall policy](../firewall-policy.md) |

**Ważne:** kolumna EN wskazuje dokumenty technicznie powiązane, **nie** gwarantuje przekładu rozdział po rozdziale. Nie należy zakładać, że dwie procedury opisują dokładnie ten sam zakres testów.

## Odtwarzanie routera od zera — dokument w przygotowaniu

Polska procedura odbudowy ASUS-a po wyzerowaniu konfiguracji i SSD powstaje w [PR #205 — Disaster Recovery](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/205). Dopóki PR nie zostanie scalony, to **wersja do przeglądu**, a nie zatwierdzona instrukcja na `main`.

Aktualna kanoniczna dokumentacja techniczna to [Router Disaster Recovery (EN)](../router-disaster-recovery.md). Próby z 2026-10-09 potwierdziły trwałość działających usług po restarcie, **nie** pełne odtworzenie routera i pakietów od pustego urządzenia.

## Inne materiały po polsku

- [Przegląd architektury — migawka z 2026-10-08](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-08.md) — datowany opis, nie automatycznie aktualizowana dokumentacja.
- Polska nakładka językowa ASUS WebUI i polski interfejs RouterCloud są elementami **lokalizacji produktu**, a nie polską kopią całego repozytorium.

## Zasady korzystania

1. Przed wdrożeniem lub przywracaniem sprawdź bieżący stan projektu i **datę potwierdzonych testów**.
2. Komendy, adresy ścieżek, nazwy zmiennych `EDGE_*`, nazwy testów i komunikaty `PASS/FAIL` zapisujemy w oryginale.
3. Przy rozbieżności PL/EN zatrzymaj zmianę i porównaj obie procedury z dowodami produkcyjnymi — nie zgaduj.
4. Przegląd lub tłumaczenie dokumentu **nie stanowi testu** poprawności odbudowy infrastruktury.

Wszelkie zmiany zasad należy zgłaszać w [Issue #206](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/206).
