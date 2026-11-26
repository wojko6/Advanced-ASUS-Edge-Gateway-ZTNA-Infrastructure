# Fedora VictoriaMetrics 1.154.1 — manual production upgrade (2026-10-21)

> **Evidence class:** operator-pasted terminal output from the Fedora 44 host, not an independent remote session, signed transaction log, or proof of other services' current state.

## Scope

A separately authorized, manual VictoriaMetrics upgrade from the previously reported `1.153.0` baseline to `1.154.1` was performed on the **Fedora monitoring host**, not on the ASUS router. The installer produced a local rollback and data-backup directory and performed an isolated `vmrestore` restore test before reporting the deployment successful.

The installed candidate corresponds to the VictoriaMetrics upstream release `v1.154.1`, published 2026-10-20 on GitHub. This documentation records **operator-reported deployment outputs**, not a new source-code or supply-chain audit.

## Captured result

| Signal | Operator-reported result |
| --- | --- |
| Restore | `RESTORE_TEST=PASS` |
| vmrestore restored bytes | `17100289` (approximately 17.1 MB) |
| vmrestore completion | `successfully shut down http server for metrics` |
| Upgrade | `DEPLOYMENT=PASS` |
| Reported new version | `VERSION=1.154.1` |
| Service | `SERVICE=ACTIVE` |
| HTTP endpoint | `HTTP_HEALTH=PASS` |
| Query API | `QUERY_API=PASS` |
| Metrics data configuration changed | `DATA_CONFIG_CHANGED=NO` |
| Other services restarted by installer | `OTHER_SERVICES_RESTARTED=NO` |

Private Fedora-local rollback and data-backup directory:

```text
/var/backups/victoriametrics/pre-1.154.1-20261021T171517Z-12452
```

The operator's excerpt showed `vmrestore` reporting that 17,100,289 bytes were restored in 0.112 seconds and zero bytes were deleted. No complete backup manifest, binary digests, independent restore-verification report, Prometheus scrape freshness measurements or Grafana rule evaluation data were supplied in the excerpt. The restore PASS reflects the executing script's reported acceptance conditions, not a broad disaster-recovery certification.

## Separation and follow-up

- **No ASUS mutation or restart** was part of this deployment.
- No syslog-ng, Tailscale, DNS Guard, Pi-hole, RouterCloud, Loki, Alloy, Caddy or Grafana restart was reported from this VictoriaMetrics installer.
- Earlier the same day, a **Fedora-only** DNS outage was resolved by disabling receipt of Tailscale DNS settings with `tailscale set --accept-dns=false`; the user then confirmed stable internet. This was independent of the VictoriaMetrics binary upgrade and must not be mistaken for an ASUS DNS Guard/Unbound regression or a Grafana/Loki change.
- The existing Fedora `homelab-update-check.timer` remains **check-only**; this manual update does not enable unattended installation or resolve the independent RouterCloud cross-UID coordination questions.
- Long-term metric ingestion freshness, cold-boot persistence and backup recovery during a real outage remain untested in this checkpoint.

**Outcome:** `VICTORIAMETRICS_LIVE_UPGRADE=PASS` within the bounded operator-reported postflight above.
