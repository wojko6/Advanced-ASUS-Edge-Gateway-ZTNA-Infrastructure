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
```

All HTTP listeners bind to `127.0.0.1`; the baseline does not expose the
monitoring stack to LAN or WAN.

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
