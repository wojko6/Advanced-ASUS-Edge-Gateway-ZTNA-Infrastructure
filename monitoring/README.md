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


## Fedora VictoriaMetrics manual upgrade (2026-10-21)

**Operator-reported production acceptance:** VictoriaMetrics was upgraded from the previously recorded `1.153.0` baseline to **`1.154.1`** on Fedora 44. A backup and isolated `vmrestore` trial returned `RESTORE_TEST=PASS` (17,100,289 bytes restored); the installer then returned `DEPLOYMENT=PASS`, `SERVICE=ACTIVE`, `HTTP_HEALTH=PASS`, `QUERY_API=PASS`, `DATA_CONFIG_CHANGED=NO` and `OTHER_SERVICES_RESTARTED=NO`. A rollback/data directory was retained on Fedora. No router runtime or other monitoring service was intentionally modified by this VictoriaMetrics installer. This does not prove a cold-boot return or long-term scrape freshness. See [dated evidence](../evidence/2026-10-21/fedora-victoriametrics-1.154.1-live-upgrade.md).

## Grafana alerting

**2026-10-18 Fedora controlled-update checkpoint (operator-reported):** manually upgraded Grafana from 13.2.3 to **13.2.4** via Pilot v2.3 after verified offline SQLite/archive backup. Postflight returned Grafana HTTP 200, 15 rules / 0 paused, five active services and zero error-priority Grafana journal records in the checked hour; the operator confirmed receipt of Email and Telegram notifications. **This is not proof of delivery from all 15 rules, configuration parity after an unrelated future provisioning reload or automatic rollback.** A check-only package-update timer is active, but unattended installation is **not**. Caddy TLS 1.3/SNI passed 3/3 local probes; HTTP-over-HTTPS remains untested in the new update gate. See [Fedora update operations](../docs/operations/fedora-homelab-automatic-updates.md), [18 October worklog](../docs/worklog/2026-10-18.md) and [operator evidence](../evidence/2026-10-18/fedora-update-operator-validation.md). Existing 2026-10-15 and 2026-10-13 passages below remain dated history; the checked-in Email-only Grafana contact source is **not** a safe live Email+Telegram replacement.

**2026-10-15 repository synchronization:** [Merged PR #250](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/250) aligns the `routercloud-backup.timer` **source** with daily 21:30 and the Grafana `routercloud_backup_stale` **source** with a 26-hour threshold / 48-hour metrics window (and matching backup-failure lookback). Operator-reported live Fedora timer and a real scheduled backup on 2026-10-14 at 21:30 passed. Last reported **running** Grafana threshold on Oct 14, however, was still 8h/24h; staged 26h/48h file content was **not reloaded**. The repository merge does not install a unit or reload Grafana, and does not assert the production rule is now 26h. Any future activation must protect the live Email+Telegram contact, reconfirm 15 rules and rollback, and obtain separate explicit approval.

**2026-10-13 bounded V4 follow-up (published 2026-10-15):** The [sanitized Grafana #236 traceability evidence](../evidence/2026-10-13/grafana-rule-traceability-matrix.md) and [dated migration/rollback record](../docs/grafana-236-telegram-chatid-deployment-runbook.md) document operator-confirmed V4 Chat ID protection and a single synthetic test's real Firing+Resolved delivery to **Gmail and Telegram**, with 15 production rules remaining. The live contact point has **Email + Telegram**; the Git source `asus-email-contact.yml` is **Email-only** and is **not safe to apply as a replacement**. Do not infer individual 15-rule delivery, anti-flap, full restore, or a later Grafana provisioning reload from this publication. Related [Issue #236](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/236) remains OPEN.

Fifteen source-controlled Grafana alert rules are provisioned from
[`grafana/provisioning/alerting/asus-tuf-alerts.yml`](grafana/provisioning/alerting/asus-tuf-alerts.yml):

- SSH collector unavailable;
- router-reported WAN down;
- failed HTTPS / ICMP / router-DNS blackbox probe;
- stale router telemetry;
- negotiated WAN link speed below 900 Mb/s for at least three minutes;
- sustained DNS Guard fail-open/bootstrap mode for at least ten minutes, with fresh telemetry (`dns_guard_sustained_failopen`);
- unhealthy independent DNS bootstrap resolver (`dns_guard_bootstrap_unhealthy`);
- stale DNS Guard-specific telemetry (`dns_guard_telemetry_stale`);
- invalid or UNKNOWN DNS Guard state (`dns_guard_state_unknown`);
- missing DNS Guard watchdog (`dns_guard_watchdog_missing`);
- repeated DNS recovery/flapping (`dns_guard_recovery_flapping`);
- RouterCloud backup result is failed;
- RouterCloud backup age exceeds **26 hours** in current **Git source**, with an additional five-minute `for` window; its reference daily 21:30 timer and the 48-hour stale/failure lookbacks are source-aligned in [merged PR #250](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/250). **Production deployment of this rule is NOT independently confirmed** (last documented running Grafana on Oct 14 used 8h/24h);
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
All fifteen rules specify the `ASUS Edge Gateway Email` receiver, and the
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

DNS Guard v3.2 also exposes a coarse, privacy-safe machine-readable state through
`dns-guard metrics`. The Fedora-side `dns-guard-metrics` helper polls that state
over the existing SSH management path once per minute and imports only mode,
break-glass state, transition timestamps and a runtime fallback counter into
VictoriaMetrics. It does not export DNS names, client identities or query
history. The `dns_guard_sustained_failopen` rule warns only when bootstrap mode
persists for ten minutes and the most recent DNS Guard collection is younger
than three minutes, so stale pushed data cannot indefinitely masquerade as a
current fail-open state. The PR #197 five additional DNS Guard UIDs were verified **loaded** in
Grafana's database on 2026-10-08, and VictoriaMetrics returned fresh
bootstrap-health and watchdog-presence metrics. The final router healthcheck
passed after real power-cycle convergence. Per-rule Firing and actual inbox
delivery for these five new alerts are **not** claimed.
See [bounded v3.2 live acceptance](../docs/dns-guard-v3.2-recovery-audit-live-validation.md).

The live test is intentionally **not** part of normal CI because it mutates the
local metrics state and can generate real notifications:

```sh
./tests/test-grafana-routercloud-alerting-live.sh
```

**Issue #178 is CLOSED** after the 2026-10-12 bounded synthetic
`Firing → Normal → Resolved` notification test delivered to **Gmail and
Telegram**. The tested temporary rule was removed; the operator reported the
normal baseline of 15 rules. This is **not** proof of individual
`Firing/Resolved` delivery for every DNS Guard/RouterCloud rule.
Grouping/anti-flap behavior, safe source-versus-live provisioning parity for
Email+Telegram and default-policy persistence after reload remain **explicit
unverified follow-ups**. Do not store Telegram credentials or destination
identifiers in the repository to paper over provisioning drift.
See the [2026-10-12 alerting audit](../evidence/2026-10-12/grafana-alerting-routing-audit.md).

See [the original alerting validation evidence](../evidence/2026-09-27/grafana-alerting-validation.md),
the [WAN-speed e-mail validation](../evidence/2026-10-06/grafana-wan-speed-email-alert-validation.md),
and the [RouterCloud live alerting validation](../evidence/2026-10-07/grafana-routercloud-alerting-live-validation.md).

### 2026-10-12 Grafana and Loki live audit checkpoint

The operator-reported Fedora audit verified Alloy/Loki availability and
fresh log ingestion; 15/15 Grafana rules were unpaused, healthy, evaluated,
inactive and directly bound to a valid existing receiver. The **live**
Grafana contact contains one Email and one Telegram integration, and the
operator received contact-point **test notifications** through Gmail and
Telegram. The default policy initially named an unresolved `empty` receiver;
the operator changed it through the Grafana UI to
`ASUS Edge Gateway Email`. A subsequent authenticated read-only API audit
confirmed the default receiver and all 15 direct routes (`FINAL_ROUTING_AUDIT=PASS`).
The UI edit is a **real Grafana configuration change**, even though diagnostic
commands were read-only.

Source/live config drift remains unresolved: the tracked
`grafana/provisioning/alerting/asus-email-contact.yml` currently defines only
an Email integration, but the live API shows Email **and** Telegram. Never add
live destination identifiers or Telegram tokens to Git without a separate
secrets and provisioning design review. Grafana default-policy persistence
across a provisioning reload/restart was **not tested**.

Contact-point test messages alone are not full E2E evidence. A **separate
2026-10-12 controlled synthetic Grafana alert** (`E2E-TEST-2026-10-12`)
reached `Firing` with `vector(1)` / threshold 0.5 and automatically notified
both Gmail and Telegram (screenshots reviewed). After switching back to
`vector(0)`, the operator confirmed `Normal` and subsequent `Resolved`
messages on both channels. **Automatic firing, recovery and dual-channel
delivery: PASS within this temporary synthetic rule scope.** The temporary
rule was **deleted by the operator**, who confirmed exactly **15 rules
remain**. This completes the bounded synthetic E2E + cleanup acceptance
(operator-reported inventory count, no additional final API snapshot). Do not treat this as per-rule firing acceptance for all 15 rules.
The bounded 2026-10-07 RouterCloud test remains separate historical evidence. The Loki discard
metric was not exposed; matching sent/received counter snapshots must not be
reported as guaranteed zero loss. See
[dated sanitized observations](../evidence/2026-10-12/grafana-alerting-routing-audit.md)
and [worklog](../docs/worklog/2026-10-12.md).

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



## 2026-10-27 Grafana 13.3.0 / Loki 3.7.9 DNS-query follow-up

**Operator-reported Fedora production checkpoint; manual change, not an unattended-update authorization.** Grafana OSS was upgraded from `13.2.4-1` to `13.3.0-1.x86_64` using the official release RPM. The operator reported successful SHA-256 / RPM signature verification, `grafana-server=active`, `/api/health` with `database=ok` / `version=13.3.0`, and no priority-error entries in the checked post-restart Grafana journal. VictoriaMetrics was active and its health endpoint answered OK; Loki `3.7.9` was active and ultimately returned `/ready=200` after a transient startup-readiness state.

The provisioned **Pi-hole — Aktywność DNS v2** dashboard initially had a `Top 10 domen` panel failure for the last 24 hours: Loki's default `max_query_series=500` rejected the query. Shorter-range and selective JSON parsing tests alone did not solve the 24-hour limit. A controlled, operator-validated change to `limits_config.max_query_series: 1000` passed `loki -verify-config`, Loki readiness, live `/config` inspection and an actual 24-hour `topk(10, ...)` query (HTTP 200, 10 results). Both domain-ranking panels subsequently displayed data for the last 24 hours using their existing `| json` expressions; **no dashboard JSON change is required by this observation**. The reference Loki configuration here records the approved operator-reported setting.

The first deployment attempt rolled back safely because `/config?mode=diff` returned HTTP 500, *including with the original configuration*. Normal `/config` returned HTTP 200 and was used for the successful verification instead. The Loki rollback config was compared byte-for-byte with its backup; the successful deployment preserved the existing 168-hour retention. Post-check showed all Grafana, Loki and VictoriaMetrics services active. The Grafana alert scheduler loaded 15 rule definitions; the checked post-change journal query did not find matching evaluation-error messages. **Per-rule history, complete alert evaluation, and actual notification delivery were not independently validated**. Duplicate Loki/plugin paths were observed and deliberately left unchanged.

See [sanitized Grafana/Loki validation evidence](../evidence/2026-10-27/fedora-grafana-1330-loki-series-cap.md). No ASUS gateway, DNS Guard, Pi-hole, firewall, Caddy, automatic updating, retention or alert-provisioning changes are authorized by this note.
