# HCC V0.14.5A–D — instrukcja izolowanego laboratorium

**Status:** polska adaptacja operatorska, 2026-10-30; Draft PR #338,
bez scalenia i bez wdrożenia. **DEPLOYMENT_GATE=HOLD.**
Źródłem kontraktu i ograniczeń jest
[dokument angielski V0.14.5A–B](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5-OFFLINE-SEGMENT-REPLAY-LAB.md).
Etap C opisuje [osobny kontrakt zapisu punktu wznowienia](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5C-DISPOSABLE-CHECKPOINT-LAB.md).
Etap D opisuje [osobny kontrakt syntetycznej tożsamości rekordów](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5D-SYNTHETIC-EVENT-IDENTITY-LAB.md).
Instrukcja jest z nimi uzgodniona. Operator potwierdził już A–B na Fedorze:
**59/59 testów OK, oba laboratoria PASS i sprzątanie YES**. Następnie osobno
potwierdził C: **28/28 testów OK w 0.171 s, laboratorium i sprzątanie PASS**.
To dwa uruchomienia na kolejnych rewizjach, bez akceptacji rzeczywistego Alloy/SELinux.

## Co sprawdzamy

- V0.14.5A zapisuje syntetyczne, niezmienne segmenty w prywatnym katalogu
  tymczasowym. Sprawdza cały istniejący bufor, uprawnienia, hash, blokadę
  współpracujących procesów oraz błędy zapisu. Retencja tylko wskazuje
  kandydatów; nie usuwa segmentów.
- V0.14.5B odtwarza zamknięty zestaw segmentów do odbiornika w pamięci.
  Punkt wznowienia przesuwa dopiero po potwierdzeniu konkretnego segmentu.
  Utrata punktu wznowienia po odbiorze może spowodować powtórzenie; nie
  deklarujemy dostarczania dokładnie raz ani rzeczywistego odbioru przez Loki.
- Nakładające się rekordy, niejednoznaczna kolejność czasowa, obce pliki,
  osierocone pliki tymczasowe i zmieniony zestaw segmentów oznaczają HOLD.
  Nie ma automatycznej naprawy ani kasowania pozostałości.

## Uruchomienie bez sudo

W osobnym checkoutcie gałęzi PR #338 przejdź do
`experiments/fedora/homelab-control-center-v0.1`. Wymagany Linux i Python 3.10+
z obsługą `flock` katalogu. Polecenia laboratoryjne nie przyjmują ścieżki
produkcyjnej ani adresu serwera.

```bash
python3 -B tools/v0145a_segment_spool.py --self-test
python3 -B tools/v0145a_segment_spool.py --lab
python3 -B tools/v0145b_segment_replay.py --self-test
python3 -B tools/v0145b_segment_replay.py --lab
python3 -B -m unittest discover -s tests -p 'test_v0145[ab]*.py' -v
```

Self-testy pracują tylko w pamięci. Tryby `--lab` i testy jednostkowe tworzą
jedynie losowe katalogi w `/tmp`, po czym je usuwają. Jeden test uruchamia
osobne krótkie procesy testowe i kończy je bez bloków sprzątania, aby sprawdzić
pozostałości oraz zwolnienie blokady. To nie symuluje utraty zasilania dysku.

Oczekiwane: **59 testów PASS**, oba self-testy PASS,
`V0145A_RESULT=PASS_SYNTHETIC_SEGMENTS_ONLY`,
`V0145B_RESULT=PASS_SYNTHETIC_REPLAY_MODEL_ONLY`, `TEMP_STATE_REMOVED=YES`
i `DEPLOYMENT_GATE=HOLD`. Przy błędzie zatrzymaj procedurę i zachowaj wynik;
nie usuwaj prawdziwego bufora w celu wymuszenia PASS.

## Osobny etap C — plik punktu wznowienia

W nowszej rewizji tej samej gałęzi dostępny jest etap C. Zapisuje atomowo
`checkpoint.json` w prywatnym katalogu testowym, odczytuje go po ponownym
otwarciu i sprawdza wznowienie także w osobnym procesie. Przerwanie po ACK
przed zapisem nadal może dać powtórną próbę; nie deklarujemy exactly-once.

```bash
python3 -B tools/v0145c_checkpoint_store.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145c*.py' -v
python3 -B tools/v0145c_checkpoint_store.py --lab
```

Oczekiwane: **28 testów OK**,
`V0145C_RESULT=PASS_DISPOSABLE_CHECKPOINT_ONLY`, `TEMP_STATE_REMOVED=YES`
i `POWER_LOSS_DURABILITY=NOT_TESTED`. Łącznie A–C: **87 testów**.
Osierocony plik tymczasowy blokuje wznowienie i wymaga przeglądu; brak
automatycznej naprawy. Nagłe zakończenie procesu nie jest utratą zasilania.
Wszystkie dane C są usuwane wraz z katalogiem testowym. **Nie zainstalowano
trwałego magazynu punktu wznowienia. C przeszedł już osobny test na Fedorze:
28/28, `V0145C_RESULT=PASS_DISPOSABLE_CHECKPOINT_ONLY` oraz
`FEDORA_V0145C_LAB=PASS`.** Odtworzono prefiks 1, końcowy prefiks wyniósł 2;
trzecia próba odbioru była oczekiwanym powtórzeniem po utracie zapisu.

## Osobny etap D — identyfikatory syntetycznych rekordów

D rozróżnia rekordy mające tę samą klasę i czas, zachowuje mikrosekundy i
wykrywa powtórzenia po identyfikatorze. Zmiana treści pod tym samym ID oznacza
HOLD dla całej partii, bez częściowego zapisu do rejestru w pamięci.
Surowe boot/cursor i klucz nie są kopiowane do wyniku. Użyty HMAC z **publicznym
kluczem testowym** nie potwierdza pochodzenia z journala. Jednostka i kursor
są tylko deklarowanymi polami syntetycznej koperty.

```bash
python3 -B tools/v0145d_event_identity.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145d*.py' -v
python3 -B tools/v0145d_event_identity.py --lab
```

Oczekiwane: **31 testów OK**, `V0145D_RESULT=PASS_SYNTHETIC_IDENTITY_ONLY`,
`SOURCE_PROVENANCE=DECLARED_SYNTHETIC_NOT_AUTHENTICATED`,
`A_C_SPOOL_SCHEMA_COMPATIBLE=NO`, `LEDGER_PERSISTENCE=NOT_IMPLEMENTED`
i `DEPLOYMENT_GATE=HOLD`. Oba tryby i testy D pracują wyłącznie w pamięci:
bez plików, sieci, subprocessów, journala i zmian usług.

Format D jest **osobny i niekompatybilny z buforem A–C**. Nie usuwaj pól ID,
aby obejść jego walidację. Nie ma trwałego rejestru, prywatnego klucza hosta,
autentykacji źródła, połączenia z rzeczywistym buforem/Alloy ani exactly-once.
ID dotyczy rekordu, a nie awarii czy pojedynczego uruchomienia kolektora.
D ma wynik Work/CI zgodnie z bieżącym PR; brak wyniku operatora na Fedorze.

## Granice wyniku — bieżący stan

W środowisku Work wykonano A–D **118/118 testów**, pełne HCC **323/323 Python**
i **55/55 JavaScript**. Na Fedorze operator potwierdził A–B (59/59 i oba
laboratoria), następnie C (28/28 i laboratorium). Są to dwa osobne uruchomienia,
bez wyniku pełnej regresji HCC na Fedorze. Brak akceptacji rzeczywistego Alloy,
SELinux, trwałych ACL i utraty zasilania. Wklejony wynik C nie zawierał
wersji Pythona/jądra, SHA checkoutu ani wyjścia self-testu; nie dopisujemy ich
na podstawie pamięci wcześniejszych sesji.
Poprzedni ZIP z 19
testami jest historyczną wersją V0.14.5A, a nie aktualnym kodem tej gałęzi.

Nie ma czytnika journala, zaufanej tożsamości rzeczywistych zdarzeń, produkcyjnego
magazynu punktu wznowienia, automatycznej retencji, usługi ani nowego endpointu HCC. Istniejący
nieaktywny fragment Alloy wskazuje pojedynczy plik i nie obsługuje tego modelu
segmentów. Nie podłączaj go do tych narzędzi ani do produkcyjnego Loki.

Scalenie PR, utworzenie trwałego bufora lub zmiana usług Fedora/ASUS wymagają
osobnej, wyraźnej zgody użytkownika. **DEPLOYMENT_GATE=HOLD.**
