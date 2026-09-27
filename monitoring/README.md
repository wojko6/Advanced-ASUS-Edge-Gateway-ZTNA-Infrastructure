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
