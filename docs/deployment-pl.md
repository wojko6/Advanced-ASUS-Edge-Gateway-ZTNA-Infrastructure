# Wdrożenie na ASUS TUF-AX5400

Ten przewodnik opisuje pierwsze, kontrolowane wdrożenie projektu na Asuswrt-Merlin. Pierwsze zastosowanie reguł wykonaj z komputera podłączonego do LAN i zachowaj dostęp do panelu routera.

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
- `EDGE_ALLOWED_LAN_HOSTS` — hosty LAN dostępne zdalnie;
- `EDGE_ALLOWED_LAN_TCP_PORTS` i `EDGE_ALLOWED_LAN_UDP_PORTS` — wymagane porty;
- `EDGE_ENABLE_EXIT_NODE` — `1` tylko wtedy, gdy router ma być exit node;
- `EDGE_WAN_IF` — pozostaw puste dla autodetekcji lub ustaw interfejs wskazany przez router;
- `EDGE_TS_SOCKET` — ścieżkę socketu lokalnego procesu `tailscaled`.
- `EDGE_UNBOUND_PORT` — port loopback zgodny z konfiguracją Unbound, domyślnie `53535`.

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

Najpierw zainstaluj pliki bez aktywowania nowych reguł:

```sh
./scripts/install.sh
```

Skrypt zapisuje istniejące hooki `firewall-start` i `services-start`, ale domyślnie ich nie uruchamia. Wrapper uruchomi stary hook tylko po ustawieniu `EDGE_RUN_LEGACY_HOOKS="1"`, co należy zrobić wyłącznie po ręcznym przeglądzie. Lokalizacja kopii jest wyświetlana po instalacji.

Jeżeli Tailscale nie jest uwierzytelniony, uruchom jednorazowo:

```sh
tailscale --socket=/var/run/tailscale/tailscaled.sock up \
  --accept-dns=false \
  --advertise-routes=192.168.50.0/24 \
  --advertise-exit-node
```

Pomiń `--advertise-exit-node`, jeżeli `EDGE_ENABLE_EXIT_NODE="0"`. Dostosuj `config/tailscale/policy.example.hujson`, opublikuj politykę i zatwierdź tylko wymaganą trasę lub exit node w panelu Tailscale.

## 5. Zastosowanie firewalla

Pozostając w LAN:

```sh
./scripts/install.sh --apply
/jffs/addons/asus-edge/bin/healthcheck.sh
```

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

dnsmasq pozostaje usługą nasłuchującą na porcie LAN `53`. Unbound nasłuchuje wyłącznie na `127.0.0.1:53535`.

Dla standardowej instalacji Entware:

```sh
cp config/unbound.conf.example /opt/etc/unbound/unbound.conf
unbound-checkconf /opt/etc/unbound/unbound.conf
```

Jeżeli używasz amtm Unbound Manager, nie nadpisuj generowanego pliku runtime. Sprawdź konfigurację zarządzaną przez dodatek:

```sh
grep -E '^(port: 53535|interface: 127\.0\.0\.1@53535)' /opt/var/lib/unbound/unbound.conf
unbound-checkconf /opt/var/lib/unbound/unbound.conf
/opt/etc/init.d/S61unbound restart
```

Następnie zweryfikuj resolver:

```sh
dig +dnssec -p 53535 @127.0.0.1 cloudflare.com A
```

Jeżeli `/jffs/configs/dnsmasq.conf.add` już istnieje, scal `config/dnsmasq.conf.add.example` zamiast nadpisywać prywatne rekordy DDNS lub lokalne. Sprawdź również `/jffs/scripts/dnsmasq.postconf`: aktywny hook NextDNS może zakończyć skrypt przed konfiguracją Unbound i przejąć ruch na port `5342`.

## 7. Test dostępu

Z uprawnionego urządzenia administracyjnego uruchom test, wskazując adres zarządzający routera i opcjonalny host LAN, na którym SMB powinno być zablokowane:

```sh
sh tests/test-live-client.sh 192.168.50.1 192.168.50.20
```

Następnie wykonaj macierz z [testing.md](testing.md) dla urządzenia administratora i zwykłego użytkownika. Porównaj wyniki z licznikami iptables i przechwyconym ruchem.

## 8. Backup i wycofanie zmian

```sh
./scripts/backup.sh /opt/backups/asus-edge
./scripts/restore.sh PLIK.tar.gz --dry-run
./scripts/uninstall.sh
```

`uninstall.sh` usuwa aktywne łańcuchy projektu i przywraca poprzednie hooki, jeżeli zostały zapisane. Konfiguracja i kopie zapasowe pozostają na urządzeniu do ręcznej weryfikacji.
