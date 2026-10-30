# HCC V0.14.5A–B — instrukcja izolowanego laboratorium

**Status:** polska adaptacja operatorska, 2026-10-30; Draft PR #338,
bez scalenia i bez wdrożenia. **DEPLOYMENT_GATE=HOLD.**
Źródłem kontraktu i ograniczeń jest
[dokument angielski V0.14.5A–B](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5-OFFLINE-SEGMENT-REPLAY-LAB.md).
Ta instrukcja została z nim uzgodniona; nie stanowi osobnej akceptacji na Fedorze.

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
python3 -B -m unittest discover -s tests -p 'test_v0145*.py' -v
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

## Granice wyniku

W środowisku Work wykonano 59/59 nowych testów oraz pełne regresje HCC:
263/263 Python i 55/55 JavaScript. Nie wykonano w tej sesji testów na laptopie
Fedora, z rzeczywistym Alloy, SELinux ani trwałymi ACL. Poprzedni ZIP z 19
testami jest historyczną wersją V0.14.5A, a nie aktualnym kodem tej gałęzi.

Nie ma czytnika journala, stabilnego identyfikatora zdarzenia, trwałego punktu
wznowienia, automatycznej retencji, usługi ani nowego endpointu HCC. Istniejący
nieaktywny fragment Alloy wskazuje pojedynczy plik i nie obsługuje tego modelu
segmentów. Nie podłączaj go do tych narzędzi ani do produkcyjnego Loki.

Scalenie PR, utworzenie trwałego bufora lub zmiana usług Fedora/ASUS wymagają
osobnej, wyraźnej zgody użytkownika. **DEPLOYMENT_GATE=HOLD.**
