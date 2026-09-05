# Drukarka Samsung M262x/M282x w sieci lokalnej

Instrukcja obejmuje konfigurację starszej drukarki Samsung w LAN dla Zorin OS,
Windows 10/11 oraz Androida. Najpierw uruchom wydruk na jednym komputerze, a
dopiero później konfiguruj pozostałych klientów.

> Adresy w publicznym dokumencie są przykładami z zakresów dokumentacyjnych.
> Zastąp `PRINTER_LAN_IP` rzeczywistym adresem drukarki zapisanym wyłącznie w
> konfiguracji lokalnej.

## 1. Warunki wstępne

- drukarka i klient znajdują się w tej samej sieci LAN;
- drukarka korzysta z Wi-Fi 2,4 GHz i WPA2-Personal/AES;
- router ma rezerwację DHCP dla adresu drukarki;
- panel WWW drukarki otwiera się pod `http://PRINTER_LAN_IP`;
- port RAW 9100 jest dostępny; opcjonalnie dostępne są IPP 631 i SNMP 161.

Podstawowe testy:

```sh
ping -c 3 PRINTER_LAN_IP
nc -vz PRINTER_LAN_IP 9100
nc -vz PRINTER_LAN_IP 631
```

Nie wystawiaj HTTP, IPP, RAW ani SNMP drukarki bezpośrednio do Internetu.

## 2. Stały adres i usługi drukarki

1. Odczytaj adres MAC drukarki z panelu routera lub strony konfiguracji.
2. Utwórz rezerwację DHCP i uruchom ponownie drukarkę.
3. Potwierdź, że panel SyncThru nadal otwiera się pod tym samym adresem.
4. Włącz tylko potrzebne usługi: HTTP, RAW TCP/IP 9100, IPP 631, SNMP do
   odczytu i ewentualnie mDNS/Bonjour do wykrywania lokalnego.
5. Wyłącz Telnet, FTP, WSD i Wi-Fi Direct, jeśli nie są używane.

SNMPv1/v2 nie zapewnia szyfrowania. Pozostaw społeczność tylko do odczytu i
ogranicz dostęp zaporą do sieci lokalnej.

## 3. Windows 10 i Windows 11

Konfigurację zweryfikowano w Windows 11 x64. W Windows 10 procedura jest taka
sama, chociaż nazwy ekranów Ustawień mogą się nieznacznie różnić.

### Ważna korekta dotycząca sterownika

Podczas automatycznego dodawania drukarki **Windows sam zainstalował**
`Samsung M262x 282x Series Class Driver V4`. Nie był to sterownik wskazany
ręcznie. System wykrywał drukarkę i komunikował się z nią, lecz w testowanej
konfiguracji zadania nie kończyły się fizycznym wydrukiem.

Rozwiązaniem była ręczna instalacja sterownika producenta
`Samsung Universal Print Driver 3`. W zweryfikowanym środowisku działała wersja
`3.0.16.0`, sterownik Type 3, format danych RAW i port TCP 9100.

### Instalacja

1. Pobierz oprogramowanie dla Samsung Xpress SL-M2825DW z oficjalnej strony
   wsparcia HP/Samsung.
2. Uruchom Samsung Printer Installer jako administrator.
3. Wybierz **Dostępna drukarka**, ponieważ urządzenie jest już podłączone do
   sieci.
4. Wskaż drukarkę po jej adresie `PRINTER_LAN_IP`.
5. Pozwól instalatorowi utworzyć nową kolejkę.
6. Sprawdź, czy kolejka korzysta z `Samsung Universal Print Driver 3`.
7. Sprawdź port: Standard TCP/IP, protokół RAW, numer `9100`.
8. Wydrukuj stronę testową Windows.
9. Wydrukuj dwustronicowy PDF z dupleksem po długiej krawędzi.
10. Dopiero po udanych testach usuń niedziałającą kolejkę Class Driver V4.

Kontrola w PowerShellu:

```powershell
Test-NetConnection PRINTER_LAN_IP -Port 9100

$p = Get-Printer | Where-Object DriverName -Match `
  'Universal Print Driver 3' | Select-Object -First 1

$p | Format-List Name,DriverName,PortName,PrinterStatus
Get-PrinterPort -Name $p.PortName |
  Format-List Name,PrinterHostAddress,PortNumber,Protocol,SNMPEnabled
```

Oczekuj `TcpTestSucceeded : True`, portu 9100 i protokołu RAW. Instalator może
nadać portowi nazwę identyfikatora urządzenia zamiast samego adresu IP.

Notatnik nie jest miarodajnym testem dupleksu, ponieważ jego dialog może nie
udostępniać wszystkich opcji sterownika. Testuj dwustronicowy PDF w Edge lub
Adobe Reader.

## 4. Zorin OS i CUPS

Najpierw pozwól CUPS wykryć drukarkę przez DNS-SD. Sprawdź kolejki:

```sh
lpstat -t
lpstat -v
lpstat -p -l
```

Jeżeli działająca kolejka pojawiła się automatycznie, wykonaj test:

```sh
lp -d NAZWA_KOLEJKI /usr/share/cups/data/testprint
```

Ręczna kolejka IPP może używać adresu:

```text
ipp://PRINTER_LAN_IP/ipp/print
```

Jeżeli ręczna kolejka zwraca `Printer cannot print with supplied options`, usuń
wyłącznie tę kolejkę i wróć do działającej kolejki wykrytej przez DNS-SD. Nie
usuwaj sprawnej kolejki automatycznej.

## 5. Android i HyperOS

Dla tej serii użyj `Samsung Print Service Plugin`. Systemowe usługi drukowania
Androida mogą zgłaszać, że starszy model nie jest obsługiwany.

1. Zainstaluj albo zaktualizuj Samsung Print Service Plugin ze Sklepu Play.
2. Wyłącz **Systemowe usługi drukowania**, aby podczas testu działała tylko
   wtyczka Samsunga.
3. Włącz usługę Samsung Print Service Plugin.
4. Dodaj drukarkę ręcznie po `PRINTER_LAN_IP`.
5. Uruchom telefon ponownie.
6. Wyślij jedną stronę PDF lub zdjęcie.

Jeżeli drukarka nie pojawia się w oknie drukowania, anuluj oczekujące zadania,
wyłącz i włącz wtyczkę, usuń zapisaną drukarkę i dodaj jej adres ponownie. Gdy
to nie pomaga, odinstaluj wtyczkę, zainstaluj ją ponownie i uruchom telefon.

## 6. Test odbiorczy

Wdrożenie lokalne można uznać za działające, gdy:

- panel WWW drukarki otwiera się z LAN;
- Windows drukuje stronę testową przez UPD3 i RAW 9100;
- dwustronicowy PDF drukuje się dwustronnie;
- Zorin OS drukuje przez działającą kolejkę CUPS;
- Android drukuje przez Samsung Print Service Plugin;
- po restarcie drukarki jej adres pozostaje niezmieniony;
- kolejki nie zawierają zaległych zadań.

## 7. Troubleshooting

| Objaw | Najbardziej prawdopodobna przyczyna | Działanie |
|---|---|---|
| Brak ping i panelu WWW | Adres, Wi-Fi lub izolacja klientów | Sprawdź rezerwację DHCP, pasmo 2,4 GHz i izolację AP |
| Windows wykrywa drukarkę, ale nie drukuje | Automatycznie dobrany Class Driver V4 | Zainstaluj Samsung Universal Print Driver 3 |
| Windows pokazuje Offline | Port lub monitor SNMP | Sprawdź RAW 9100; przetestuj ustawienie SNMP portu |
| Notatnik nie oferuje dupleksu | Ograniczony dialog aplikacji | Testuj PDF w Edge/Adobe Reader |
| Android zgłasza „nieobsługiwana” | Systemowa usługa bezsterownikowa | Wyłącz ją i użyj wtyczki Samsunga |
| Android nie widzi drukarki | Dane wtyczki lub zapisana kolejka | Reinstaluj wtyczkę i dodaj adres ponownie |
| CUPS zgłasza `supplied options` | Niepasująca ręczna kolejka IPP | Wróć do sprawnej kolejki DNS-SD/implicitclass |
| Po restarcie drukarka jest offline | Zmienił się adres DHCP | Przywróć rezerwację adresu |

Restart bufora Windows:

```powershell
Restart-Service Spooler
Get-PrintJob -PrinterName 'NAZWA_DRUKARKI'
```

Nie czyść całego katalogu bufora bez kopii informacji o zadaniach i świadomości,
że operacja usuwa oczekujące wydruki ze wszystkich lokalnych kolejek.

## 8. Utrzymanie

Po aktualizacji systemu, sterownika, routera albo wtyczki powtórz stronę testową,
PDF z dupleksem i test Androida. Nie resetuj drukarki do ustawień fabrycznych,
dopóki nie sprawdzisz adresacji, kolejki, portu i sterownika.

