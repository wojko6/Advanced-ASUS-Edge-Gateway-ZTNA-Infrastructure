# Fedora VictoriaMetrics v1.156.0 — operator-reported production upgrade (2026-11-09)

> **Evidence class:** sanitized operator-provided Fedora terminal output, not independent host access or an off-host recovery test. **Scope:** separate Fedora 44 observability host; no changes to ASUS router, Pi-hole, Unbound, DNS Guard, RouterCloud or firewall.

## Verified preflight

- Old live `vm_app_version`: `v1.155.0`; systemd unit `/etc/systemd/system/victoriametrics.service`, run as dedicated `victoriametrics` user/group.
- Production executable `/usr/local/bin/victoria-metrics-prod`; data `/var/lib/victoria-metrics`; local HTTP `127.0.0.1:8428`; `-retentionPeriod=90d`; `-promscrape.config=/etc/victoriametrics/prometheus.yml`.
- Effective systemd stop settings: SIGTERM (`KillSignal=15`), `TimeoutStopUSec=30s`; unit also contains additional security restrictions. The version-controlled `monitoring/systemd/victoriametrics.service` is a **reference template**, not an identical copy of the deployed unit.
- Official GitHub artifact `victoria-metrics-linux-amd64-v1.156.0.tar.gz` checked against release SHA256 **`54409ea381db0316f0bf6f242c718bc498085eb1eb37520b73526e6d86891601`**: **PASS**. The extracted `victoria-metrics-prod -version` reported `v1.156.0`.
- Original production binary and preserved pre-upgrade copy both had SHA256 **`aca3c49816db88c0e48012772fcf2a94eb66aaccd925b35d397b8b6f7f40fb43`**.

## Backup, installation and outcome

| Gate | Operator-observed result |
| --- | --- |
| Preflight service / data volume | `active`; data directory `31M` |
| VictoriaMetrics snapshot | API `/snapshot/create` returned `status=ok`; `/snapshot/list` contained new snapshot |
| Previous executable + unit | Same-host backups, executable SHA256 matched |
| Stopped-service database backup | `32M` active data copied separately; `snapshots/` omitted; scrape config copied |
| Service stop | Cleanly stopped with systemd |
| Version installation | New binary installed, original service definition retained |
| Runtime verification | `vm_app_version{...short_version="v1.156.0"} 1`, `/health` passed, systemd `active` |
| Startup journal | Storage opened, `rowsCount=24025030`, `sizeBytes=26802880`, 7 static scrape targets added |
| Scrape API | `/api/v1/targets` seven `health=up`; `/api/v1/query?query=up` seven series, all value `1` |

Seven targets: `asus_wifi_clients`, `blackbox_exporter`, `internet_icmp`, `internet_dns`, `internet_https`, plus two `monitoring_http_health` targets (Grafana and VictoriaMetrics HTTP endpoints).

**Evidence boundary:** `up=1` indicates a successful scrape/Blackbox exporter response, **not necessarily** success of the ICMP/DNS/HTTPS probe itself; `probe_success` was not checked in the supplied results. Logs show storage open, not a historical data reconciliation. Backups and snapshot are on the **same filesystem**; no isolated restore, off-host backup verification, rollback rehearsal, long soak or end-to-end Grafana alert delivery was demonstrated. A binary downgrade also requires checking on-disk-format compatibility. No automatic update policy was changed.

**Verdict:** `VICTORIAMETRICS_1_156_0=PASS_BOUNDED`; `SCRAPE_UP=7_OF_7`; `PROBE_SUCCESS=NOT_CHECKED`; `OFFHOST_RESTORE=NOT_TESTED`; `ASUS_ROUTER_CHANGED=NO`.

[Worklog](../../docs/worklog/2026-11-09.md) · [Monitoring guide](../../monitoring/README.md) · [Fedora manual-update policy](../../docs/operations/fedora-homelab-automatic-updates.md)
