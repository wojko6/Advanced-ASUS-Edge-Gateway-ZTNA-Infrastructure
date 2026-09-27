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
