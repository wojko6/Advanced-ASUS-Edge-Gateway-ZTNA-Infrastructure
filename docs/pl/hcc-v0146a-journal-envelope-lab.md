# HCC V0.14.6A — model metadanych journala i snapshot D/E

**Status:** polska adaptacja operatorska, 2026-10-30; osobny Draft po zamrożeniu
#338 na A–K. **DEPLOYMENT_GATE=HOLD.**
Źródło EN:
[kontrakt i ograniczenia V0.14.6A](../../experiments/fedora/homelab-control-center-v0.1/V0.14.6A-SUPPLIED-JOURNAL-ENVELOPE-LAB.md).

Nowa gałąź `lab/hcc-v0146a-journal-envelope-contract-20261030` bazuje na
zamrożonej gałęzi #338, commit `82ba838`. Nowy Draft jest kierowany do tej
gałęzi, dzięki czemu pokazuje wyłącznie dalszy przyrost. #338 pozostaje
Draft i niescalony; nie zmieniamy jego modułów A–K ani zakresu.

## Co jest zaimplementowane

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

## Uruchomienie laboratoryjne

W checkoutcie nowego Draft przejdź do
`experiments/fedora/homelab-control-center-v0.1`. Wymagany Python 3.10+.
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

## Wyniki i granice

Work: **29/29 V0.14.6A**, pełne HCC **571/571 Python / 55/55 JavaScript PASS**.
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
wyniku V0.14.6A na Fedorze, rzeczywistego journala/Alloy/Loki, trwałości po
restarcie, SELinux/ACL ani zaniku zasilania. Następne prace obejmują zaufany
czytnik, świeżość i blokady źródła, politykę kluczy oraz trwałe połączenie
zapis/transport/potwierdzenia. Ten adapter nie kończy całej integracji wejścia.

**Bez scalenia, usług produkcyjnych Fedora/ASUS, zmian konfiguracji,
automatycznego ponawiania i retencji. DEPLOYMENT_GATE=HOLD.**
