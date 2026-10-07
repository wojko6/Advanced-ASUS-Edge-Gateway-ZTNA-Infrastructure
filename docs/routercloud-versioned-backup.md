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

Automatyczny backup:

~~~text
00:00
06:00
12:00
18:00
~~~

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
- `routercloud_backup_stale` — wiek ostatniego backupu przekracza 8 godzin; `for: 5m`;
- `routercloud_maintenance_bad` — ostatni maintenance/integrity check jest nieudany; `for: 1m`;
- `routercloud_maintenance_stale` — wiek ostatniego maintenance przekracza 8 dni; `for: 30m`.

Reguły `*_bad` używają `noDataState: OK`, ponieważ brak historii jest
obsługiwany osobno przez reguły `*_stale`. Reguły staleness używają
`noDataState: Alerting`, ponieważ brak świeżej próbki jest sam w sobie sygnałem
problemowym.

Wszystkie cztery reguły są częścią dziewięcioregułowego baseline Grafany i
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
