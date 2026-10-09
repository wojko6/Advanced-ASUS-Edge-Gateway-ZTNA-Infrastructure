# ASUS TUF-AX5400 — procedura awaryjna od pustego routera i SSD

**Dokument operacyjny / Issue [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)**  
**Stan na 2026-10-09:** procedura przygotowana i oparta na prawdziwych backupach oraz testach cząstkowych; **pełne odtworzenie od zera NIEZALICZONE**.  
**Nie wykonywać na zdrowym routerze produkcyjnym.** Nie jest to jednoetapowy instalator.

## 0. Scenariusz i warunki bezpieczeństwa

Przyjmujemy najtrudniejszy wariant: sprawny sprzęt ASUS TUF-AX5400, po resecie do ustawień fabrycznych, pusty nośnik SSD/JFFS bez pakietów Entware i bez działających Pi-hole, Unbound, DNS Guard i Tailscale. Dane ratunkowe są na oddzielnej Fedorze lub zaszyfrowanym nośniku offline.

Inna awaria:
- **Tylko utrata konfiguracji ASUS/NVRAM:** po zweryfikowaniu zgodności modelu i firmware można rozważyć natywny eksport CFG; nie trzeba automatycznie formatować działającego SSD.
- **Tylko uszkodzenie SSD:** nie resetować sprawnego NVRAM/JFFS; odtwarzać magazyn i usługi.
- **Uszkodzony firmware / router nie uruchamia panelu:** najpierw właściwa, zweryfikowana dla modelu procedura firmware recovery. Przywracanie plików Entware nie naprawi niedziałającego bootloadera.
- **Zapasowy router:** podłączać do **odizolowanej sieci testowej**. Dwa urządzenia z adresem bramy i aktywnym DHCP nie mogą jednocześnie obsługiwać tej samej sieci.

**Ochrona dostępu:** fizyczny dostęp, laptop na Ethernet, lokalna możliwość zalogowania do WebUI, zapisane metody odzyskania dostępu. Nie uzależniać działań ratunkowych od Tailscale ani Pi-hole. Nie wyłączać reguł ochronnych ani nie otwierać administracji z WAN tylko dla wygody.

**Reguła:** wykonujemy jedną zmianę infrastrukturalną, sprawdzamy bramkę PASS/STOP, dopiero potem następną. Nie używać `reboot`, `nvram commit`, `mkfs`, `mkswap`, `setcap`, `restore.sh --apply`, `install.sh` ani `service restart_wan` na istniejącym zdrowym urządzeniu „dla testu”.

## 1. Zestaw ratunkowy — przygotowany **przed** awarią

| Artefakt / narzędzie | Źródło / wymaganie | Ograniczenie |
|---|---|---|
| ASUS Edge CORE | zaszyfrowane `asus-edge-*.tar.gz.gpg` i sidecar SHA-256, off-router | odtwarza tylko wybrane pliki projektu, nie system/Entware |
| Pi-hole DR | `pihole-dr-*-verified.tar.gz.gpg` i sidecar | 15 plików + 4 manifesty, bez pełnej instalacji pakietów |
| Firmware CFG | natywny `Settings_TUF-AX5400-*.CFG.gpg` i sidecar | przywrócenie CFG na czystym firmware nieprzetestowane |
| Źródło projektu | konkretny, zweryfikowany commit/release projektu + opcjonalna kopia offline | `main` może ewoluować; nie instalować przypadkowej przyszłej wersji |
| Obrazy i pakiety | sprawdzony obraz zgodnego GNUton/Merlin, offline lub dostępny repozytorium Entware, właściwe pakiety ARMv7, manifest wersji/hashy | **sam backup nie zapewnia** firmware ani wszystkich pakietów |
| Narzędzia Fedora | GPG, sha256sum, tar, Python/SQLite, SSH, prywatny tmpfs, nośnik offline | hasła/klucze prywatne nie trafiają do repo |
| Plan LAN | adresy IP, zależności DHCP/DNS, urządzenie administracyjne, WAN ISP | dane poufne przechowywać osobno od publicznego runbooka |

**Wymagane źródła referencyjne:** [DR baseline](router-disaster-recovery.md), [generator Pi-hole](pihole-dr-generator.md), [manifest odbudowy](../scripts/collect-dr-manifest.sh), [architektura startu](architecture/boot-service-dependency-flow.md), [model SSD](ENTWARE-SSD-MIGRATION.md), [wdrożenie projektu](deployment-pl.md).

### Kontrola backupów na Fedorze (tylko odczyt)

Przykład dla trzech aktualnie zweryfikowanych archiwów; po rotacji backupów zastąpić nazwami z prywatnego rejestru:

```bash
set -e
BACKUPS="$HOME/Archiwa/ASUS-Edge-Issue-129"
for NAME in \
  pihole-dr-20261009-121026-verified.tar.gz.gpg \
  asus-edge-20261009-112140.tar.gz.gpg \
  Settings_TUF-AX5400-20261009-113811.CFG.gpg
do
    test -f "$BACKUPS/$NAME"
    test -f "$BACKUPS/$NAME.sha256"
    sha256sum -c "$BACKUPS/$NAME.sha256"
done
```

Nie odczytywać bez potrzeby treści CFG ani konfiguracji zawierających sekrety w terminalu/logu. GPG odszyfrowuje się **tylko w prywatnym tmpfs**, po sprawdzeniu `findmnt -T "$XDG_RUNTIME_DIR" -no FSTYPE` = `tmpfs` i wystarczającej wolnej pamięci. Nie ma obowiązku deszyfrowania wszystkich trzech materiałów w tym samym momencie.

**GATE 0:** każdy wymagany artefakt jest dostępny, zweryfikowany i da się go odszyfrować; kompatybilny firmware i repozytoria/pakiety mają potwierdzone pochodzenie; istnieje niezależny dostęp przez LAN. W przeciwnym razie **STOP**.

## 2. Przywrócenie podstawowego ASUS-a — bez własnych usług DNS

1. Podłącz tylko laptop administracyjny przez kabel; zapasowy router pozostaje poza produkcyjną siecią z aktywnym DHCP. Sprawdź rzeczywisty adres routera i domyślne poświadczenia po konfiguracji początkowej **lokalnie**.
2. Uruchom zgodny firmware GNUton/Asuswrt-Merlin dla **dokładnego modelu TUF-AX5400**. Aktualny referencyjny wariant to `3004.388.11_1-gnuton1_tuf`; nie zgadywać pliku firmware ani automatycznie instalować innej wersji.
3. Skonfiguruj niezbędny WAN, NAT i **działający niezależny DNS dla routera**, aby NTP nie zależał od nieistniejącego jeszcze Pi-hole. DNS otrzymany z WAN musi faktycznie odpowiadać; nie wpisywać w ciemno prywatnego lub niedostępnego resolvera.
4. Przygotuj lokalne konto administracyjne, JFFS custom scripts/configs i ograniczony do LAN dostęp SSH dopiero po ustawieniu odpowiedniej polityki. Po restarcie SSH potwierdź klucz hosta, zamiast wyłączać weryfikację `StrictHostKeyChecking`.
5. **CFG:** importuj wyłącznie po potwierdzeniu zgodności i rozważeniu, które ustawienia mogą od razu włączyć stare skrypty, DHCP, DNS i reguły. Sam import CFG nie jest potwierdzoną procedurą ratunkową. Jeśli nie jest bezpieczny, odbuduj podstawy ręcznie.

**GATE 1:** WebUI dostępne po kablu, działający WAN/IP i niezależne DNS/NTP, JFFS gotowe, podstawowa konfiguracja zapisana, brak nieautoryzowanego zarządzania WAN. Bez tego nie przechodź do Entware ani projektu.

## 3. Odbudowa SSD, swap i Entware

1. Na odłączonym od produkcji urządzeniu zidentyfikuj **konkretny** nośnik (pojemność, identyfikator, układ partycji) i potwierdź, że można zniszczyć jego zawartość. **Nie kopiować z Internetu poleceń `mkfs`/partycjonowania z założonym `/dev/sda`.**
2. Odtwórz sprawdzony układ **GPT / ext4**: partycja `ENTWARE` około 64 GiB oraz `ROUTER_DATA` na pozostałe dane (jeżeli używany dysk pozwala na te wielkości). Montowanie referencyjne `/tmp/mnt/ENTWARE` i `/tmp/mnt/ROUTER_DATA`.
3. Odbuduj Entware z zatwierdzonego źródła, zamontuj `/opt` do właściwego drzewa `/tmp/mnt/ENTWARE/entware`. Przygotuj `opkg` i `/opt/etc/init.d/rc.unslung`, ale **nie włączaj jeszcze nieodtworzonych usług**.
4. Utwórz od nowa **puste** pliki swap, zgodnie ze sprawdzonym układem (~512 MiB na ENTWARE i ~2 GiB na ROUTER_DATA) i możliwościami docelowego nośnika. Nie przenosić zawartości istniejących plików swap jako backupu.
5. Odtwórz / sprawdź AMTM i jego `mount-entware.mod`. Porównaj **tylko referencyjny** `recovery-reference/jffs/scripts/post-mount` z nowym hookiem. Wprowadź ręcznie poprawną kolejność: `swapon` **przed** wywołaniem AMTM `mount-entware.mod`. Historyczny opis migracji 2026-09-11 zawiera **starszą kolejność**, więc nie kopiować go bez porównania do obecnego [diagramu startu](architecture/boot-service-dependency-flow.md).

Kontrole odczytowe na **odbudowywanym** routerze:

```sh
mount | grep -E '/tmp/mnt/(ENTWARE|ROUTER_DATA)'
ls -ld /opt /tmp/mnt/ENTWARE/entware
test -x /opt/bin/opkg && echo 'OPKG=PASS'
test -x /opt/etc/init.d/rc.unslung && echo 'RC_UNSLUNG=PASS'
cat /proc/swaps
sh -n /jffs/scripts/post-mount
awk '/swapon/ && !s {s=NR} /mount-entware\.mod/ && !m {m=NR}
END {print "SWAP_LINE=" s, "ENTWARE_LINE=" m; if (!(s>0 && m>s)) exit 1}' /jffs/scripts/post-mount
```

**GATE 2:** oba właściwe systemy plików zamontowane do odczytu/zapisu, poprawne `/opt`, Entware `opkg`, dwa aktywne swapy i **swap-before-Entware** potwierdzony. W przypadku błędu wstrzymaj usługi zależne od RAM/swap, zwłaszcza Tailscale.

## 4. Pakiety i konta — granica brakującej automatyzacji

Przed odtwarzaniem skryptów odtwórz **zgodne i zaufane pakiety** z prywatnego `packages.txt` oraz manifestów wersji. Nie zakładaj, że każda wersja znajduje się nadal w publicznym feedzie Entware.

Wymagają osobnego potwierdzenia:
- **Unbound**: referencyjne `1.26.1`, środowisko Unbound Manager, zależności i konfiguracja DNSSEC;
- **Pi-hole FTL**: referencyjny ARMv7 FTL `6.7.1`, pakiet `2026.09.20-1`, wymagane narzędzia `setcap/getcap`; sprawdzić sumy binariów i zgodność ABI;
- **Tailscale**: wersja faktycznych binariów może różnić się od metadanych `opkg`, dlatego wymagana kontrola provenance;
- **syslog-ng**, GNU `patch` (instalator WebUI go wymaga) oraz zależności projektu.

Pi-hole wymaga konta **uid=999/gid=999** zgodnie z prywatnym manifestem. Nie tworzyć go ślepo, gdy identyfikatory kolidują z nową instalacją.

**GATE 3:** pakiety, binaria, zależności, użytkownicy/usługi i startup managerów zostały zweryfikowane; **STOP**, jeżeli brakuje artefaktu źródłowego lub binarium odpowiada niewłaściwej architekturze.

## 5. CORE — odzyskiwanie plików projektu

1. Zweryfikuj i odszyfruj prywatny CORE backup na Fedorze do tmpfs. Sprawdź wewnętrzny manifest i dokładną listę archiwum. Nie podawaj zaszyfrowanego `.gpg` bezpośrednio do `restore.sh`.
2. Prawdziwy skrypt [`scripts/restore.sh`](../scripts/restore.sh) przyjmuje **`BACKUP.tar.gz --dry-run|--apply`**. Wcześniej wykazano, że może odtworzyć archiwum do alternatywnego katalogu `EDGE_RESTORE_ROOT` na odizolowanej Fedorze. **Bez tego parametru `--apply` zapisuje bezpośrednio do `/jffs` i `/opt` docelowego routera**.
3. Właściwe odtworzenie CORE na odbudowywanym urządzeniu wymaga zatwierdzenia zawartości, sposobu bezpiecznego dostarczenia archiwum w prywatny obszar roboczy oraz planu cofnięcia zmian. Nie uruchamiaj `--apply` przed zakończeniem GATE 0–3.
4. Zachowaj wersję managerów AMTM/Unbound Manager i nowy `post-mount`. W archiwum kopia hooka jest **wyłącznie do porównania**; `restore.sh` wyłącza automatyczne odtwarzanie nawet dawnych wersji `jffs/scripts/post-mount`.
5. Jeżeli wybierasz ponowną instalację kodu projektu, [`scripts/install.sh`](../scripts/install.sh) wymaga `config/edge.conf` (prywatnego), GNU `patch` i zweryfikowanego artefaktu ARMv7 supervisor. Instalator modyfikuje hooki JFFS; nawet bez `--apply` nie jest wyłącznie odczytowy. **Nie wykonuj bez przeglądu, snapshotu i planu wycofania.**

Odczytowy checkpoint **po zatwierdzonym odtworzeniu**:

```sh
test -r /jffs/configs/asus-edge.conf && echo 'EDGE_CONF=PASS'
sh -n /jffs/scripts/services-start
sh -n /jffs/scripts/wan-event
sh -n /jffs/scripts/firewall-start
test -x /jffs/addons/asus-edge/bin/dns-guard
test -x /jffs/addons/asus-edge/bin/healthcheck.sh
```

**Uzupełnienie z 2026-10-09 — dodatkowy BusyBox ARMv7:** opcjonalna wersja 1.36.1 w /jffs/addons/asus-edge/tools/busybox/1.36.1/busybox **nie jest objęta obecnym archiwum CORE**. Nie jest zależnością rozruchu ani odbudowy DNS. Dopiero po ukończeniu odbudowy podstawowej infrastruktury odtwórz ją z **osobnego, zweryfikowanego artefaktu na Fedorze** albo z ponownej, sprawdzonej kompilacji. Nie zastępuj /bin/busybox, /bin/sh ani globalnego PATH. Instrukcja PL: [bezpieczne używanie BusyBox ARMv7](pl/busybox-armv7.md); kontrakt EN: [custom BusyBox ARMv7](custom-busybox-armv7.md). Weryfikacja trwałości po restarcie i osobny test rollbacku tej wersji pozostają otwarte.

**GATE 4:** manifest CORE i uprawnienia zweryfikowane, hooki zgodne z aktualnym managerem, testy składni PASS, rollback możliwy. **Nie aktywować docelowego DNS Guard do Pi-hole** przed ukończeniem następnego etapu.

## 6. Pi-hole, Gravity i FTL — rekonstrukcja ze sprawdzonego archiwum

1. Zweryfikuj prywatny Pi-hole DR backup na Fedorze (integralność SHA-256, 15 źródłowych plików, cztery manifesty, SQLite Gravity). Użyj prywatnego tmpfs i inspekcji bez automatycznego wypakowania całego archiwum jako root.
2. Na docelowym odbudowywanym routerze zainstaluj / potwierdź właściwe wydanie FTL i konto `pihole` 999:999. Przy zatrzymanym FTL odtwórz **wyłącznie** zaakceptowane pliki i metadane ze zweryfikowanego archiwum.
3. Referencyjny kontrakt: `/opt/etc/pihole` 999:999 / 0755; `pihole.toml`, `gravity.db`: 999:999 / 0640; `/opt/bin/pihole-FTL`: 0:0 / 0755.
4. FTL `security.capability` **nie przetrwało tar**. Po sprawdzeniu sumy przywróconej binarki ustaw **wyłącznie na docelowej kopii** zestaw z prywatnego `manifest/ftl-capabilities.txt`, następnie potwierdź `getcap`. Laboratorium Fedora tmpfs przeszło ten round-trip; na pustym Entware pozostaje on do przetestowania.
5. `S64pihole-ip` musi ustanowić dedykowany adres **`192.168.50.253`** **przed** startem `S65pihole-FTL`; `S61unbound` musi zapewnić upstream na `127.0.0.1:53535`. Sprawdź uniknięcie konfliktu TCP/UDP 53 z firmware dnsmasq.
6. Nie przywracaj historii zapytań FTL ani danych uwierzytelniania Tailscale jako elementu tego archiwum.

Tylko kontrola odczytowa **po** zaakceptowanym odtworzeniu:

```sh
id pihole
/opt/bin/stat -L -c '%u:%g %a %n' \
  /opt/etc/pihole /opt/etc/pihole/gravity.db /opt/etc/pihole/pihole.toml \
  /opt/bin/pihole-FTL
/opt/sbin/getcap /opt/bin/pihole-FTL
for S in S61unbound S64pihole-ip S65pihole-FTL; do
    sh -n "/opt/etc/init.d/$S" || exit 1
done
/opt/sbin/unbound-checkconf -q /opt/var/lib/unbound/unbound.conf
/bin/busybox ifconfig -a | grep -F '192.168.50.253'
```

**GATE 5:** FTL bez błędów startu, Gravity integralne, UID/GID/mode/capabilities zgodne, alias przed FTL i odseparowane listenery. Nie przełączać DHCP ani resolvera routera na Pi-hole przed spełnieniem GATE 5.

## 7. Kontrolowana aktywacja DNS Guard i usług

Odbudowuj kolejno:
1. **WAN bootstrap DNS + NTP** niezależne od Pi-hole.
2. **Unbound**, test TCP/UDP i DNSSEC na `127.0.0.1:53535`.
3. **Pi-hole/Gravity**, test zwykłej rezolucji, kontrolowanego blokowania i upstream.
4. **DNS Guard v3.2** z poprawnymi wartościami `EDGE_DNS_LOCAL_RESOLVER_IP`, watchdog w `cru` i działającym `crond`; *dopiero* gdy `ready` PASS — przełączenie lokalne w kontrolowanym wdrożeniu. Nie ustawiać routerowego DNS na Pi-hole wcześniej.
5. **dnsmasq DHCP / LAN**: reklamowanie docelowego DNS `192.168.50.253` wyłącznie gdy stabilny; kontrola lokalnych nazw, PTR, logiki przechwytywania DNS i polityki DoT.
6. **Tailscale**: ponowne uprawnione zalogowanie, `netfilter-mode=off`, brak odzyskiwania starego stanu auth; następnie **firewall** i test dozwolonych/zabronionych źródeł.
7. **syslog-ng**, RouterCloud, telemetryczne kolektory oraz usługi poboczne — dopiero gdy CORE DNS i dostęp administracyjny są stabilne.

Kontrole końcowe **tylko odczytowe**:

```sh
/jffs/addons/asus-edge/bin/dns-guard ready
/jffs/addons/asus-edge/bin/dns-guard status
/jffs/addons/asus-edge/bin/dns-guard metrics
cru l | grep -F '#AsusEdgeDNSGuard#'
cat /tmp/resolv.conf
/bin/busybox pidof unbound
/bin/busybox pidof pihole-FTL
/bin/busybox pidof tailscaled
/jffs/addons/asus-edge/bin/healthcheck.sh
/jffs/addons/asus-edge/bin/check-usb-exposure.sh
```

**GATE 6:** DNS Guard `READY=PASS`, resolver lokalny `192.168.50.253` po ustabilizowaniu, działający WAN fallback, filtry i DNSSEC, DHCP/PTR, firewall i dostęp administracyjny, sprawny Tailscale oraz wynik `Summary: 0 failure(s), 0 warning(s)` (albo jawnie wyjaśnione wyjątki poza pełną akceptacją).

## 8. Restart docelowego odbudowanego routera

Dopiero po spełnieniu GATE 0–6, mając fizyczny dostęp i maintenance window, wykonaj **jeden** ręcznie autoryzowany restart *odbudowywanego* routera. Nie wykonuj automatycznego kolejnego restartu przy braku SSH. Porównaj:
- faktycznie **nowy** uptime i powrót SSH przez LAN;
- oba swap, `/opt`, Entware, kolejność `swapon` przed AMTM;
- FTL capabilities, alias Pi-hole, Unbound/FTL/Tailscale/syslog-ng;
- DNS Guard watchdog **przed** ścieżką oczekiwania na Entware, początkowa polityka WAN i późniejszy powrót na Pi-hole;
- DNSSEC/Gravity/DHCP, reguły firewalla, brak nadmiarowej ekspozycji USB;
- końcowy healthcheck bez błędów i ostrzeżeń.

**GATE 7:** odbudowane urządzenie po restarcie działa samodzielnie i spełnia wszystkie kryteria. W razie błędu **STOP**, zachowaj logi w prywatnym miejscu, odzyskuj dostęp przez LAN i bootstrap DNS, przywróć ostatni zweryfikowany etap; nie wykonuj pochopnego resetu fabrycznego.

## 9. Czego ta procedura nadal NIE dowodzi

- Pełna rekonstrukcja routera z firmware + pustym JFFS + pustym SSD, w tym dokładne pakiety Unbound/FTL i bezkolizyjne konta: **jeszcze nie wykonana**.
- Przywrócenie firmware CFG, FTL capabilities na świeżym filesystemie Entware, kompletna integracja usług po rzeczywistym restore: **nieprzetestowane razem**.
- Rozruch przy brakującym Entware i jednoczesna utrata obu ścieżek DNS: **niezweryfikowane**.
- RTO/RPO: **niezmierzone**. Szyfrowanie oraz integralność plików nie gwarantują jeszcze dostępności pakietów ani możliwości importu CFG.

**Zaliczona węższa część:** 2026-10-09 potwierdzono integralność prywatnych backupów, odtwarzanie CORE w clean-room, odtworzenie capabilities na Fedorze tmpfs, a na istniejącym routerze jeden kontrolowany restart, pełną konwergencję usług i healthcheck 0/0. Patrz [dowód #129](../evidence/2026-10-09/issue-129-pihole-dr-reboot-persistence.md).

### Kolejne bezpieczne ćwiczenie

Przygotować odizolowane środowisko/testowy router i **suchy przebieg całej listy GATE 0–7**, notując brakujące artefakty instalacyjne oraz wszelkie nieodtwarzalne zależności. Nie uznawać #129 za zamknięte, dopóki pusta instancja rzeczywiście nie osiągnie GATE 7.
