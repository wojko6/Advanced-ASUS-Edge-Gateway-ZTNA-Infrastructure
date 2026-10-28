# Zacznij tutaj — przewodnik po repozytorium ASUS Edge Gateway

**Status:** CURRENT / TYLKO NAWIGACJA  
**Przegląd:** 2026-10-28 (nawigacja, stan roboczych PR i odnośniki do dowodów; bez nowych testów routera ani usług)  
**Język:** polski przewodnik dla czytelnika · [English version](../START-HERE.md)

Nie musisz czytać całego repozytorium ani uruchamiać żadnych poleceń, żeby zrozumieć projekt. Ta strona jest **mapą lektury**, a nie instrukcją instalacji czy zgodą na wdrożenie.

## Co to za projekt?

To rozbudowane laboratorium sieciowe Home/SMB oparte na **ASUS TUF-AX5400** z oprogramowaniem GNUton Asuswrt-Merlin. Łączy kontrolę ruchu i dostępów, zdalny dostęp Tailscale, DNS z Pi-hole i Unbound, RouterCloud, procedury odtwarzania oraz monitoring na oddzielnym komputerze Fedora. Ważne są nie tylko funkcje, lecz również udokumentowane decyzje i wyniki testów.

**Ważna granica:** ASUS pozostaje działającą bramą sieciową. To *laboratorium o podejściu zbliżonym do rozwiązań firmowych*, ale **nie** infrastruktura o wysokiej dostępności (HA). Wariant Flint 4 + ASUS oraz przyszły OPNsense to **projekty i badania**, a nie wykonana migracja. Aktualny stan opisuje [PROJECT-STATUS.md](../../PROJECT-STATUS.md).

## Pierwsza wizyta: trasa na 15–20 minut

Podane czasy to orientacyjne **czasy czytania**, nie wyniki testów. Przeglądaj najważniejsze sekcje — nie czytaj od razu całych publikacji.

| Krok | Co otworzyć | Na co zwrócić uwagę | Około |
| --- | --- | --- | --- |
| 1 | [Wprowadzenie i najważniejsze osiągnięcia](../../README.md#portfolio-highlights) | Cel projektu, możliwości i ograniczenia | 3 min |
| 2 | [Aktualna architektura ASUS v1.2](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.md) ([PDF, 17 stron](../architecture/ASUS-Edge-Gateway-Architecture-2026-10-15-v1.2.pdf)) | Schemat, role ASUS-a i Fedory, DNS, magazyn danych; **przejrzyj**, nie czytaj od razu całego PDF | 5 min |
| 3 | [Granice zaufania](../architecture/high-level-trust-boundaries.md) | Kto i z jakiej sieci może uzyskiwać dostęp do usług | 4 min |
| 4 | [Stan projektu](../../PROJECT-STATUS.md) | Najpierw początek dokumentu, datowane testy produkcyjne i ograniczenia HOLD/NOT DEPLOYED | 5 min |
| 5 | [Model dokumentacji](../documentation-model.md) | Który dokument jest źródłem prawdy przy rozbieżności między planem, testem a produkcją | 2 min |

**Po tych pięciu krokach możesz zakończyć pierwszą wizytę.** Jeżeli chcesz wiedzieć więcej, wybierz *jedną* ścieżkę poniżej.

## Wybierz ścieżkę według zainteresowań

| Interesuje Cię… | Czytaj dalej | Na razie możesz pominąć… |
| --- | --- | --- |
| Ogólny obraz projektu / portfolio | [Osiągnięcia](../../README.md#portfolio-highlights) → [studia przypadków](../CASE-STUDIES.md) | Surowe raporty testowe i dzienniki |
| Inżynieria sieciowa | [Indeks architektury](../network-design.md) → [topologia](../architecture/physical-topology.md) → [adresacja i strefy](../architecture/addressing-and-zones.md) | Dawne diagramy i hipotetyczne migracje |
| Bezpieczeństwo / Zero Trust | [Model bezpieczeństwa](../security.md) → [model zagrożeń](../threat-model.md) → [polityka zapory](../firewall-policy.md) | Szczegółowe dowody każdego zabezpieczenia |
| Administracja / instalacja | [Operations](../operations.md) → [polski indeks operatora](README.md) → [instrukcja wdrożenia](../deployment-pl.md) | Uruchamianie komend, dopóki nie znasz wymagań, kopii zapasowych i zasad zatwierdzania |
| Awarie / odzyskiwanie | [Indeks Disaster Recovery](../disaster-recovery-index.md) → [techniczna procedura DR](../router-disaster-recovery.md) | Odtwarzanie działającego routera: pełna odbudowa pustego urządzenia nie jest jeszcze potwierdzona |
| Testy / odtwarzalność | [Strategia testów](../testing.md) → [wymagania i kryteria akceptacji](../requirements.md) → [zbieranie dowodów](../evidence-collection.md) | Archiwum dowodów, dopóki nie weryfikujesz konkretnej tezy |
| Historia / plany | [Roadmap](../roadmap.md) → [dziennik prac](../worklog/README.md) | Traktowanie historycznego pomysłu lub wyniku PASS w laboratorium jako stanu produkcyjnego |

### Opcjonalne laboratorium panelu monitoringu Fedora

[Homelab Control Center V0.1–V0.3](../../experiments/fedora/homelab-control-center-v0.1/README.md) to **nie** interfejs WebUI ASUS-a ani usługa uruchamiana automatycznie. W scalonej wersji V0.3 tylko dwa panele korzystają z ograniczonej, rzeczywistej telemetrii VictoriaMetrics i DNS Guard. Pozostałe dane DEMO są domyślnie ukryte i wymagają świadomego włączenia. [Testy HTTPS i granice wnioskowania (EN)](../../experiments/fedora/homelab-control-center-v0.1/V0.3-DNS-GUARD-PREFLIGHT.md) nie oznaczają pełnej weryfikacji DNS ani stałego wdrożenia. **DEPLOYMENT_GATE=HOLD.**

**Rozszerzenia niescalone (nieobecne na `main`):** HCC V0.4 w [Draft PR #318](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/318) proponuje trzeci panel LIVE z pojedynczym testem Blackbox DNS routera. V0.5 w [zależnym Draft PR #323](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/323) proponuje **ręcznie otwierane, datowane archiwum**, nie strumień zdarzeń LIVE. Osobne doświadczenia z historią DNS Guard [Issue #319](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/319) i [Draft PR #320–#322](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/320) nie oznaczają automatycznego failover DNS klientów ani instalacji usługi. Przed uznaniem funkcji za obecną w systemie trzeba sprawdzić status scalenia i wyniki właściwych testów.

**Granica publikacji:** [Draft PR #325](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/325) zawiera propozycję publicznego dziennika za 27 października, a [Draft PR #326](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/326) — za 28 października i prace nad Tailscale. Dopóki nie zostaną scalone, ich wpisy nie są częścią `main`. Osobne [scalone PR #324](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/324) dotyczy monitoringu Grafana/Loki z 27 października. TreeMap zajętości dysków w RouterCloud [#327](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/327) pozostaje pomysłem.

## Mapa katalogów

- **Katalog główny:** [README](../../README.md) przedstawia projekt, [PROJECT-STATUS](../../PROJECT-STATUS.md) opisuje bieżący stan i ograniczenia, [CHANGELOG](../../CHANGELOG.md) zmiany, a [CONTRIBUTING](../../CONTRIBUTING.md) zasady współpracy.
- **`docs/`:** architektura, instrukcje, indeksy tematyczne, studia przypadków, plany i audyty. Korzystaj najpierw z indeksów, nie z alfabetycznej listy plików.
- **`docs/architecture/`:** aktualna, **datowana architektura ASUS-a** oraz warianty historyczne i przyszłe. Wyższy numer wersji *przyszłego wariantu* nie oznacza wdrożenia.
- **`docs/pl/`:** ten przewodnik i polskie materiały operatora. [Polityka językowa](../language-policy.md) wyjaśnia, dlaczego część kanonicznych materiałów pozostaje po angielsku.
- **`evidence/YYYY-MM-DD/`:** zanonimizowane dowody ograniczone datą i środowiskiem. Wynik z laboratorium Fedora/QEMU **nie** oznacza automatycznie wdrożenia na ASUS-ie.
- **`docs/worklog/` i `docs/audits/`:** historia prac i przeglądów, nie zastępstwo aktualnych instrukcji.
- **`scripts/`, `router/`, `monitoring/`, `tests/`:** implementacja i testy; zajrzyj tu po poznaniu architektury i zakresu projektu.

## Jak rozumieć oznaczenia?

| Oznaczenie | Co oznacza |
| --- | --- |
| **CURRENT** | Utrzymywany dokument w granicach podanej daty i zakresu |
| **HISTORICAL / SUPERSEDED** | Zapis historyczny, nie najnowsza instrukcja konfiguracji |
| **PLANNED / DRAFT** | Pomysł lub projekt; **nie** oznacza wdrożenia |
| **PASS** | Przeszedł *konkretny test* — trzeba sprawdzić datę, środowisko i ograniczenia |
| **LAB ONLY / Fedora / QEMU** | Badanie izolowane; nie dowodzi wykonania na routerze ASUS |
| **NOT DEPLOYED / HOLD / NO-GO** | Brak akceptacji produkcyjnej; nie należy zakładać instalacji ani zgody na zmianę |

**Jak sprawdzać ważne twierdzenia?** Zacznij od [PROJECT-STATUS](../../PROJECT-STATUS.md), następnie otwórz odpowiedni **aktualny dokument**, a na końcu jego **datowane dowody**. Przy rozbieżności stosuj [hierarchię źródeł](../documentation-model.md). Zielony wynik CI i połączenie PR nie oznaczają automatycznie wdrożenia na routerze.

## Czego nie czytać pierwszego dnia?

Możesz pominąć całe archiwum `evidence/`, dzienne wpisy `worklog/`, starsze PDF-y architektury, eksperymentalne gałęzie i obszerne komendy w runbookach wdrożeniowych. Wróć do nich, gdy chcesz zweryfikować konkretny wynik lub decyzję.

**Do zapoznania się z repozytorium nie trzeba wykonywać żadnych zmian na routerze.** Nie uruchamiaj instalatorów, przywracania kopii, napraw uprawnień, zmian DNS/firewalla ani eksperymentalnych helperów SSD/PrivDrop tylko dlatego, że są opisane. Najpierw zweryfikuj wymagania, zgodę na zmianę i bezpieczne wycofanie.

---

**Co dalej?** [Architektura sieci](../network-design.md) · [Studia przypadków](../CASE-STUDIES.md) · [Polskie instrukcje](README.md) · [Bieżący stan](../../PROJECT-STATUS.md) · [Zasady dokumentacji](../documentation-model.md)
