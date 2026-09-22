# Wdrożenie na ASUS TUF-AX5400

Ten przewodnik opisuje pierwsze, kontrolowane wdrożenie projektu na Asuswrt-Merlin. Pierwsze zastosowanie reguł wykonaj z komputera podłączonego do LAN i zachowaj dostęp do panelu routera.

> **Status referencyjnego routera:** obserwacja niezmienionego stanu została zakończona **2026-09-22** po ciągłej pracy od 2026-09-11 do 2026-09-22. Poniższe polecenia wykonuj wyłącznie podczas kontrolowanego wdrożenia lub okna serwisowego, z aktualnym backupem, drogą rollbacku i walidacją po zmianie. Sukces testów repozytorium/CI nie oznacza automatycznie, że dana zmiana została wdrożona na referencyjnym ASUS-ie.

## 1. Przygotowanie routera

Włącz obsługę własnych skryptów JFFS. Sprawdź montowanie `/opt`, Entware i wymagane pakiety:

```sh
mount | grep ' /opt '
opkg list-installed | grep -E '^(tailscale|unbound|syslog-ng) '
```

Instalator projektu nie instaluje ani nie aktualizuje pakietów.

## 2. Konfiguracja

```sh
cp config/edge.conf.example config/edge.conf
vi config/edge.conf
```

Ustaw przede wszystkim:

- `EDGE_ADMIN_TS_SOURCES` — adresy Tailscale urządzeń administracyjnych, np. `100.70.10.20/32`;
- `EDGE_ALLOWED_LAN_HOSTS` — adresy IPv4 lub CIDR hostów/sieci LAN dostępnych zdalnie; nazwy DNS nie są tu rozwiązywane;
- `EDGE_ALLOWED_LAN_TCP_PORTS` i `EDGE_ALLOWED_LAN_UDP_PORTS` — wymagane porty;
- `EDGE_ENABLE_EXIT_NODE` — `1` tylko wtedy, gdy router ma być exit node;
- `EDGE_WAN_IF` — pozostaw puste dla autodetekcji lub ustaw interfejs wskazany przez router;
- `EDGE_TS_SOCKET` — ścieżkę socketu lokalnego procesu `tailscaled`;
- `EDGE_UNBOUND_PORT` — port loopback zgodny z konfiguracją Unbound, domyślnie `53535`;
- `EDGE_REQUIRE_SWAP` — pozostaw `auto`, ustaw `1`, jeśli dane wdrożenie bezwzględnie wymaga aktywnego swapu przed startem Tailscale, albo `0`, aby wyłączyć ten warunek. W trybie `auto` skrypt wymaga swapu na platformach niskopamięciowych objętych ochroną przy rygorystycznym `vm.overcommit_memory=2`; mechanizm nie zależy od tego, czy swap znajduje się na SSD, flashu czy innym odpowiednim nośniku;
- `EDGE_SWAP_WAIT_SECONDS` — czas oczekiwania na wymagany swap przed startem Tailscale.

Każdy port z listy zostanie udostępniony każdemu hostowi z listy. Jeżeli hosty wymagają różnych zestawów usług, potrzebne są osobne reguły/łańcuchy.

Przykład dostępu do jednego serwera HTTPS:

```sh
EDGE_ADMIN_TS_SOURCES="100.70.10.20/32"
EDGE_ALLOWED_LAN_HOSTS="192.168.50.10"
EDGE_ALLOWED_LAN_TCP_PORTS="443"
EDGE_ALLOWED_LAN_UDP_PORTS=""
```

## 3. Test przed instalacją

```sh
chmod +x scripts/*.sh router/scripts/* tests/*.sh tests/mocks/*
sh tests/test-static.sh
```

## 4. Instalacja etapowa

Najpierw zainstaluj pliki bez aktywowania nowej polityki firewalla:

```sh
./scripts/install.sh
```

To nie jest całkowicie pasywny „dry-run”. Instalator zapisuje snapshot ścieżek, które zmienia, kopiuje konfigurację i zarządzane binaria do JFFS oraz instaluje wrappery `firewall-start`, `services-start` i `wan-event`. Bez `--apply` nie wywołuje jednak nowej polityki firewalla w bieżącej sesji. Istniejące niezarządzane hooki są zachowywane pod katalogiem `legacy` i domyślnie wyłączone; wrapper uruchomi stary hook tylko po ustawieniu `EDGE_RUN_LEGACY_HOOKS="1"`, co należy zrobić wyłącznie po ręcznym przeglądzie. Lokalizacja kopii jest wyświetlana po instalacji.

Jeżeli którykolwiek etap instalacji plików/hooków się nie powiedzie, instalator próbuje odtworzyć cały snapshot i kończy się błędem. W trybie bez `--apply` nie wykonuje restartu firewalla, ponieważ polityka nie została jeszcze zastosowana. Zachowaj dostęp lokalny/LAN również na tym etapie, ponieważ zainstalowane hooki zaczną uczestniczyć w odpowiednich przyszłych zdarzeniach firmware'u.

Jeżeli Tailscale nie jest uwierzytelniony, uruchom jednorazowo:

```sh
tailscale --socket=/var/run/tailscale/tailscaled.sock up \
  --netfilter-mode=off \
  --accept-dns=false \
  --advertise-routes=192.168.50.0/24 \
  --advertise-exit-node
```

`--netfilter-mode=off` jest celowy: politykę routera egzekwują łańcuchy `EDGE_TS_*`, a nie równoległe reguły `ts-*` zarządzane przez Tailscale. Pomiń `--advertise-exit-node`, jeżeli `EDGE_ENABLE_EXIT_NODE="0"`. Dostosuj `config/tailscale/policy.example.hujson`, opublikuj politykę i zatwierdź tylko wymaganą trasę lub exit node w panelu Tailscale.

## 5. Zastosowanie firewalla

Poniższe wykonuj z LAN wyłącznie podczas pierwszego wdrożenia, zaplanowanego maintenance albo odzyskiwania po awarii:

```sh
./scripts/install.sh --apply
/jffs/addons/asus-edge/bin/healthcheck.sh
```

`--apply` ponownie wykonuje instalację/snapshot, a następnie uruchamia zarządzany hook `firewall-start`; nie jest to osobny tryb, który jedynie stosuje wcześniej skopiowane pliki. Jeżeli zastosowanie firewalla zawiedzie, instalator odtwarza snapshot i — tylko gdy rollback plików się powiedzie — próbuje `service restart_firewall`, aby wrócić do polityki firmware'u. Nie traktuj tego jako gwarantowanego zdalnego rollbacku: błąd odtwarzania lub restartu wymaga lokalnego dostępu i ręcznej weryfikacji.

Sprawdź reguły i liczniki:

```sh
iptables -nvL EDGE_TS_INPUT
iptables -nvL EDGE_TS_FORWARD
iptables -t nat -nvL EDGE_TS_PREROUTING
ip6tables -nvL EDGE_TS6_INPUT
ip6tables -nvL EDGE_TS6_FORWARD
```

Łańcuchy IPv6 domyślnie blokują nowe połączenia z `tailscale0`, aby ruch IPv6 nie omijał granularnej polityki IPv4.

## 6. Unbound i dnsmasq

dnsmasq pozostaje usługą nasłuchującą na porcie `53` dla LAN i `tailscale0`. Unbound nasłuchuje wyłącznie na `127.0.0.1:53535`.

Dla standardowej instalacji Entware:

```sh
cp config/unbound.conf.example /opt/etc/unbound/unbound.conf
unbound-checkconf /opt/etc/unbound/unbound.conf
```

Jeżeli używasz amtm Unbound Manager, nie nadpisuj generowanego pliku runtime. Sprawdź konfigurację zarządzaną przez dodatek. Restart poniżej jest działaniem serwisowym i powinien być wykonywany wyłącznie podczas zaplanowanego maintenance albo gdy jest potrzebny do odzyskania usługi:

```sh
grep -E '^(port: 53535|interface: 127\.0\.0\.1@53535)' /opt/var/lib/unbound/unbound.conf
unbound-checkconf /opt/var/lib/unbound/unbound.conf
/opt/etc/init.d/S61unbound restart
```

Następnie zweryfikuj resolver:

```sh
dig +dnssec -p 53535 @127.0.0.1 cloudflare.com A
```

Jeżeli `/jffs/configs/dnsmasq.conf.add` już istnieje, scal `config/dnsmasq.conf.add.example` zamiast nadpisywać prywatne rekordy DDNS lub lokalne. Aktywna konfiguracja musi zawierać `interface=tailscale0`; dzięki `bind-dynamic` dnsmasq obsłuży adres interfejsu po jego utworzeniu. Po scaleniu, podczas zaplanowanego wdrożenia/maintenance, uruchom `service restart_dnsmasq` i potwierdź wpis w `/etc/dnsmasq.conf`. Jeżeli w przyszłości zostanie ogłoszona nowa obserwacja niezmienionego stanu, jej ograniczenia muszą być zapisane w aktualnym `PROJECT-STATUS.md`. Sprawdź również `/jffs/scripts/dnsmasq.postconf`: aktywny hook innego resolvera może zakończyć skrypt przed konfiguracją Unbound lub przejąć klasyczny ruch DNS; nie zakładaj konkretnego portu bez sprawdzenia bieżącej konfiguracji.

## 7. Test dostępu

Z uprawnionego urządzenia administracyjnego uruchom test, wskazując adres zarządzający routera i opcjonalny host LAN, na którym SMB powinno być zablokowane:

```sh
sh tests/test-live-client.sh 192.168.50.1 192.168.50.20
```

Następnie wykonaj macierz z [testing.md](testing.md) dla urządzenia administratora i zwykłego użytkownika. Porównaj wyniki z licznikami iptables i, jeżeli jest to rzeczywiście potrzebne, z krótkim kontrolowanym przechwyceniem ruchu. Preferuj istniejące logi i odczytowe liczniki, gdy wystarczają do odpowiedzi na pytanie testowe; nowe mechanizmy telemetryczne traktuj jako osobną zmianę serwisową.

## 8. Backup i wycofanie zmian

Poniższe polecenia są przeznaczone dla zaplanowanego maintenance lub odzyskiwania:

```sh
./scripts/backup.sh /opt/backups/asus-edge
./scripts/restore.sh PLIK.tar.gz --dry-run
./scripts/uninstall.sh
```

`uninstall.sh` usuwa aktywne łańcuchy projektu i przywraca poprzednie hooki, jeżeli zostały zapisane. Konfiguracja i kopie zapasowe pozostają na urządzeniu do ręcznej weryfikacji.
