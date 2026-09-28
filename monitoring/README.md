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
[the case study](../docs/asus-tuf-ax5400-observability-case-study.md) and
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

Four live-validated Grafana alert rules are provisioned from
[`grafana/provisioning/alerting/asus-tuf-alerts.yml`](grafana/provisioning/alerting/asus-tuf-alerts.yml):

- SSH collector unavailable;
- router-reported WAN down;
- failed HTTPS / ICMP / router-DNS blackbox probe;
- stale router telemetry.

A controlled collector outage drove the collector and telemetry rules through
`Pending -> Firing`, while the independent blackbox rule remained healthy.
After the collector restarted, all rules returned to normal.

The same test identified an important dependency boundary: loss of collector
data must not masquerade as a WAN failure. The WAN rule therefore uses
`noDataState: OK`; collector and telemetry loss are handled by their dedicated
rules.

No external notification contact point is part of this baseline yet.

See [the alerting validation evidence](../evidence/2026-09-27/grafana-alerting-validation.md).

## Planned Pi-hole DNS activity extension

Issue #108 will extend this off-router pattern without changing the validated
monitoring baseline above.

The preferred future flow is:

```text
Pi-hole FTL query history on ASUS
        |
        | bounded read-only incremental extraction
        v
Fedora collector
        |
        v
Grafana Alloy -> Loki -> existing Grafana
```

This is intentionally separate from the VictoriaMetrics metrics pipeline and
from the syslog-ng mTLS system-log pipeline. Full domain names and client
identifiers must not become persistent high-cardinality Loki labels.

No Loki/Alloy DNS analytics deployment is claimed by this file yet. The initial
scope is limited to Pi-hole-visible DHCP-managed main-LAN traffic; resolver
coverage gaps remain documented in
[the analytics plan](../docs/network-dns-visibility-client-activity-analytics.md).

## Grafana interface language

Grafana 13 provides a built-in Polish interface option. The application UI
itself therefore does not require a custom translation patch.

This is separate from dashboard content: panel titles, descriptions, legends
and other strings stored in the project dashboard JSON are project-owned
content and were localized explicitly. The reference deployment therefore uses
the native Polish Grafana UI together with the project-localized Polish
TUF-AX5400 dashboard.
