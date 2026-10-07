# ASUS TUF-AX5400 observability reference deployment

This directory captures the external monitoring baseline validated on 2026-09-27.

```text
ASUS TUF-AX5400
  ├─ read-only SSH collection ──> asus-wifi-exporter :9101
  └─ Traffic Analyzer SQLite ───> scheduled importer
                                      |
Internet/DNS targets ──> blackbox_exporter :9115
                                      |
                                      v
                             VictoriaMetrics :8428
                                      |
                                      v
                                  Grafana :3000
                                      ^
                                      |
Browser -> https://grafana.home.arpa -> Caddy 127.0.0.1:443
```

All monitoring HTTP listeners bind to `127.0.0.1`; the baseline does not
expose the monitoring stack to LAN or WAN. Grafana remains on
`127.0.0.1:3000` and is accessed locally through Caddy at
`https://grafana.home.arpa/`.

The custom collector/importer baseline comes from
`idcdog/asuswrt-merlin-monitoring` pinned at
`ed2f24a25f90983cb7e7715af61332b51491223b`. Apply the patch in
`patches/` before installing the exporter.

The validated Fedora deployment uses a 30-second exporter/scrape interval,
10-minute Traffic Analyzer timer and 90-day VictoriaMetrics retention.

The SSH-dependent systemd user units deliberately keep `NoNewPrivileges=true`
but do not use `ProtectSystem`, `ProtectHome` or `PrivateTmp`. On Fedora 44,
those options caused a user namespace where OpenSSH rejected the legitimate
root-owned `/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf`. Dedicated system
services that do not depend on the user's SSH configuration retain stronger
sandboxing.

Enable linger for boot-time user services:

```bash
sudo loginctl enable-linger "$USER"
```

Security boundary: no private SSH key, client identifiers, WAN address or
Tailscale identity belongs in this directory. See
[the case study](../docs/case-studies/asus-tuf-ax5400-observability-case-study.md) and
[sanitized evidence](../evidence/2026-09-27/observability-stack-validation.md).


## Local HTTPS frontend for Grafana

The validated local operator URL is:

```text
https://grafana.home.arpa/
```

The reference host resolves that name locally:

```text
127.0.0.1 grafana.home.arpa
```

Caddy terminates HTTPS only on loopback and proxies to Grafana:

```text
127.0.0.1:443 -> Caddy -> 127.0.0.1:3000 -> Grafana
```

The tested Caddy configuration is stored in
[`caddy/Caddyfile`](caddy/Caddyfile). Grafana's systemd drop-in also sets its
canonical root URL to `https://grafana.home.arpa/`.

Caddy uses an internal CA for the local certificate. The Caddy service runs as
the unprivileged `caddy` account, so automatic installation of the root CA into
Fedora's system trust store can fail because that service account has no sudo
rights. The validated procedure is documented in
[`caddy/README.md`](caddy/README.md).

Never commit the Caddy CA private key or other files from the live Caddy storage
directory.


## Grafana alerting

Nine source-controlled Grafana alert rules are provisioned from
[`grafana/provisioning/alerting/asus-tuf-alerts.yml`](grafana/provisioning/alerting/asus-tuf-alerts.yml):

- SSH collector unavailable;
- router-reported WAN down;
- failed HTTPS / ICMP / router-DNS blackbox probe;
- stale router telemetry;
- negotiated WAN link speed below 900 Mb/s for at least three minutes;
- RouterCloud backup result is failed;
- RouterCloud backup age exceeds eight hours, with an additional five-minute `for` window;
- RouterCloud maintenance/integrity result is failed;
- RouterCloud maintenance age exceeds eight days, with an additional thirty-minute `for` window.

The original controlled collector outage drove the collector and telemetry rules
through `Pending -> Firing`, while the independent blackbox rule remained
healthy. After the collector restarted, all rules returned to normal. The same
test established the dependency boundary that missing collector data must not
masquerade as WAN-down evidence, so the WAN rule uses `noDataState: OK`.

An e-mail contact point is provisioned from
[`grafana/provisioning/alerting/asus-email-contact.yml`](grafana/provisioning/alerting/asus-email-contact.yml).
SMTP credentials remain local to the Fedora host and are not stored in Git.
All nine current rules route directly to `ASUS Edge Gateway Email`, and the
contact point keeps resolved notifications enabled. Actual firing/resolved inbox
delivery is live-validated for the WAN-speed path.

On 2026-10-07, `routercloud_backup_bad` was also exercised with a controlled
live E2E test. The test injected only the coarse success metric into local
VictoriaMetrics, waited for Grafana to reach `Alerting/Firing`, restored the
real healthy metric from `status.env`, and required recovery to `Normal` or no
active alert instance. It also leaves a cleanup trap so an interrupted test
attempts to restore the real metric. This proves the RouterCloud rule evaluation
and Grafana notification-routing path; it does not claim a separately captured
RouterCloud inbox delivery.

The live test is intentionally **not** part of normal CI because it mutates the
local metrics state and can generate real notifications:

```sh
./tests/test-grafana-routercloud-alerting-live.sh
```

Issue #178 still owns grouping/anti-flap validation and bounded
Telegram/mobile critical escalation. The four RouterCloud rules and direct
e-mail routing are no longer open items.

See [the original alerting validation evidence](../evidence/2026-09-27/grafana-alerting-validation.md),
the [WAN-speed e-mail validation](../evidence/2026-10-06/grafana-wan-speed-email-alert-validation.md),
and the [RouterCloud live alerting validation](../evidence/2026-10-07/grafana-routercloud-alerting-live-validation.md).

## Pi-hole DNS activity collector

Issue #108 Phase 0, the Fedora collector, local Alloy/Loki ingestion, the
Grafana DNS dashboard, full Fedora reboot persistence and controlled two-client
main-LAN acceptance were live-validated on 2026-09-28. The complete analytics
path remains Fedora-side; no Loki/Alloy listener is exposed to LAN or WAN.

The implemented acquisition path is:

```text
Pi-hole FTL authenticated API on ASUS
        |
        | SSH local forward
        v
127.0.0.1:18080 on Fedora
        |
        v
pihole-dns-collector.py
        |
        +--> private SQLite checkpoint/journal
        |
        +--> private queries.ndjson
                  |
                  v
                Alloy
                  |
                  v
          127.0.0.1:3100 Loki
                  |
                  v
          existing local Grafana
```

The collector accepts API credentials only through a private local credential
file and refuses cleartext non-loopback HTTP.

Phase 0 showed that the global API cursor can be ahead of the newest row
already flushed to disk. The implementation therefore freezes the disk and
memory sources on their own first returned query IDs, unions them on Fedora,
deduplicates by query ID and advances its checkpoint only after a journaled
local append.

Reference files:

- `pihole-dns-collector.py`
- `config/pihole-dns-collector.env.example`
- `systemd/pihole-api-tunnel.service`
- `systemd/pihole-dns-collector.service`
- `systemd/pihole-dns-collector.timer`
- `systemd/pihole-dns-collector-alloy-spool.conf`
- `alloy/config.alloy`
- `loki/config.yml`
- `grafana/provisioning/datasources/loki.yml`
- `grafana/dashboards/pihole-dns-activity.json`

The recurring timer remains separate from the one-shot service. Live validation
confirmed manual collection, timer-driven collection, prepared-batch recovery,
a controlled SSH-transport failure and catch-up after transport restoration.
The final integrity checkpoint contained 10,414 unique, strictly ascending query
IDs with zero duplicates and a matching persisted checkpoint. The default guard
allows at most 1,000 pages of 500 rows per source and fails closed rather than
silently skipping a larger backlog.

See the
[sanitized collector validation evidence](../evidence/2026-09-28/pi-hole-dns-collector-live-validation.md)
and the
[Phase 2/3 analytics validation](../evidence/2026-09-28/pi-hole-dns-analytics-phase2-3-validation.md).

The validated Loki deployment uses TSDB v13 with filesystem storage under
`/var/lib/loki`, seven-day configured retention and loopback-only HTTP/gRPC.
Alloy tails the private DNS spool and forwards only to local Loki. A bounded
equality check matched 11,116 local events to 11,116 Loki events for the tested
window. Domain/client/upstream values remain parsed fields rather than
persistent Loki labels.

A controlled Fedora reboot returned Grafana, Loki, Alloy, Caddy, the Pi-hole
SSH tunnel and the collector timer automatically. The collector remained
duplicate-free with a matching checkpoint; after the stack settled, the
seven-day source/Loki equality check matched 12,183 events to 12,183 events.
Loki may briefly return HTTP 503 from `/ready` while its startup ring/WAL
recovery converges.

A later controlled two-client test distinguished two separate main-LAN clients
without publishing their addresses. The same test confirmed the current
Tailscale coverage boundary: a Windows classic-DNS marker carried over
`tailscale0` was absent from Pi-hole history, while the client became visible
when using the ordinary main-LAN Pi-hole path.

The provisioned Grafana dashboard is titled
`Pi-hole — Aktywność DNS v2`. It includes blocked/cache/forwarded/unfinished
status, cache-hit rate, reply latency, top domains/clients/upstreams and an
explicit coverage disclaimer. Live screenshots containing real household DNS
activity are intentionally not stored in the public repository.

This pipeline remains separate from the VictoriaMetrics metrics path and the
syslog-ng mTLS system-log path. Full domain names, client IPs and hostnames must
remain parsed event fields rather than persistent high-cardinality Loki labels.

The scope remains limited to Pi-hole-visible DHCP-managed main-LAN traffic.
The tested Tailscale classic-DNS path is now an evidence-backed exclusion; the
hard-coded external LAN interception path and encrypted-DNS paths remain
separate coverage work. See
[the analytics plan](../docs/network-dns-visibility-client-activity-analytics.md).

## Grafana interface language

Grafana 13 provides a built-in Polish interface option. The application UI
itself therefore does not require a custom translation patch.

This is separate from dashboard content: panel titles, descriptions, legends
and other strings stored in the project dashboard JSON are project-owned
content and were localized explicitly. The reference deployment therefore uses
the native Polish Grafana UI together with the project-localized Polish
TUF-AX5400 dashboard.

## Grafana GitHub / CI observability

The 2026-09-28 Fedora Grafana checkpoint also added a read-only GitHub
integration for this repository. The validated plugin set includes:

- Grafana GitHub Data Source 2.9.1;
- Polystat Panel 2.1.16;
- Business Charts / Apache ECharts 7.2.5.

The GitHub datasource is provisioned read-only. Its fine-grained credential is
kept locally on Fedora and is not stored in repository files or dashboard JSON.

The `ASUS Edge Gateway — Engineering / CI` dashboard is now complete and
source-controlled as
[`grafana/dashboards/asus-edge-gateway-engineering-ci.json`](grafana/dashboards/asus-edge-gateway-engineering-ci.json).
The stored file is the Grafana 13.2.2 v2 resource form with dashboard UID
`ad92bsh`.

The live-validated dashboard includes:

- recent Validation suite workflow runs, sorted newest first, with direct run
  links;
- the latest CI result;
- current open-Issue and open-Pull-Request counts;
- merged Pull Requests over the selected dashboard period, filtered by
  `MergedAt`, with direct PR links;
- recent commits on `main`, sorted newest first, with direct commit links;
- a Polystat `Infrastructure Health` overview for the SSH collector, WAN,
  Internet HTTPS, Internet ICMP, router DNS, VictoriaMetrics and Grafana.

The Polystat queries are instant checks and map `1 -> OK` and `0 -> BŁĄD`.
The 2026-09-29 accepted live checkpoint showed all seven signals as `OK`.

The exported dashboard resource contains datasource names, queries and panel
configuration only. The GitHub credential remains in the locally provisioned
datasource and is not stored in dashboard JSON. Business Charts remains
optional and is not required by this dashboard.

