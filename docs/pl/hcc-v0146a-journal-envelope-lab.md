# HCC V0.14.6A–B — model metadanych journala i testowy zapis D/E

**Status:** polska adaptacja operatorska, 2026-10-30; [Draft #342](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/342) po zamrożeniu
#338 na A–K. **DEPLOYMENT_GATE=HOLD.**
Źródło EN:
[kontrakt i ograniczenia V0.14.6A](../../experiments/fedora/homelab-control-center-v0.1/V0.14.6A-SUPPLIED-JOURNAL-ENVELOPE-LAB.md).
Zapis opisuje [kontrakt V0.14.6B](../../experiments/fedora/homelab-control-center-v0.1/V0.14.6B-DISPOSABLE-IMPORT-LAB.md).

Nowa gałąź `lab/hcc-v0146a-journal-envelope-contract-20261030` bazuje na
zamrożonej gałęzi #338, commit `82ba838`. Nowy Draft jest kierowany do tej
gałęzi, dzięki czemu pokazuje wyłącznie dalszy przyrost. #338 pozostaje
Draft i niescalony; nie zmieniamy jego modułów A–K ani zakresu.

## Co jest zaimplementowane w A

Adapter działa wyłącznie w pamięci. Sprawdza podane rekordy JSONL i przekazuje
wybrane zdarzenia do modelu tożsamości D oraz kanonicznego snapshotu E.
Zachowuje mikrosekundy jako liczby całkowite i rozróżnia dwa kursory z tym
samym czasem i typem błędu. Nie dopasowuje danych przez usunięcie ID do
starszego formatu A–C.

**Podane metadane można sfałszować.** Test pokazuje, że spójnie wymyślony
rekord zostaje zaakceptowany przez ten model. Nie ma rzeczywistego czytnika
journala, weryfikacji pochodzenia, prywatnego klucza, trwałego zapisu ani ACK.
Wyjście nadal ma oznaczenie `synthetic-unit-envelope`. Wartość UID 1000 w
fiksturach jest testowa, nie jest odczytem UID operatora Fedory.

Wymagane są dokładne wartości `_SYSTEMD_USER_UNIT`, `_UID`,
`_SYSTEMD_OWNER_UID` i `_TRANSPORT=stdout`, poprawny boot/kursor oraz czas.
`USER_UNIT` czy `SYSLOG_IDENTIFIER` nie zastępują wymaganych pól. Pole
`_LINE_BREAK` powoduje HOLD. Tablice/null w wymaganych polach, błędny Unicode,
znaki kontrolne, przekroczenie limitów i niewłaściwy rekord na końcu również
odrzucają całą partię. Inne metadane nie trafiają do wyniku.

Rozpoznawane są tylko tekstowe wskazówki `SSH_TIMEOUT`, `SSH_AUTH_FAILURE`
i `HTTP_IMPORT_TIMEOUT`. Nie dowodzą przyczyny problemu sieciowego lub DNS.
Przypisywanie komunikatów managera `COLLECTOR_EXIT_255` jest poza tym etapem;
szeroki wynik zapytania o user-unit może zawierać rekordy spoza tego podzbioru.

Powtórzony boot/kursor ze zmienionym czasem lub wiadomością oznacza HOLD,
nawet gdy wiadomości dają tę samą kategorię albo obie są nierozpoznane.
Treść jest porównywana tylko w pamięci bieżącego wywołania. Deduplikacja nie
jest trwała ani między wywołaniami. Brak pasujących wiadomości daje
`snapshot=None`, bez przesunięcia kursora lub potwierdzenia odbioru.

## Uruchomienie laboratoryjne A

W checkoutcie nowego Draft przejdź do
`experiments/fedora/homelab-control-center-v0.1`. Wymagany Linux/Python 3.10+.
Oba tryby używają tylko syntetycznych danych w pamięci, bez sudo i zmian usług.

```bash
python3 -B tools/v0146a_journal_envelope.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0146a*.py' -v
python3 -B tools/v0146a_journal_envelope.py --lab
```

CLI nie przyjmuje wejścia stdin, pliku, UID, adresu serwera ani klucza.
Nie podłączaj do niego wyjścia rzeczywistego journala. Limit wejścia API to
1 MiB, 128 rekordów, 16 KiB na rekord, 64 pola i 4096 bajtów UTF-8 wiadomości;
pozostają też limity D/E. Przekroczenie oznacza HOLD, bez obcięcia danych.

Oczekiwane: **29 testów OK** oraz:

```text
INPUT_RECORDS=5 CLASSIFIED_RECORDS=4 IGNORED_RECORDS=1
UNIQUE_IDENTITY_EVENTS=3 DUPLICATE_EVENTS=1
OUTPUT=CANONICAL_E_SNAPSHOT_IN_MEMORY
TIME_PRECISION=EXACT_INTEGER_MICROSECONDS
SOURCE_PROVENANCE=UNVERIFIED_SUPPLIED_BYTES
TRUSTED_JOURNAL_READER=NOT_IMPLEMENTED
MANAGER_EXIT_255_ATTRIBUTION=NOT_SUPPORTED
PERSISTENCE_ACK_CHECKPOINT_RETENTION=NO
V0146A_RESULT=PASS_SUPPLIED_METADATA_MODEL_ONLY
DEPLOYMENT_GATE=HOLD
```

## V0.14.6B — prywatny, tymczasowy magazyn importu

B waliduje całą partię przez A i cały istniejący snapshot E, następnie scala
zdarzenia po ID i pełnej kanonicznej treści. Nowy plik zapisuje jako prywatny
plik tymczasowy `0600`, synchronizuje, atomowo zastępuje `handoff.json` i
synchronizuje katalog `0700`. Dokładne duplikaty nie przepisują snapshotu.
Osierocone pliki, uszkodzony stan i konflikty oznaczają HOLD, także przy
partii bez pasujących wiadomości. Limit magazynu to 1024 zdarzenia / 512 KiB.

```bash
python3 -B tools/v0146b_disposable_import.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0146b*.py' -v
python3 -B tools/v0146b_disposable_import.py --lab
```

Self-test B jest pamięciowy. Laboratorium B tworzy i usuwa **własny prywatny
katalog w `/tmp`**; nie ma argumentu ścieżki magazynu, pliku wejściowego,
UID, klucza czy serwera. Wymagany Linux/Python 3.10+ z blokadą `flock`
i operacjami plikowymi/fsync. Nie wymaga sudo ani zmian usług.

Oczekiwane: **32 testy OK**, `INITIAL_RETAINED_EVENTS=3`,
`REOPEN_REPLAY_DUPLICATES=4`, `DUPLICATE_REWRITE=NO`,
`LOST_RECEIPT_REPLAY=RETAINED_EVENT`, `FINAL_RETAINED_EVENTS=4`,
`FILES_WRITTEN=DISPOSABLE_E_STORE_ONLY`, `TEMP_STATE_REMOVED=YES`,
`V0146B_RESULT=PASS_DISPOSABLE_IMPORT_ONLY` i `DEPLOYMENT_GATE=HOLD`.
Sukces laboratorium jest wypisywany dopiero po usunięciu katalogu testowego.

B wyprowadza osobny klucz przestrzeni ID z klucza bazowego, oczekiwanego UID,
unitu i transportu. Klucz nie jest zapisywany. Po zachowaniu zdarzeń zmiana
UID albo klucza daje HOLD, także przy partii bez dopasowań. To nie jest
uwierzytelnienie źródła. Snapshoty samodzielnego A/E mają inną przestrzeń;
nie są automatycznie migrowane. UID polityki nie oznacza konta procesu
zapisującego plik testowy.

Testy trzech faktycznych zakończeń osobnych procesów obejmują plik tymczasowy
przed zamianą, stan po zamianie przed synchronizacją katalogu i stan po tej
synchronizacji przed zwróceniem wyniku. To obserwacje bieżącego systemu plików,
bez testu zaniku zasilania lub rebootu. Wynik zapisu nie jest ACK odbiornika.

Ważne granice: B nie zachowuje surowych wiadomości ani ich odcisków pomiędzy
wywołaniami. Zmieniony tekst z tym samym ID/czasem/kategorią może być ponownie
uznany za identyczne zdarzenie po sanitacji; test to pokazuje. Całkowita utrata
snapshotu w pustym katalogu wygląda jak nowy magazyn i pozwala na ponowny
import. Pierwsza partia bez dopasowań nie tworzy pliku ani kotwicy polityki.
Nie ma przesuwania kursora, ACK, automatycznej naprawy lub retencji.

## Wyniki i granice

Checkpoint A: **29 testów / 571 Python / 55 JavaScript PASS**. Po B: **32 B /
61 V0.14.6A–B**, pełne Work **603/603 Python / 55/55 JavaScript PASS**.
Zamrożony #338 nadal ma własny checkpoint 542 Python / 55 JavaScript; nie
dopisujemy do niego nowego etapu. Bieżące CI nowej gałęzi jest osobnym wynikiem
przypisanym do SHA w nowym Draft.

Przed publikacją test wykrył nieobsłużony wyjątek kodowania dla samotnego
surogatu Unicode; poprawka zamienia go na kontrolowany HOLD. Kolejny test
wykrył, że ta sama kategoria nie wystarcza do wykrycia zmienionej wiadomości
pod tym samym kursorem; dodano dokładne porównanie w pamięci. Nieudane wyniki
pozostają w [dzienniku EN](../worklog/2026-10-30.md).

Pełny lokalny test statyczny repozytorium nadal kończy się błędem fikstury
DNS Guard UDP/TCP; brak lokalnego shellcheck pozostaje ograniczeniem. Nie ma
wyniku V0.14.6A–B na Fedorze, rzeczywistego journala/Alloy/Loki, trwałości po
reboocie, SELinux/ACL ani zaniku zasilania. Otwarcie nowych deskryptorów i
zakończenia procesów w B nie są tą akceptacją. Następne prace obejmują zaufany
czytnik, świeżość i blokady źródła, politykę kluczy oraz trwałe połączenie
zapis/transport/potwierdzenia. Ten adapter nie kończy całej integracji wejścia.

**Bez scalenia, usług produkcyjnych Fedora/ASUS, zmian konfiguracji,
automatycznego ponawiania i retencji. DEPLOYMENT_GATE=HOLD.**
