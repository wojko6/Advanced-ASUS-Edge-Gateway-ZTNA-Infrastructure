# RouterCloud — versioned encrypted backups

Issue: #138

## Cel

RouterCloud przechowuje dane live na SSD routera ASUS. Sam rsync nie zapewnia
historii wersji, dlatego druga warstwa backupu działa poza routerem na Fedorze.

Architektura:

~~~text
ASUS RouterCloud live data
        |
        | restricted read-only rsync over SSH
        v
Fedora staging mirror
        |
        | restic
        v
encrypted repository on separate local SSD
~~~

Staging jest tylko roboczym lustrem. Nie jest backupem.

## Granice bezpieczeństwa

Backup używa osobnego klucza SSH przeznaczonego wyłącznie do odczytu
RouterCloud.

Po stronie routera klucz jest ograniczony forced-commandem do dokładnego
kontraktu rsync `--server --sender` i katalogu RouterCloud.

Klucz backupowy nie może:

- uruchamiać dowolnych poleceń SSH;
- odczytywać katalogów poza RouterCloud;
- wysyłać plików na router;
- usuwać plików z RouterCloud.

`rsync --delete` jest używany wyłącznie po stronie lokalnego stagingu, aby
odzwierciedlać usunięcia z live RouterCloud. Nie daje to prawa usuwania danych
na routerze.

## Lokalizacje domyślne

~~~text
staging:
  ~/.local/state/routercloud-backup/staging

restic repository:
  /mnt/dysk-lokalny/backups/routercloud-restic

restic password file:
  ~/.config/routercloud-backup/restic-password

backup status:
  ~/.local/state/routercloud-backup/status.env

maintenance status:
  ~/.local/state/routercloud-backup/maintenance-status.env
~~~

Opcjonalne ustawienia deploymentu mogą znajdować się w:

~~~text
~/.config/routercloud-backup.env
~~~

Przykład:

~~~text
monitoring/config/routercloud-backup.env.example
~~~

Hasła restic nie wolno przechowywać w repozytorium.

## Harmonogram

Automatyczny backup: **codziennie o 21:30 czasu lokalnego Fedory**.

~~~text
21:30
~~~

Zmiana harmonogramu została wykonana na Fedorze 2026-10-14 przez lokalny drop-in systemd (`~/.config/systemd/user/routercloud-backup.timer.d/90-routercloud-2130.conf`). Walidacja operacyjna wykazała `ISSUE235_BACKUP_SCHEDULE=PASS` i następny termin 2026-10-14 21:30 CEST; **rzeczywisty harmonogramowy backup po zmianie uprawnień SSD zakończył się PASS 2026-10-14 o 21:30:03+02:00** (`LAST_RESULT=success`, `LAST_RC=0`, `LAST_STAGE=complete`); osobnego identyfikatora nowego snapshotu restic nie utrwalono w tym raporcie. Po aktualizacji jednostki z repozytorium należy upewnić się, że lokalny drop-in nie wymusza sprzecznego harmonogramu; nie usuwać go bez uprzedniej kontroli `systemctl --user cat routercloud-backup.timer` oraz `systemctl --user list-timers --all routercloud-backup.timer`.

Timer:

~~~text
routercloud-backup.timer
~~~

Konserwacja repozytorium:

~~~text
Sunday 03:30
~~~

Timer:

~~~text
routercloud-backup-maintenance.timer
~~~

Oba timery używają `Persistent=true`.

User systemd ma działać również po starcie systemu bez interaktywnego logowania:

~~~bash
loginctl show-user "$USER" -p Linger
~~~

Oczekiwane:

~~~text
Linger=yes
~~~

## Polityka retencji

Retencja dotyczy snapshotów oznaczonych tagiem `scheduled`.

~~~text
all snapshots within newest 48h
14 daily
8 weekly
12 monthly
3 yearly
~~~

Snapshoty dowodowe z testów #138 nie są objęte tą polityką.

## Integralność repozytorium

Cotygodniowa konserwacja wykonuje:

~~~bash
restic forget --prune
restic check --read-data
~~~

`check --read-data` weryfikuje również faktyczne packi danych.

## Lista snapshotów

~~~bash
REPO="/mnt/dysk-lokalny/backups/routercloud-restic"
PASSFILE="$HOME/.config/routercloud-backup/restic-password"

restic \
  --repo "$REPO" \
  --password-file "$PASSFILE" \
  snapshots
~~~

## Przywrócenie pojedynczego pliku

Najpierw wybierz właściwy snapshot.

Restore wykonuj do izolowanego katalogu lokalnego:

~~~bash
REPO="/mnt/dysk-lokalny/backups/routercloud-restic"
PASSFILE="$HOME/.config/routercloud-backup/restic-password"

SNAPSHOT="<snapshot-id>"
TARGET="$HOME/routercloud-restore"
SOURCE_PATH="/home/USER/.local/state/routercloud-backup/staging/path/to/file"

mkdir -p "$TARGET"
chmod 700 "$TARGET"

restic \
  --repo "$REPO" \
  --password-file "$PASSFILE" \
  restore "$SNAPSHOT" \
  --target "$TARGET" \
  --include "$SOURCE_PATH"
~~~

Przed ponownym umieszczeniem pliku w RouterCloud należy zweryfikować jego
zawartość oraz, jeśli dostępny, SHA256.

## Przywrócenie pełnego katalogu

~~~bash
REPO="/mnt/dysk-lokalny/backups/routercloud-restic"
PASSFILE="$HOME/.config/routercloud-backup/restic-password"

SNAPSHOT="<snapshot-id>"
TARGET="$HOME/routercloud-full-restore"

mkdir -p "$TARGET"
chmod 700 "$TARGET"

restic \
  --repo "$REPO" \
  --password-file "$PASSFILE" \
  restore "$SNAPSHOT" \
  --target "$TARGET"
~~~

Testowego restore nie należy wykonywać bezpośrednio nad live RouterCloud.

## Recovery po przypadkowym nadpisaniu lub usunięciu

1. Wybrać snapshot sprzed zdarzenia.
2. Odtworzyć wymagany plik lub katalog do izolowanego katalogu.
3. Zweryfikować dane i hash.
4. Dopiero potem przenieść odzyskane dane do właściwego workflow RouterCloud.

Historia restic pozostaje niezależna od aktualnego stanu stagingu.

## Status backupu

~~~bash
systemctl --user status routercloud-backup.timer
systemctl --user status routercloud-backup.service
cat ~/.local/state/routercloud-backup/status.env
~~~

## Status maintenance

~~~bash
systemctl --user status routercloud-backup-maintenance.timer
systemctl --user status routercloud-backup-maintenance.service
cat ~/.local/state/routercloud-backup/maintenance-status.env
~~~

## Coarse observability

Do lokalnej VictoriaMetrics publikowane są wyłącznie:

~~~text
routercloud_backup_last_run_success
routercloud_backup_last_run_timestamp_seconds
routercloud_backup_last_duration_seconds
routercloud_backup_last_rc

routercloud_maintenance_last_run_success
routercloud_maintenance_last_run_timestamp_seconds
routercloud_maintenance_last_duration_seconds
routercloud_maintenance_last_rc
~~~

Nie są publikowane:

- nazwy plików;
- zawartość RouterCloud;
- prywatne dane użytkownika;
- hasła;
- klucze SSH;
- tokeny.

Publikacja metryk jest best-effort. Awaria VictoriaMetrics nie może spowodować
niepowodzenia właściwego backupu lub maintenance.

## Alerting Grafana

Stan backupu i maintenance jest oceniany poza routerem przez Grafanę na Fedorze.
Źródłem pozostają wyłącznie powyższe metryki coarse-grained.

Provisioning zawiera cztery reguły:

- `routercloud_backup_bad` — ostatni wynik backupu jest nieudany; `for: 1m`;
- `routercloud_backup_stale` — wiek ostatniego backupu przekracza 26 godzin (backup raz dziennie o 21:30 + 2 godziny marginesu); `for: 5m`;
- `routercloud_maintenance_bad` — ostatni maintenance/integrity check jest nieudany; `for: 1m`;
- `routercloud_maintenance_stale` — wiek ostatniego maintenance przekracza 8 dni; `for: 30m`.

**Granica źródło → produkcja (stan udokumentowany 2026-10-14):** zmiana na harmonogram dzienny `21:30` działała na Fedorze z lokalnego drop-in. Repozytorium (scalone [PR #250](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/250)) publikuje odpowiadające mu `OnCalendar`, ale **nie uruchamia ani nie przeładowuje systemd/Grafany**. W ostatniej udokumentowanej kontroli uruchomiony alert `routercloud_backup_stale` nadal używał **8h/24h**. Na dysku Fedora miał już oddzielnie przygotowany plik `26h/48h`, lecz `GRAFANA_RELOADED=NO`. Scalenie PR #250 nie zawiera nowego odczytu produkcyjnego Grafany po 14 października. Przed jakąkolwiek kontrolowaną aktywacją osobno sprawdzić dane live przez API/UI oraz konfigurację Email+Telegram, 15 reguł, brak obcych zmian i prywatny rollback. Nie stosować surowej repozytoryjnej konfiguracji kontaktowej Email-only jako zamiennika dla produkcyjnego Email+Telegram. [Dziennik 14 października](worklog/2026-10-14.md); [Issue #236](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/236).

**Okno metryk:** zarówno alarm `routercloud_backup_bad`, jak i `routercloud_backup_stale` analizują obecnie (źródłowo) ostatnie **48h** timestampu/rezultatu. Utrzymuje to informację o nieudanym backupie także między 24. a 26. godziną po ostatnim wyniku; ustawienie `noDataState: OK` w `*_bad` nie jest zastępnikiem alarmu `*_stale`. Dashboard używa 30-dniowego lookback, a `93600` sekund odpowiada 26h. Sprawność powiadomień po przyszłym provisioningu wymaga osobnego testu; samo `git merge` niczego nie aktywuje.

**Ochrona punktu odtworzenia:** przejście z czterech kopii na dobę do jednej oznacza zwykle około **24h** odstępu między poprawnymi kopiami zamiast **6h**. `Persistent=true` może nadrobić pominięte uruchomienie po powrocie Fedory, ale nie gwarantuje powodzenia kopii, gdy ASUS/SSD nie są dostępne.

Reguły `*_bad` używają `noDataState: OK`, ponieważ brak historii jest
obsługiwany osobno przez reguły `*_stale`. Reguły staleness używają
`noDataState: Alerting`, ponieważ brak świeżej próbki jest sam w sobie sygnałem
problemowym.

Wszystkie cztery reguły są częścią **15-regułowego** baseline Grafany i
routują do istniejącego kontaktu `ASUS Edge Gateway Email`. Dane SMTP pozostają
poza repozytorium.

2026-10-07 wykonano kontrolowany live E2E dla
`routercloud_backup_bad`: syntetyczny stan failure doprowadził regułę do
`Firing`, następnie przywrócono rzeczywistą zdrową metrykę z `status.env`, a
Grafana wróciła do stanu bez aktywnej instancji. Test nie jest elementem zwykłego
CI, ponieważ celowo modyfikuje lokalną metrykę i może uruchomić realne
powiadomienie.

Zobacz:
- [monitoring Grafana alerting](../monitoring/README.md#grafana-alerting);
- [sanitized live validation](../evidence/2026-10-07/grafana-routercloud-alerting-live-validation.md);
- `tests/test-grafana-routercloud-alerting-live.sh`.


## Fail-closed

Backup i maintenance odmawiają działania, jeżeli:

- osobny SSD nie jest zamontowany;
- plik hasła restic jest niedostępny;
- oczekiwane repozytorium restic nie istnieje.

Chroni to między innymi przed przypadkowym utworzeniem repozytorium na
systemowym filesystemie w przypadku braku mountu SSD.

## Zweryfikowane acceptance tests

Na fizycznym środowisku Fedora + ASUS TUF-AX5400 potwierdzono:

- read-only transport ASUS -> Fedora staging;
- brak możliwości arbitrary SSH dla klucza backupowego;
- brak możliwości odczytu ścieżek poza RouterCloud;
- brak możliwości zapisu na router przez klucz backupowy;
- staging mirror z lokalnym `--delete`;
- zaszyfrowane repozytorium restic;
- snapshot bazowy;
- snapshot V1;
- restore V1 po późniejszym nadpisaniu;
- snapshot V2;
- restore V2 po późniejszym usunięciu;
- snapshot stanu po usunięciu;
- pełny restore katalogu do izolowanej lokalizacji;
- zgodność SHA256 odzyskanych wersji;
- jawna polityka retencji;
- `forget --prune`;
- `restic check --read-data`;
- brak błędów integralności;
- automatyczny backup przez systemd;
- cotygodniowy maintenance;
- trwałość timerów i mountu po restarcie Fedory;
- poprawny backup po restarcie;
- coarse metrics w VictoriaMetrics.

## Zweryfikowane snapshoty testowe

~~~text
baseline:
  1b8bcaf7

V1:
  bc600eaf

V2:
  78a0880c

deleted state:
  49ea11cd
~~~

Hash odzyskanej V1:

~~~text
1754f04f52c765d8dbdf662becfa53edbdddab429a052d538a8bd333134104a4
~~~

Hash odzyskanej V2:

~~~text
244ef6189939f605bb337b31df53928459ddb2e08dbbe2285b9f641bbfe381ad
~~~

## Ważne ograniczenie

Utrata hasła restic oznacza utratę możliwości odszyfrowania backupu.

Kopia hasła powinna istnieć poza komputerem wykonującym backup, np. w
zaufanym menedżerze haseł lub innym bezpiecznym miejscu.

Hasło, prywatne klucze SSH oraz zawartość backupu nie należą do publicznego repozytorium.
