# ASUS TUF-AX5400 external observability case study

## Executive summary

On 2026-09-27 the reference ASUS TUF-AX5400 / GNUton deployment gained an
external observability stack without adding time-series storage or dashboard
workloads to the 512 MiB router.

Validated architecture:

```text
ASUS TUF-AX5400
  ├─ read-only SSH telemetry ──> custom exporter :9101
  └─ Traffic Analyzer SQLite ─> importer every 10 minutes
                                   |
Internet + DNS probes ─────────> Blackbox Exporter :9115
                                   |
                                   v
                          VictoriaMetrics :8428
                                   |
                                   v
                              Grafana :3000
```

All HTTP components bind to loopback. Router-side interaction is read-only.

## Compatibility finding and remediation

The starting point was `idcdog/asuswrt-merlin-monitoring` pinned at
`ed2f24a25f90983cb7e7715af61332b51491223b`. Router-only preflight passed
15 checks with 0 warnings and 0 failures.

The first live exporter run failed because `chanim_stats` returned a hexadecimal
Broadcom chanspec (`0x180a`) where the parser expected a decimal channel.
Read-only validation showed channel 8 / chanspec `8l (0x180a)` on 2.4 GHz and
channel 100 / chanspec `100/160 (0xe872)` on 5 GHz.

The bounded fix keeps utilization/noise from `chanim_stats` and obtains the
primary channel from `wl -i <radio> channel`. The router configuration is not
modified. After the fix, a one-shot collection emitted 166 metrics; a later
steady scrape stored 171 samples.

## Traffic Analyzer and Internet probes

Traffic Analyzer dry-run validated 428 hourly buckets, 12 devices and 2848
samples. The initial import succeeded. After a real Fedora reboot the timer
imported one new completed hourly bucket (4 devices / 8 RX+TX samples) and
advanced its state successfully.

Blackbox direct tests returned `probe_success 1` for HTTPS to example.com,
ICMP to 1.1.1.1 and a DNS A-query for example.com through the ASUS router.

## Service security and local exposure

Validated listeners were restricted to loopback on ports 3000, 8428, 9101,
9102 and 9115. Blackbox runs unprivileged with only `CAP_NET_RAW` for ICMP.

The first SSH collector user unit used `ProtectSystem=strict`,
`ProtectHome=read-only` and `PrivateTmp=true`. On Fedora 44 this created a
user namespace in which OpenSSH rejected the legitimate root-owned system SSH
configuration file. The user-unit namespace options were removed; the host file
itself remained `root:root 0644`. `NoNewPrivileges=true` remains enabled.

## Reboot persistence

After a real Fedora reboot, the SSH collector, VictoriaMetrics, Grafana,
Blackbox Exporter and Traffic Analyzer timer returned automatically. Boot-scoped
warning/error checks for the monitoring units contained no entries.

The SSH scrape briefly showed `up=0` during startup convergence. After one full
scrape interval the target was `up`, `lastError` was empty, 171 samples were
scraped and `up{job="asus_wifi_clients"} = 1`.

This validates restart persistence for the tested Fedora host, not high
availability while the workstation is powered off.

## Local HTTPS frontend

After the monitoring stack and dashboard were validated, the local Grafana
frontend was hardened/polished with Caddy.

Grafana remains bound to `127.0.0.1:3000`. Caddy 2.11.4 listens only on
`127.0.0.1:443` and serves the local operator URL:

```text
https://grafana.home.arpa/
```

The local name resolves to loopback. Caddy uses `tls internal` and proxies only
to the local Grafana listener. HTTP-to-HTTPS redirect handling is disabled so no
port-80 listener is required.

The packaged service could not automatically install its internal CA because
the unprivileged `caddy` account is not a sudoer. The public root certificate
was installed manually into Fedora's trust store. Brave/Chromium on the tested
profile also required the same public root certificate in the user's NSS
database. No CA private key was copied or published.

Live validation confirmed `127.0.0.1:443` for Caddy and
`127.0.0.1:3000` for Grafana. The HTTPS frontend returned HTTP/2 302 to
`/login`, and the browser subsequently loaded the local URL without a
certificate warning.

This remains a local-only frontend; it is not a design for remote Grafana
exposure.

## Grafana interface language

Grafana 13 provides a built-in Polish interface option. The application UI
itself therefore does not require a custom translation patch.

This is separate from dashboard content: panel titles, descriptions, legends
and other strings stored in the project dashboard JSON are project-owned
content and were localized explicitly. The reference deployment therefore uses
the native Polish Grafana UI together with the project-localized Polish
TUF-AX5400 dashboard.

## Dashboard adaptation

The upstream dashboard was cleaned for the reference deployment: RT-BE88U/SNMP
fallbacks and stale 192.168.1.x defaults were removed, China-specific probe
targets were replaced, WAN text was aligned with the detected `vlan35`
interface, the operator dashboard was localized to Polish, and narrow cards /
uptime display were polished.

## Claim boundaries

This case supports the tested TUF-AX5400/GNUton read-only collection path,
external storage/dashboard operation, the tested probes, historical Traffic
Analyzer import, the tested Fedora reboot recovery, and the tested loopback-only
Caddy HTTPS frontend. It does not establish cross-model compatibility, ISP
billing-grade traffic accounting, secure remote dashboard exposure or
monitoring availability while the Fedora host is off.

See [sanitized execution evidence](../evidence/2026-09-27/observability-stack-validation.md).


## Grafana alerting validation

The local Grafana deployment now provisions four baseline rules for collector
availability, WAN state, independent Internet/DNS probes and telemetry
freshness.

A controlled Fedora-only fault test stopped the SSH collector without changing
the router or WAN connection. The collector and stale-telemetry rules progressed
to `Firing`; the HTTPS/ICMP/DNS blackbox rule remained healthy. Restarting the
collector restored all rules to normal.

The test also exposed a dependency-quality issue in the initial WAN rule:
missing collector data could leave the WAN rule in a no-data state even though
the physical WAN had not been tested as down. The provisioned WAN policy was
therefore changed to `noDataState: OK`. Dedicated collector/freshness rules
own missing-telemetry detection, while the WAN rule is reserved for an actual
reported WAN-down value.

After the change, Grafana 13.2.2 reported database health `ok`, and a journal
check scoped to the newly started process contained no matching error/failure
entries.

This case validates rule evaluation and recovery only. External notification
delivery is a separate future step.
