# RouterCloud Fedora-local backup and maintenance recovery — 2026-11-01

**Evidence:** operator-provided Fedora command output, manually inspected VictoriaMetrics metrics and operator-confirmed Grafana UI. This is a **sanitized day-scoped maintenance note**, not an automatic production change or a full-site health certification.

## Observed problem

- RouterCloud backup/maintenance alerting showed stale or failed execution history. The intended Fedora-local backup filesystem was not available at its expected mountpoint.
- The operator identified a commented-out persistent mount entry in `/etc/fstab` for the intended storage volume, and restored the reviewed mount configuration.
- **Cause boundary:** the missing mount explains the immediate local backup-target accessibility problem. The reason the entry became commented out, and any unrelated earlier failure, were **not established**. No conclusion about ASUS WAN/DNS, RouterCloud remote credentials or Tailscale failure follows.

## Operator recovery and validation

1. Restore and verify the correct Fedora-local storage mount; do not format, overwrite or guess device identities.
2. Perform manual backup and maintenance/check runs **only after** confirming the intended storage target.
3. Observe both systemd job results and the exported VictoriaMetrics last-run metrics.
4. Inspect the existing Grafana alert panel for expected normal status, rather than hiding or disabling alerts.

The operator reported the following bounded acceptance on November 1 (local CET):

| Validation | Observed result |
| --- | --- |
| Backup run around 22:05 | `success`, return code 0 |
| Maintenance/check around 22:08 | `success`, return code 0 |
| Restic repository check | 29 snapshots; 14 pack files checked, no reported errors |
| VictoriaMetrics backup | `last_run_success=1`; `last_rc=0` |
| VictoriaMetrics maintenance | `last_run_success=1`; `last_rc=0` |
| Grafana alert UI | Operator-confirmed expected state |

Snapshot and pack counts describe the **executed integrity check**, not completeness or restorability of every backup. Time-stamped metrics are a bounded local observation, not a perpetual job-success promise.

## Operational controls and remaining work

- Preserve and verify the actual `/etc/fstab` entry and disk identity **locally**; do not copy UUIDs, private mount paths or repository identifiers to this public record.
- Prefer a read-only mount/target and timer preflight **before** a future scheduled backup; investigate missing disks without destructive commands.
- Confirm the next scheduled backup and maintenance executions independently. This note does not establish a successful future timer run.
- A cold-boot persistence test, full data restore and extended alert soak were **not** demonstrated by these checks.
- No changes to ASUS production services, DNS Guard, Pi-hole, Unbound, router firewall, or AI model authority were performed as part of this local storage recovery.

**Status:** `FEDORA_ROUTERCLOUD_BACKUP_MAINTENANCE_BOUNDED_ACCEPTANCE=PASS`, `FULL_RESTORE=NOT_TESTED`, `ASUS_PRODUCTION_CHANGE=NO`.
