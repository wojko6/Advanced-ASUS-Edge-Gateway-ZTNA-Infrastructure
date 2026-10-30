# HCC V0.14.5A–K — instrukcja izolowanego laboratorium

**Status:** polska adaptacja operatorska, 2026-10-30; Draft PR #338,
bez scalenia i bez wdrożenia. **DEPLOYMENT_GATE=HOLD.**
Źródłem kontraktu i ograniczeń jest
[dokument angielski V0.14.5A–B](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5-OFFLINE-SEGMENT-REPLAY-LAB.md).
Etap C opisuje [osobny kontrakt zapisu punktu wznowienia](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5C-DISPOSABLE-CHECKPOINT-LAB.md).
Etap D opisuje [osobny kontrakt syntetycznej tożsamości rekordów](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5D-SYNTHETIC-EVENT-IDENTITY-LAB.md).
Etap E opisuje [atomowy zapis identyfikatora i treści](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5E-ATOMIC-HANDOFF-LAB.md).
Etap F opisuje [testowy odbiornik i osobny plik ACK](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5F-SYNTHETIC-DELIVERY-ACK-LAB.md).
Etap G opisuje [plikowy odbiornik testowy i deduplikację zachowanych ID](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5G-DISPOSABLE-FILE-RECEIVER-LAB.md).
Etap H opisuje [formatter żądania JSON Loki działający w pamięci](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5H-OFFLINE-LOKI-REQUEST-LAB.md).
Etap I opisuje [planowanie partii z kontrolą wersji źródła i testowych ACK](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5I-OFFLINE-BATCH-PLAN-LAB.md).
Etap J opisuje [jedną wymianę HTTP z własną fiksturą loopback](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5J-OWNED-LOOPBACK-EXCHANGE-LAB.md).
Etap K opisuje [sekwencyjne wykonanie ograniczonego początku planu](../../experiments/fedora/homelab-control-center-v0.1/V0.14.5K-BOUNDED-PREFIX-EXCHANGE-LAB.md).
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

## Osobny etap E — identyfikator i treść w jednym zapisie

E zapisuje każdą parę ID/treść w jednej prywatnej migawce. Po utracie wyniku
wywołania i ponownym otwarciu dane nadal są dostępne, nawet gdy ponowienie
nie dodaje nowych ID. Używa normalizacji D, bez wcześniejszego oznaczania
rekordów jako zapamiętanych w jego rejestrze ulotnym.

```bash
python3 -B tools/v0145e_atomic_handoff.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145e*.py' -v
python3 -B tools/v0145e_atomic_handoff.py --lab
```

Oczekiwane: **34 testy OK**, `V0145E_RESULT=PASS_DISPOSABLE_ATOMIC_HANDOFF_ONLY`
i `TEMP_STATE_REMOVED=YES`. Self-test tylko w pamięci; laboratorium i testy
plikowe używają świeżych prywatnych katalogów `/tmp`, które są usuwane na końcu.
Osierocony plik tymczasowy oznacza HOLD bez automatycznego sprzątania.
Nagłe zakończenie procesu nie jest utratą zasilania.

Migawka ma maksymalnie 1024 rekordy / 512 KiB, a jej SHA-256 wykrywa uszkodzenia,
nie potwierdza pochodzenia. Format nie jest strumieniem NDJSON ani adapterem
Alloy/A–C. Brak odbiornika, ACK, automatycznego ponawiania i kasowania danych;
nie deklarujemy exactly-once ani wdrożenia trwałego bufora. E ma wynik Work,
bez akceptacji na Fedorze i bez kontaktu z usługami.

## Osobny etap F — testowy odbiornik i plik potwierdzeń

F wysyła po jednym zachowanym rekordzie E do ulotnego odbiornika w pamięci.
Zapisuje ACK dopiero po dokładnym dopasowaniu schematu, zakresu klucza, ID i
skrótu pełnej treści rekordu. To własny protokół testowy, nie potwierdzenie HTTP
Loki ani dowód trwałego odbioru. Odbiornik nie usuwa duplikatów prób.

```bash
python3 -B tools/v0145f_delivery_ack.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145f*.py' -v
python3 -B tools/v0145f_delivery_ack.py --lab
```

Oczekiwane: **37 testów OK**,
`V0145F_RESULT=PASS_DISPOSABLE_DELIVERY_ACK_ONLY`,
`ACK_PROTOCOL=IN_PROCESS_FIXTURE_NOT_LOKI`, `RECEIVER_DURABILITY=NOT_IMPLEMENTED`,
`SOURCE_PAYLOADS_RETAINED=3`, `SYNTHETIC_RECEIVE_ATTEMPTS=4`,
`TEMP_STATE_REMOVED=YES` i `DEPLOYMENT_GATE=HOLD`.
Jedno celowe powtórzenie następuje po odbiorze bez zapisu ACK.

Plik `delivery-acks.json` ma tryb 0600 w osobnym katalogu 0700, limit 1024 par
ID/hash i 256 KiB. Zapis: prywatny plik tymczasowy, pełny zapis, fsync pliku,
atomowa podmiana i fsync katalogu. Nowa para nie może nadpisać poprzedniej.
Wznowienie śledzi zbiór ID, dzięki czemu nie pomija później dodanego niższego ID;
kolejność nie jest chronologiczna. Wszystkie rekordy E pozostają zachowane.

Uszkodzony/obcy/osierocony stan, zmiana zakresu klucza lub brak/zmiana wcześniej
potwierdzonego rekordu oznaczają HOLD, bez zerowania i kasowania. Całkowita
utrata pliku ACK może spowodować ponowne próby. Skrót stanu nie uwierzytelnia
odbiornika ani zapisu; proces root i niewspółpracujący zapis z tym samym UID
nie są objęte modelem. Dwa katalogi muszą być różne i pozostawać zablokowane
przez całe wywołanie; nie współdziel deskryptorów między równoległymi wywołaniami.

Cztery testy osobnych procesów sprawdzają nagłe zakończenie po zweryfikowanym
ACK przed zapisem, po fsync pliku tymczasowego, po podmianie oraz po fsync
katalogu przed zwrotem. To nie jest zanik zasilania ani trwałość odbiornika.
Self-test jest pamięciowy; pliki laboratorium/testów pozostają w świeżych
drzewach `/tmp` usuwanych na końcu. Brak automatycznego ponawiania, retencji,
rzeczywistego transportu i adaptera Alloy/A–C. F ma wynik Work, bez testu na Fedorze.

## Osobny etap G — plikowy odbiornik i ponowienie po utracie ACK

G przechowuje pełną treść rekordu w osobnej migawce plikowej, zanim zwróci
testowe ACK z F. Po ponownym otwarciu oraz po utracie ACK znajduje ten sam ID
i identyczną treść bez ponownego zapisu migawki. To ograniczona deduplikacja
w zachowanym stanie testowym, bez gwarancji exactly-once dla rzeczywistej usługi.

```bash
python3 -B tools/v0145g_file_receiver.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145g*.py' -v
python3 -B tools/v0145g_file_receiver.py --lab
```

Oczekiwane: **36 testów OK**,
`V0145G_RESULT=PASS_DISPOSABLE_FILE_RECEIVER_ONLY`,
`REPLAY_RECEIVER_SNAPSHOT_UNCHANGED=YES`,
`FINAL_RECEIVER_RECORDS=3 FINAL_STORED_ACKS=3`, `SOURCE_PAYLOADS_RETAINED=3`,
`ACK_PROTOCOL=IN_PROCESS_FIXTURE_NOT_LOKI`, `TEMP_STATE_REMOVED=YES`
i `DEPLOYMENT_GATE=HOLD`. Wznawiany etap ma początkowo jeden rekord odbiornika
i zero zapisanych ACK. Wszystkie dane źródła i odbiornika pozostają zachowane.

Trzy katalogi muszą mieć różne inody i pozostać prywatne oraz zablokowane do
zamknięcia deskryptorów. Nie współdziel deskryptorów między równoległymi
wywołaniami. Źródło i odbiornik mają osobne pliki `handoff.json` w formacie E
(każdy do 1024 rekordów / 512 KiB), a nadawca osobny plik ACK z F (1024 par /
256 KiB). Pojedyncza treść przekazywana odbiornikowi ma limit 4096 bajtów.
Zapis odbiornika: prywatny plik tymczasowy, pełny zapis, fsync pliku, atomowa
podmiana, fsync katalogu, a następnie ACK. Duplikat wymaga ponownego fsync
katalogu, bez przepisywania pliku. Kolejność wynika z ID, nie chronologii.

Przed próbą i także po pozornym zakończeniu wysyłki G sprawdza wszystkie trzy
magazyny: każdy rekord odbiornika musi mieć identyczną treść w źródle, a każdy
zapisany ACK odpowiadać rekordowi odbiornika. Zmiana/brak wcześniej odebranego
rekordu, obcy zakres klucza, uszkodzony/obcy/osierocony stan oznaczają HOLD.
Nie ma automatycznego zerowania, kasowania ani naprawy.

Sześć przypadków nagłego zakończenia osobnego procesu obejmuje fsync pliku
tymczasowego odbiornika, podmianę, fsync katalogu odbiornika, zweryfikowane ACK
przed zapisem nadawcy, fsync pliku tymczasowego ACK oraz podmianę ACK.
Ponowienie po utracie ACK nie dopisuje drugiego rekordu o tym samym ID.
Osierocony plik po zakończeniu procesu blokuje dalszą próbę bez kasowania.
To nie są testy zaniku zasilania, restartu hosta ani trwałości zdalnej usługi.

Utrata samego pliku ACK powoduje ponowienie, które wykorzystuje zachowane ID
odbiornika. **Utrata obu plików — odbiornika i ACK — nie jest wykrywana jako
utrata historii; model zaczyna odbudowę od początku.** Skróty nie uwierzytelniają
plików, ról ani pochodzenia z journala. Brak niezależnego punktu zaufania do
wykrywania cofnięcia stanu. Root i niewspółpracujący zapis z tym samym UID
pozostają poza modelem.

Self-test jest pamięciowy; laboratorium używa tylko świeżych katalogów `/tmp`,
bez sieci i osobnych procesów. Testy jednostkowe uruchamiają ograniczone czasowo
procesy wyłącznie do prób wznowienia/przerwania. Katalogi są usuwane na końcu.
Brak transportu Loki, adaptera Alloy/A–C, automatycznych ponowień, retencji,
trwałego magazynu produkcyjnego i wyniku G na Fedorze.

## Osobny etap H — format żądania JSON bez wysyłki

H sprawdza kompletną migawkę E i formatuje jeden JSON zgodnie z opisanym kształtem
API Loki. Zachowuje mikrosekundy jako dokładne całkowite nanosekundy zapisane
napisem. Pełny rekord pozostaje linią JSON; ID, zakres klucza, czas i klasa nie
trafiają do etykiet strumienia. Żądanie ma tylko stałe etykiety `component`
i `source=synthetic-unit-envelope`. Rekordy są uporządkowane po czasie, a przy
równych czasach po ID. Kolejność i magazyny F/G pozostają bez zmian.

```bash
python3 -B tools/v0145h_loki_request.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145h*.py' -v
python3 -B tools/v0145h_loki_request.py --lab
```

Oczekiwane: **26 testów OK**,
`V0145H_RESULT=PASS_OFFLINE_REQUEST_ENCODING_ONLY`,
`MICROSECOND_PRECISION=EXACT_NO_FLOAT`, `REQUEST_BODY_BYTES=1231`,
`REQUEST_CONTRACT=DOCUMENTED_JSON_SHAPE_NOT_LOKI_ACCEPTANCE`,
`DELIVERY_OR_ACK=NOT_IMPLEMENTED`, `FILES_WRITTEN=NO SUBPROCESS=NO`
i `DEPLOYMENT_GATE=HOLD`. Oba tryby oraz testy H są wyłącznie pamięciowe,
bez sieci, plików, stdin, osobnych procesów i kontaktu z usługami. Wyjście CLI
nie drukuje treści żądania, ID ani zakresu klucza.

Limit laboratoryjny: **16 rekordów / 64 KiB treści żądania**. Są to ograniczenia
H, nie odczytana konfiguracja serwera Loki. Większa poprawna migawka jest
odrzucana w całości, bez obcinania, wyboru oczekujących rekordów i paginacji.
Uszkodzony dalszy rekord nie jest pomijany. Format A–C i surowe koperty journala
nie są wejściem tego narzędzia. Skrót treści jest sumą kontrolną, bez dowodu
pochodzenia lub dostarczenia; poprawnie podrobione ID mogą przejść formatowanie.

Zweryfikowano publiczną dokumentację API i etykiet Grafana z 2026-10-30; linki
źródłowe są w kontrakcie EN. **Nie wysłano żądania i nie potwierdzono jego
przyjęcia przez rzeczywisty Loki.** Daty graniczne 2000–2100 w testach sprawdzają
przeliczenie liczb, nie dopuszczalne okna czasowe serwera. Brak klienta HTTP,
interpretacji odpowiedzi/ACK, zmiany punktu wznowienia i integracji Alloy.
Istniejący fragment Alloy nie jest adapterem dla tego JSON-a. Ograniczenie G
dotyczące utraty pary plików nadal obowiązuje. H nie ma wyniku na Fedorze.

## Osobny etap I — plan partii bez wysyłki i zapisu postępu

I sprawdza kompletną migawkę E i zadeklarowany stan ACK w formacie F. Każdy ACK
musi odpowiadać ID i skrótowi pełnej treści w źródle. Pozostałe rekordy tworzą
plan żądań H, w kolejności czasu i ID. Każdy oczekujący rekord występuje w planie
raz; nie oznacza to dostarczenia dokładnie raz do rzeczywistego odbiornika.

```bash
python3 -B tools/v0145i_batch_plan.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145i*.py' -v
python3 -B tools/v0145i_batch_plan.py --lab
```

Oczekiwane: **30 testów OK**, `V0145I_RESULT=PASS_OFFLINE_BATCH_PLAN_ONLY`,
`PLANNED_REQUESTS=3 PENDING_SYNTHETIC_RECORDS=33`,
`BATCH_RECORD_COUNTS=16,16,1`, `PLAN_REUSE_ON_CHANGED_INPUT=HOLD`,
`ACK_BASIS=DECLARED_F_FIXTURE_NOT_LOKI_RECEIPT`, `ACK_OR_CHECKPOINT_ADVANCE=NO`
i `DEPLOYMENT_GATE=HOLD`. W pamięci jest 35 rekordów i dwa zadeklarowane ACK;
nie ma pliku stanu, odbioru ani kontaktu z Loki. Oba tryby i testy I nie tworzą
plików, sieci ani procesów; wyjście CLI nie zawiera ID, zakresu ani treści żądań.

Maksymalnie **64 żądania / 1 MiB sumy treści**, każde zgodne z limitem H:
16 rekordów / 64 KiB. Sprawdzono pełne 1024 rekordy. Uszkodzony dalszy rekord,
obcy zakres, nieznany ID lub zły hash ACK oznaczają HOLD przed budową partii.
Błąd przy budowaniu dalszego żądania nie zwraca częściowego planu. Wybór opiera
się na zbiorze ID; nowy niższy ID nie jest pomijany przy jawnej budowie nowego planu.

Plan jest powiązany z dokładnymi bajtami źródła i ACK. Ponowna kontrola przelicza
całość: zmienione źródło/ACK, treść, ID lub metadane planu oznaczają HOLD.
Ścisła kontrola typów odrzuca również `True`/`1.0` jako liczniki i modyfikowalny
`bytearray` zamiast `bytes`; wcześniejszy błąd porównania i poprawka są w dzienniku.
Przyszły kod musi przekazać świeżo odczytane bajty. I nie odczytuje/blokuje plików
i nie zapobiega zmianie danych po sprawdzeniu. Stare bajty mogą ukryć zmianę stanu.

`None` oznacza jawną deklarację braku ACK; uszkodzony stan nigdy nie zamienia się
w `None`. Brak ACK i zapisany pusty stan są różnymi podstawami planu. **ACK z F
są tutaj zadeklarowaną fiksturą, nie potwierdzeniem z rzeczywistego Loki.** I nie
sprawdza magazynu odbiornika G. Zgodnie podrobione źródło i ACK mogą dać pusty
plan bez rzeczywistego odbioru. Skróty nie uwierzytelniają danych, a ograniczenie
G dotyczące utraty pary plików nadal obowiązuje. Brak klienta HTTP, harmonogramu,
przesuwania punktu wznowienia, retencji i wyniku I na Fedorze.

## Osobny etap J — jedna wymiana z własnym odbiornikiem HTTP

J uruchamia własny tymczasowy odbiornik na numerycznym IPv4 `127.0.0.1` i porcie
wybranym przez system. Jeden proces Pythona wysyła wybraną partię H z wcześniej
zweryfikowanego planu I. Odbiornik sprawdza prywatny token tej fikstury i dokładne
bajty żądania. Nie ma opcji adresu/portu produkcyjnego ani automatycznych ponowień.

```bash
python3 -B tools/v0145j_loopback_exchange.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145j*.py' -v
python3 -B tools/v0145j_loopback_exchange.py --lab
```

Wymagane: Linux/Python 3.10+, możliwość utworzenia własnego gniazda IPv4 loopback
i jednego procesu potomnego. **Self-test jest pamięciowy; laboratorium oraz
sieciowe testy J używają własnych gniazd loopback i ograniczonych czasowo procesów.**
Nie wymagają sudo, zmiany usług, praw journala ani połączenia z rzeczywistym Loki.

Oczekiwane: **30 testów OK**,
`V0145J_RESULT=PASS_OWNED_LOOPBACK_FIXTURE_ONLY`,
`SYNTHETIC_REQUESTS_SENT=1 RECORDS_IN_REQUEST=16`,
`HTTP_STATUS=204 FIXTURE_BODY_MATCH=YES`, `CLIENT_ATTEMPTS=1 AUTOMATIC_RETRY=NO`,
`CLIENT_WORKER=EXITED_AND_REAPED FIXTURE_LISTENER=CLOSED`,
`NETWORK=OWNED_EPHEMERAL_IPV4_LOOPBACK_ONLY`,
`REAL_LOKI_ACCEPTANCE=NOT_TESTED ACK_OR_CHECKPOINT_ADVANCE=NO`
i `DEPLOYMENT_GATE=HOLD`. Fikstura zachowuje w pamięci dokładną treść żądania.
Po wymianie nadal pozostają **33 rekordy oczekujące / dwa zadeklarowane ACK**.
Nie zapisano danych do pliku ani punktu wznowienia.

Rodzic ogranicza komunikację procesu klienta do 2 sekund od jego utworzenia;
po przekroczeniu limitu lub przerwaniu kończy proces i zbiera go z osobnym
limitem 1 sekundy. Samo tworzenie procesu nie jest objęte tym limitem. Zamknięcie
kontekstu zwalnia blokadę testowego zawieszenia, zamyka połączenie/listener
i kończy wątek odbiornika. Nieudane sprzątanie oznacza HOLD. Przed publikacją
test wykrył brak tej obsługi dla `KeyboardInterrupt`; poprawka i wynik negatywny
pozostają w dzienniku. Rzeczywisty test limitu czasu zebrał proces klienta;
przerwanie oraz `OSError` sprawdzono przez wstrzyknięte wyjątki.

Sprawdzono błędne 200/260, przekierowanie, 429/500, dodatkową treść, błędne
ramkowanie, zerwane połączenie i zły status. Nie przyjmujemy ogólnego „2xx = ACK”:
dokumentacja Loki dopuszcza konfigurowalny status blokady ingestii, także 200.
J uznaje wyłącznie wybraną odpowiedź własnej fikstury oraz obserwację zgodnych
bajtów. To zależy od kontroli nad odbiornikiem i **nie dowodzi trwałego przyjęcia
przez prawdziwy Loki**. Parser HTTP może traktować 204 jako odpowiedź bez treści;
dlatego J dodatkowo sprawdza pustą odpowiedź w skrypcie kontrolowanej fikstury.

Odczyt odpowiedzi ma limit aplikacyjny 512 bajtów plus jeden bajt kontroli,
raport klienta 1 KiB. Kontrola liczby/rozmiaru nagłówków następuje po parsowaniu
przez bibliotekę standardową, nie przed nim. Nie jest to audyt produkcyjnego
klienta HTTP. Brak TLS/auth/tenantów, przyjęcia/readback Loki, wysyłki wielu
partii, mapowania odpowiedzi na ACK i blokad żywego źródła. Token fikstury nie
jest systemem uwierzytelniania hostów. J nie ma wyniku na Fedorze.

## V0.14.5K — ograniczony początek planu i zatrzymanie po błędzie

K wykonuje po kolei najwyżej cztery żądania od indeksu zero w planie I;
domyślnie wybiera trzy. Każde wysyła przez osobną własną fiksturę J. Przed
każdym żądaniem ponownie sprawdza dostarczone bajty źródła i ACK, a poprzedni
odbiornik zamyka przed kolejnym odczytem stanu. Pierwszy błąd stanu, wymiany
lub sprzątania zatrzymuje dalsze żądania. Nie ma ponowień.

```bash
python3 -B tools/v0145k_prefix_exchange.py --self-test
python3 -B -m unittest discover -s tests -p 'test_v0145k*.py' -v
python3 -B tools/v0145k_prefix_exchange.py --lab
```

Wymagania jak w J: Linux/Python 3.10+, własne gniazda IPv4 loopback i procesy
potomne. Self-test działa w pamięci. Laboratorium i sieciowe testy K tworzą
odbiorniki i ograniczone procesy klientów po kolei, bez sudo i zmiany usług.
CLI nie przyjmuje adresu, portu, ścieżki ani zmiany limitu.

Oczekiwane: **25 testów OK**, `V0145K_RESULT=PASS_OWNED_PREFIX_FIXTURES_ONLY`,
`SELECTED_PREFIX_REQUESTS=3 SEND_CALLS=3 MATCHED_FIXTURES=3`,
`OBSERVED_HTTP_POSTS=3 REMAINING_UNINVOKED_REQUESTS=0`,
`PENDING_RECORDS_AFTER_RUN=33 DECLARED_ACKS_AFTER_RUN=2`,
`STATE_CHECKS=BEFORE_EACH_SELECTED_REQUEST`,
`FAILED_BATCH_POLICY=STOP_NO_RETRY_NO_FOLLOWING_REQUEST`,
`CLIENTS_REAPED=YES LISTENERS_CLOSED=YES`,
`NETWORK=OWNED_EPHEMERAL_IPV4_LOOPBACK_ONLY`,
`REAL_LOKI_ACCEPTANCE=NOT_TESTED ACK_OR_CHECKPOINT_ADVANCE=NO`
i `DEPLOYMENT_GATE=HOLD`.

W teście odpowiedź 500 drugiej partii pozostawia jeden zgodny wynik, dwie
próby i brak otwarcia trzeciego odbiornika. Zmiana źródła/ACK przed drugą
partią zatrzymuje ją jeszcze przed otwarciem gniazda. Test rzeczywistego
zawieszenia drugiego odbiornika zbiera procesy klientów i zamyka bieżącą
fiksturę; testy przerwania i błędu sprzątania używają wstrzykniętych wyjątków.

Limit wybranych treści wynosi 256 KiB; limity pojedynczej wymiany J pozostają.
**Nie ma wspólnego twardego limitu czasu dla całego przebiegu.** Zaufana funkcja
dostarczająca stan musi przekazać świeże bajty. K nie ogranicza jej czasu, nie
blokuje żywych plików i nie wykrywa zmian ukrytych przez stare bajty. Wszystkie
skrypty odpowiedzi sprawdza przed rozpoczęciem sieci. Licznik zgodnych wymian
rośnie dopiero po udanym sprzątaniu odbiornika.

Raport rozróżnia wywołania J i zaobserwowane POST-y. Nieudana próba mogła już
dotrzeć do odbiornika; `uninvoked_requests` obejmuje także resztę planu poza
wybranym początkiem. `plan_pending_records` opisuje pierwotny plan, nie nowy
odczyt kolejki. Raport nie jest ACK ani punktem wznowienia. Nadal pozostają
33 oczekujące rekordy / dwa zadeklarowane ACK; ponowne jawne uruchomienie
zaczyna od indeksu zero i może powtórzyć wcześniejsze żądania. Nie ma trwałego
odbiornika, dowodu przyjęcia przez Loki ani wyniku K na Fedorze.

### CI dla gałęzi laboratoryjnej

Dla pierwszego commita K `9d5c0b5` ogólny CI przeszedł, lecz kolejne odczyty
Actions nie pokazały przebiegu HCC. Przyczyny nie ustalono; brak wyniku nie
jest PASS ani nieudanym testem HCC. Ten wynik pozostaje w dzienniku.

Workflow HCC uruchamia się teraz także po `push` do dokładnie tej gałęzi:
`lab/hcc-v014-alloy-manual-correlation-20261029`, przy zmianie katalogu HCC
lub pliku workflow. Nadal działa wyzwalacz PR i tryb ręczny. Push sprawdza
bezpośrednio rewizję gałęzi; oba zdarzenia mogą utworzyć osobne przebiegi.
Wynik trzeba powiązać z SHA i rodzajem zdarzenia. Zestaw 541 Python / 55
JavaScript, polecenia laboratoryjne A–K, uprawnienie odczytu repozytorium
i limit czasu zadania pozostają bez zmian. Bieżący wynik zdalny jest zapisany
w Draft #338 oddzielnie od lokalnych testów. Zielony CI nie daje zgody na
scalenie ani działania na Fedorze/ASUS. **DEPLOYMENT_GATE=HOLD.**

## Granice wyniku — aktualizacja po K

W środowisku Work wykonano A–K **336/336 testów**, pełne HCC **541/541 Python**
i **55/55 JavaScript**. Na Fedorze operator potwierdził A–B (59/59 i oba
laboratoria), następnie C (28/28 i laboratorium). Są to dwa osobne uruchomienia,
bez wyniku pełnej regresji HCC na Fedorze. Brak akceptacji rzeczywistego Alloy,
SELinux, trwałych ACL i utraty zasilania. Wklejony wynik C nie zawierał
wersji Pythona/jądra, SHA checkoutu ani wyjścia self-testu; nie dopisujemy ich
na podstawie pamięci wcześniejszych sesji.
D/E/F/G/H/I/J/K nie mają wyników operatora na Fedorze. Ogólny lokalny zestaw statyczny
repozytorium nadal kończy się kodem 1 w niezmienionych testach DNS Guard UDP/TCP;
bieżący przebieg K oraz wcześniejsze J/I i diagnostyczny H odtworzyły ten punkt
zatrzymania. Pierwszy przebieg H
zatrzymał się wcześniej bez wskazania przyczyny; osobny test healthcheck przeszedł
7/7. Wyniki HCC i zdalnego CI oraz opisane nieudane przebiegi lokalne pozostają
osobno opisane w PR i dzienniku.
Poprzedni ZIP z 19
testami jest historyczną wersją V0.14.5A, a nie aktualnym kodem tej gałęzi.

Nie ma czytnika journala, zaufanej tożsamości rzeczywistych zdarzeń, produkcyjnego
magazynu punktu wznowienia, automatycznej retencji, zainstalowanej usługi ani nowego endpointu HCC. Istniejący
nieaktywny fragment Alloy wskazuje pojedynczy plik i nie obsługuje tego modelu
segmentów. Nie podłączaj go do tych narzędzi ani do produkcyjnego Loki.

Scalenie PR, utworzenie trwałego bufora lub zmiana usług Fedora/ASUS wymagają
osobnej, wyraźnej zgody użytkownika. **DEPLOYMENT_GATE=HOLD.**
