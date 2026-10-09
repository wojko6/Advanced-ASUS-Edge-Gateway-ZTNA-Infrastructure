# BusyBox 1.36.1 dla ASUS TUF-AX5400 — bezpieczne używanie

**Status (2026-10-09):** dodatkowa binarka BusyBox 1.36.1 (ARMv7) została zainstalowana obok firmware'owej 1.25.1 i przeszła wybrane testy na routerze. Niniejszy tekst jest **instrukcją operatora**. Kanoniczne szczegóły, zakres testów i odtwarzanie: [Custom BusyBox ARMv7 (EN)](../custom-busybox-armv7.md).

## Zasada bezpieczeństwa

- **Nie zastępuj /bin/busybox ani /bin/sh.** Główny system plików ASUS-a to squashfs zamontowany tylko do odczytu; wbudowane applety mogą zawierać poprawki producenta.
- **Nie modyfikuj globalnego PATH.** Nie zmieniaj hooków rozruchowych, DNS Guard, supervisora, Entware ani automatycznej polityki routera.
- Korzystaj z wersji opcjonalnej tylko przez **pełną ścieżkę i nazwę appletu**.
- Przy każdej nowej kompilacji sprawdź architekturę, ABI, statyczne linkowanie, sumę SHA-256, zachowanie w QEMU i na odizolowanym celu.
- Brak polecenia jest powodem do zbadania alternatyw, pakietów Entware i bezpiecznej cross-compilation — **nie do ślepej podmiany systemowych komponentów**.

## Wdrożony artefakt

| Parametr | Stan zweryfikowany 2026-10-09 |
| --- | --- |
| Router | TUF-AX5400 / GNUton 3004.388.11_1-gnuton1_tuf |
| Wersja fabryczna | BusyBox 1.25.1, /bin/busybox |
| Wersja dodatkowa | BusyBox 1.36.1, statyczny ARM EABI5 |
| Lokalizacja | /jffs/addons/asus-edge/tools/busybox/1.36.1/busybox |
| Rozmiar | 2 153 552 bajty |
| SHA-256 | 08929e6cf52e8ed49ea46f1945ac51193613550099a2bbec24f90b0c1c58763a |
| JFFS po instalacji | 19,8 MiB wolnego |
| Healthcheck po wdrożeniu | 0 błędów, 0 ostrzeżeń |

## Bezpieczne użycie (tylko odczyt)

~~~sh
BB=/jffs/addons/asus-edge/tools/busybox/1.36.1/busybox
EXPECTED=08929e6cf52e8ed49ea46f1945ac51193613550099a2bbec24f90b0c1c58763a

test -f "$BB" && test ! -L "$BB" || exit 1
ACTUAL=$(/opt/bin/sha256sum "$BB" | awk '{print $1}')
test "$ACTUAL" = "$EXPECTED" || exit 1

"$BB" --help | sed -n '1p'
"$BB" find /jffs/addons/asus-edge/backup -type l
"$BB" find /jffs/addons/asus-edge/backup -perm -0002
~~~

Puste wyjście dwóch poleceń FIND oznacza brak dopasowań **tylko wtedy, gdy polecenia wykonały się bez błędów**. Starszy firmware'owy FIND nie obsługiwał tych przełączników; wynik potoku z wc po błędzie nie jest poprawnym audytem.

## Dlaczego nie podmieniamy BusyBox w firmware?

Oryginał udostępnia 156 appletów, a nasz build 402. Pomimo większej liczby opcji **nie zawiera nazw bash i ntp** obecnych w wersji firmware'owej. Nazwy wspólnych appletów również nie gwarantują identycznego działania. Wbudowany /bin/sh jest dowiązaniem do oryginalnego BusyBox.

## Przywrócenie po awarii

**Obecny backup CORE nie kopiuje katalogu tools/.** Dlatego po odtworzeniu routera i działających usług możesz ponownie wgrać opcjonalne narzędzie z osobno zachowanego i zweryfikowanego artefaktu na Fedorze. Sprawdź ten sam SHA-256, rozmiar, ARM EABI5, brak konfliktów ścieżek i zapas wolnego JFFS, następnie wykonaj testy i healthcheck. Nie czyń BusyBox warunkiem uruchomienia DNS.

Obowiązują [kanoniczne zasady DR (EN)](../router-disaster-recovery.md) i [polska procedura odbudowy urządzenia od zera](../router-bare-metal-recovery-pl.md). **Pełna odbudowa z pustego routera i SSD pozostaje nieprzetestowana.**

## Cofnięcie instalacji

Rollback jest opisany w [dokumencie kanonicznym](../custom-busybox-armv7.md#rollback-documented-not-live-exercised), ale **nie został jeszcze wykonany w izolowanym teście**. Przed usunięciem sprawdź brak zależnych skryptów, dowiązań i zgodność SHA-256. Usuwać wolno wyłącznie dokładnie znany plik i pusty katalog jego wersji — nigdy cały katalog tools/ ani systemowy BusyBox. Przy rozbieżności **STOP**.

## Późniejsza decyzja o Issue #200 (9.10.2026)

Po instalacji dodatkowego BusyBox przeprowadzono odrębny, odczytowy audyt czterech katalogów: **698 obiektów, 0 zapisywalnych dla grupy lub pozostałych użytkowników, 0 symlinków**, jeden zachowany plik Pi-hole z właścicielem 999:999 i uprawnieniami 0640 w chronionym katalogu 0700. Testy instalatora i odtwarzania w izolacji z PR #209 przeszły CI **8/8 PASS**, a [Issue #200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200) zostało zamknięte w zakresie zabezpieczenia uprawnień.

Nie był to test rzeczywistego awaryjnego rollbacku na routerze. Osobny backup CORE nadal **nie zawiera** narzędzia z `tools/`, a pełna odbudowa #129 pozostaje otwarta. Szczegóły: [datowany raport #200 (EN)](../../evidence/2026-10-09/issue-200-final-permissions-acceptance.md).

## Status dowodów

Potwierdzono operatorowskim wynikiem: kompilacja i QEMU PASS, uruchomienie na routerze PASS, SHA-256 PASS, nowy FIND -type/-perm PASS, TIMEOUT PASS, audyt #200 bez obiektów world-writable i symlinków w czterech kontrolowanych drzewach, healthcheck 0/0. Nie potwierdzono pełnej równoważności wszystkich appletów, restartowej trwałości nowego narzędzia ani pełnego odtworzenia po awarii.
