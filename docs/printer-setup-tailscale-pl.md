# Zdalne drukowanie Samsung przez Tailscale

Instrukcja opisuje ograniczony źródłowo dostęp z Androida do starszej drukarki
Samsung znajdującej się za routerem ASUS. Najpierw musi działać drukowanie w
LAN zgodnie z [instrukcją lokalną](printer-setup-lan-pl.md).

> Adresy w publicznym dokumencie pochodzą z zakresów dokumentacyjnych. Rzeczywiste
> adresy LAN i Tailscale przechowuj wyłącznie w lokalnym `asus-edge.conf`.

## 1. Potwierdzony i niepotwierdzony zakres

Potwierdzono:

- dostęp Androida przez subnet route Tailscale;
- otwarcie panelu drukarki przez tunel;
- dwukierunkowe zapytania SNMP;
- fizyczny wydruk przez **zewnętrzne Wi-Fi/hotspot i Tailscale**;
- brak potrzeby wybierania Exit Node;
- odrzucanie przez router ruchu telefonu poza polityką drukarki.

Nie potwierdzono jako działającego:

- wydruku przez **same dane komórkowe** z Samsung Print Service Plugin;
- zdalnego wydruku z Windows lub Zorin OS;
- bezpośredniego IPP omijającego wtyczkę Samsunga;
- serwera pośredniczącego CUPS/IPP.

W kontrolowanym teście LTE działał SNMP, ale wtyczka nie otworzyła połączenia
TCP/631 ani TCP/9100. Zapora nie odrzuciła zadania - zatrzymało się ono po stronie
klienta Android. Nie należy naprawiać tego przez poszerzanie reguł zapory.

## 2. Architektura i granica szyfrowania

```text
Android -> szyfrowany tunel Tailscale -> router ASUS -> LAN -> drukarka
```

Tailscale szyfruje ruch od telefonu do routera. Odcinek router-drukarka pozostaje
lokalny i korzysta z nieszyfrowanych protokołów starszego urządzenia: HTTP, IPP,
RAW i SNMP.

## 3. Warunki wstępne

- lokalny wydruk działa na co najmniej jednym kliencie;
- Windows 10/11 korzysta z Samsung Universal Print Driver 3, a nie z
  automatycznie zainstalowanego Class Driver V4, jeśli ten nie przechodzi testu;
- router reklamuje trasę podsieci LAN;
- trasa została zatwierdzona w panelu administracyjnym Tailscale;
- telefon znajduje się we właściwym tailnecie;
- Samsung Print Service Plugin nie jest wykluczona w App split tunneling;
- Exit Node na telefonie pozostaje niewybrany.

## 4. Polityka źródłowa na routerze

Przykład do publicznej dokumentacji:

```sh
EDGE_LAN_IF="br0"
EDGE_PRINTER_TS_SOURCES="192.0.2.95/32"
EDGE_PRINTER_LAN_IP="198.51.100.140"
EDGE_PRINTER_TCP_PORTS="80 631 9100"
EDGE_PRINTER_UDP_PORTS="161"
```

| Port | Protokół | Zastosowanie |
|---|---|---|
| 80 | TCP/HTTP | Panel WWW i kontrola dostępności |
| 631 | TCP/IPP | Przesyłanie zadania IPP |
| 9100 | TCP/RAW | Przesyłanie zadania przez starszego klienta |
| 161 | UDP/SNMP | Odczyt stanu i możliwości drukarki |

Polityka powinna dopuszczać jedno źródło `/32`, jeden cel `/32` i wyłącznie
potwierdzone porty. Pozostały ruch przychodzący z `tailscale0` pozostaje
blokowany.

Zastosowanie i kontrola:

```sh
/jffs/scripts/firewall-start
/jffs/addons/asus-edge/bin/healthcheck.sh
iptables -nvL EDGE_TS_FORWARD --line-numbers
```

Oczekiwany healthcheck zawiera `source-scoped printer policy`, zero błędów i zero
ostrzeżeń. Dwukrotne uruchomienie `firewall-start` nie może powielać reguł.

## 5. Konfiguracja telefonu

1. Włącz Tailscale i pozostaw Exit Node jako **Brak/None**.
2. Otwórz **Settings -> App split tunneling**.
3. Upewnij się, że Samsung Print Service Plugin nie znajduje się na liście
   `Excluded apps`.
4. Wyłącz Systemowe usługi drukowania Androida.
5. Zainstaluj lub zaktualizuj Samsung Print Service Plugin.
6. Włącz wtyczkę i dodaj drukarkę po jej rzeczywistym adresie LAN.
7. Uruchom telefon ponownie.

Do odczytania publicznej strony statusu drukarki nie jest potrzebne logowanie do
SyncThru. Logowanie administratora jest wymagane tylko przy zmianie ustawień.

## 6. Potwierdzony test zdalny

1. Odłącz telefon od domowego Wi-Fi.
2. Połącz go z obcą siecią Wi-Fi albo hotspotem drugiego urządzenia.
3. Włącz Tailscale; Exit Node pozostaw niewybrany.
4. Otwórz `http://PRINTER_LAN_IP`.
5. Wyślij jedną stronę PDF lub zdjęcie przez Samsung Print Service Plugin.
6. Potwierdź fizyczny wydruk i brak zaległego zadania Androida.

Podczas próby obserwuj liczniki:

```sh
iptables -Z EDGE_TS_FORWARD
iptables -nvL EDGE_TS_FORWARD --line-numbers
```

Interpretacja:

- wzrost TCP/80 potwierdza dostęp do panelu;
- wzrost UDP/161 potwierdza odczyt stanu, ale nie wysłanie wydruku;
- wzrost TCP/631 lub TCP/9100 oznacza próbę przesłania zadania;
- wzrost DROP wymaga sprawdzenia źródła, celu i portu.

## 7. Test przez dane komórkowe

Można go wykonywać diagnostycznie, ale dla przetestowanej wtyczki nie jest to
obsługiwany wariant. Jeżeli HTTP lub SNMP działa, lecz TCP/631 i TCP/9100
pozostają na zero, Tailscale i zapora doprowadzają ruch do drukarki, ale klient
nie wysyła zadania.

W takiej sytuacji:

1. anuluj oczekujące zadanie;
2. wymuś zatrzymanie bufora wydruku i wtyczki;
3. usuń zapisaną drukarkę i dodaj jej adres ponownie;
4. uruchom telefon;
5. powtórz test przez zewnętrzne Wi-Fi/hotspot;
6. nie dodawaj szerokich reguł `ACCEPT` ani przypadkowych portów.

## 8. Diagnostyka pakietów

Nagłówkowe przechwycenie ruchu bez treści dokumentu:

```sh
tcpdump -ni any -nn -s 96 \
  'host PRINTER_LAN_IP and (tcp port 80 or tcp port 631 or tcp port 9100 or udp port 161)'
```

| Objaw | Wniosek | Dalszy krok |
|---|---|---|
| Brak HTTP i wszystkie liczniki = 0 | Ruch nie wszedł przez Tailscale | Sprawdź połączenie, trasę i split tunneling |
| HTTP działa, wtyczka nie widzi drukarki | Problem integracji Androida | Reinstaluj wtyczkę i dodaj IP |
| SNMP działa, brak TCP/631 i 9100 | Wtyczka nie wysłała zadania | Użyj zewnętrznego Wi-Fi/hotspotu |
| TCP/631 lub 9100 rośnie, brak papieru | Problem drukarki, formatu lub kolejki | Sprawdź stan urządzenia i prosty PDF A4 |
| Pakiety trafiają do DROP | Źródło, cel lub port nie pasuje | Odczytaj `SRC`, `DST`, `PROTO`, `DPT` |
| Po restarcie reguł brak | Konfiguracja nie jest trwała | Sprawdź `/jffs` i hook `firewall-start` |

Ruch telefonu do innego hosta lub usługi - na przykład TCP/1716 - nie jest
ruchem drukarki i ma pozostać zablokowany.

## 9. Windows 10/11

W zweryfikowanym wdrożeniu Windows 11 nie miał klienta Tailscale i drukował
wyłącznie w LAN. Windows 10 konfiguruje się lokalnie tak samo. Zdalnego wydruku
z Windows nie należy uznawać za działający, dopóki osobno nie zostaną
skonfigurowane: klient Tailscale, akceptacja trasy, źródłowa reguła `/32`, port
RAW 9100 oraz test strony fizycznej.

Automatycznie instalowany przez Windows Class Driver V4 nie był przez nas
wybierany ręcznie i w testowanej konfiguracji nie drukował. Działającym
sterownikiem lokalnym był Samsung Universal Print Driver 3.

## 10. Bezpieczeństwo i utrzymanie

- nigdy nie przekierowuj portów drukarki z WAN;
- nie dopuszczaj całego tailnetu, jeżeli drukować ma jedno urządzenie;
- po zmianie telefonu zaktualizuj źródłowy adres Tailscale `/32`;
- przechowuj rzeczywiste adresy wyłącznie w lokalnej konfiguracji;
- po restarcie routera uruchom healthcheck i sprawdź reguły;
- traktuj dostęp przez same dane komórkowe jako niepotwierdzony;
- w przyszłości rozważ CUPS/IPP na Raspberry Pi lub x86-64, jeśli wymagany jest
  niezawodny wydruk niezależny od zachowania starej wtyczki Androida.

Końcowo potwierdzony wariant to: **Android -> zewnętrzne Wi-Fi/hotspot ->
Tailscale -> router ASUS -> drukarka**.

