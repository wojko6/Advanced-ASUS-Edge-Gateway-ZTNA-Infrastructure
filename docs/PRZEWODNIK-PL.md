# Wdrożenie na ASUS TUF-AX5400 — przewodnik PL

Repozytorium jest przygotowane jako wersja 2.0 projektu portfolio. Nie wgrywaj skryptów w ciemno na router używany zdalnie — pierwsze zastosowanie reguł wykonaj z komputera podłączonego do LAN i zachowaj dostęp do panelu Merlin.

## 1. Przygotowanie

W Asuswrt-Merlin włącz obsługę własnych skryptów JFFS. Upewnij się, że `/opt` jest poprawnie montowane, Entware działa, a potrzebne pakiety są dostępne:

```sh
mount | grep ' /opt '
opkg list-installed | grep -E '^(tailscale|unbound|syslog-ng) '
```

Nazwy pakietów mogą zależeć od architektury i repozytorium Entware, dlatego instalator projektu celowo nie instaluje ich automatycznie.

## 2. Konfiguracja projektu

```sh
cp config/edge.conf.example config/edge.conf
vi config/edge.conf
```

Najważniejsze pola:

- `EDGE_ADMIN_TS_SOURCES` — stałe adresy Tailscale urządzeń administracyjnych, np. `100.70.10.20/32`;
- `EDGE_ALLOWED_LAN_HOSTS` — wyłącznie hosty LAN udostępniane zdalnie;
- `EDGE_ALLOWED_LAN_TCP_PORTS` i `EDGE_ALLOWED_LAN_UDP_PORTS` — tylko wymagane porty;
- `EDGE_ENABLE_EXIT_NODE` — `1`, jeśli router ma działać jako exit node;
- `EDGE_WAN_IF` — pozostaw puste dla autodetekcji; ustaw ręcznie, jeżeli healthcheck pokaże błąd.
- `EDGE_TS_SOCKET` — musi odpowiadać ścieżce socketu używanej przez lokalny `tailscaled`.

Przykład dostępu do NAS wyłącznie po HTTPS:

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

Najpierw zainstaluj bez uruchamiania nowych reguł:

```sh
./scripts/install.sh
```

Skrypt zapisuje istniejące hooki `firewall-start` i `services-start`, a następnie tworzy wrapper uruchamiający stary hook oraz kod projektu. Lokalizacja kopii jest wyświetlana po instalacji.

Jeżeli Tailscale nie jest jeszcze uwierzytelniony, zrób to jednorazowo interaktywnie. Nie zapisuj auth key w repozytorium.

Zmień przykładową politykę `config/tailscale/policy.example.hujson`: podstaw prawdziwe konta, adresy hostów oraz grupy. Zastosuj ją w panelu Tailscale i zatwierdź reklamowaną trasę/exit node.

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

Łańcuchy IPv6 domyślnie blokują nowe połączenia z `tailscale0`, aby IPv6 nie omijało granularnej polityki IPv4.

## 6. Unbound i dnsmasq

Na routerze port LAN `53` jest zwykle zajęty przez dnsmasq. Unbound z przykładu nasłuchuje na `127.0.0.1:53535`, a dnsmasq przekazuje do niego zapytania. Scal `dnsmasq.conf.add.example` z istniejącą konfiguracją; nie nadpisuj jej bez sprawdzenia.

```sh
unbound-checkconf /opt/etc/unbound/unbound.conf
service restart_dnsmasq
dig +dnssec @192.168.50.1 cloudflare.com A
```

## 7. Test bezpieczeństwa

Z uprawnionego klienta Tailscale:

```sh
sh tests/test-live-client.sh 192.168.50.1 192.168.50.20
```

Następnie wykonaj macierz z `docs/testing.md` dla konta administratora i zwykłego użytkownika. Porównaj wyniki z licznikami iptables oraz capture'ami `tcpdump`.

## 8. Backup i cofnięcie zmian

```sh
./scripts/backup.sh /opt/backups/asus-edge
./scripts/restore.sh PLIK.tar.gz --dry-run
./scripts/uninstall.sh
```

`uninstall.sh` usuwa aktywne łańcuchy projektu i przywraca poprzednie hooki, jeśli zostały znalezione. Konfiguracja i kopie pozostają na urządzeniu do ręcznej decyzji.

## 9. Materiał do portfolio

Po testach dodaj do repozytorium wyłącznie zanonimizowane dowody:

- tabelę oczekiwany/rzeczywisty wynik reguł;
- liczniki iptables przed i po teście;
- wykres opóźnień i przepustowości direct/subnet/exit node;
- wersje firmware i usług;
- zrzuty dashboardu logów bez adresów publicznych, tokenów i danych prywatnych.

To odróżni projekt konfiguracyjny od udokumentowanego projektu Network Security Engineering.
