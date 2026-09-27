# ASUS TUF-AX5400 observability stack validation — 2026-09-27

## Scope

Sanitized live validation. Client MAC addresses, client hostnames, WAN
addresses, Tailscale identities and authentication material are excluded.

Reference platform: ASUS TUF-AX5400, GNUton
`3004.388.11_1-gnuton1_tuf`, Fedora 44 monitoring host.

## Read-only preflight

```text
PASS  SSH public-key collection
PASS  router model: TUF-AX5400
INFO  wireless base interfaces: eth5 eth6
INFO  active WAN interface: vlan35
PASS  active WAN sysfs counters
PASS  active WAN negotiated speed: 1000 Mbps
PASS  nvram / wl / conntrack / sqlite3
PASS  Traffic Analyzer database and schema
PASS  router device inventory
Summary: 15 PASS, 0 WARN, 0 FAIL
```

## Radio compatibility

```text
eth5: current channel 8;   chanspec 8l (0x180a)
eth6: current channel 100; chanspec 100/160 (0xe872)
```

The original exporter failed parsing the hexadecimal chanspec. After the
read-only channel-source adaptation, the exporter returned valid 2.4/5 GHz
channels, WAN state/speed, temperatures and system metrics. Initial metric
count: 166. Later scrape sample count: 171.

## Traffic Analyzer

```text
dry-run: 428 buckets, 12 devices, 2848 samples
historical RX series found: 12
post-reboot timer: 1 new bucket, 4 devices, 8 samples, status=0/SUCCESS
```

No client identifiers are reproduced.

## Blackbox

```text
HTTPS example.com: probe_success 1
ICMP 1.1.1.1:     probe_success 1
DNS via router:   probe_success 1
```

## Reboot validation

Before reboot all system/user monitoring units were enabled and active and
`Linger=yes`. After the real reboot they returned automatically; all HTTP
listeners remained on `127.0.0.1`. Boot-scoped warning/error queries returned
no entries.

After one scrape interval:

```text
exporter /healthz: HTTP 200
target health: up
lastError: ''
lastSamplesScraped: 171
up{job="asus_wifi_clients"} = 1
```

**Result: PASS — external observability baseline live-validated.**


## Local HTTPS frontend validation

Caddy package/version:

```text
caddy-2.11.4-2.fc44.x86_64
Caddy v2.11.4
```

Validated listeners:

```text
127.0.0.1:443   caddy
127.0.0.1:3000  grafana
```

No `0.0.0.0:443` or `[::]:443` listener was observed.

The first HTTPS reverse-proxy test returned:

```text
HTTP/2 302
location: /login
via: 1.1 Caddy
```

Caddy logged that automatic system trust installation failed because the
unprivileged `caddy` service account is not in sudoers. The local CA public
root was therefore installed manually into the Fedora trust store. The tested
Brave/Chromium profile additionally received the public root CA through the
user NSS database.

Final browser validation loaded:

```text
https://grafana.home.arpa/login
```

without the certificate warning.

The private CA key was not copied into public evidence. The validation remains
strictly local and does not claim LAN, Tailscale or WAN exposure.
