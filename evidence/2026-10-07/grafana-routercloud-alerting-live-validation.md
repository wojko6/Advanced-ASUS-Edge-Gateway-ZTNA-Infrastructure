# Grafana RouterCloud alerting — live validation

**Date:** 2026-10-07  
**Scope:** issue #178 increment merged by PR #190  
**Environment:** Fedora-hosted Grafana + VictoriaMetrics for the ASUS Edge Gateway lab

## Goal

Validate the RouterCloud backup failure alert without causing a real backup
failure, and confirm that the live rule returns to a healthy state after the
synthetic condition is removed.

## Preconditions

The real RouterCloud backup state was healthy before fault injection:

- `LAST_RESULT=success`;
- `LAST_RC=0`;
- `LAST_STAGE=complete`;
- `last_over_time(routercloud_backup_last_run_success[24h]) = 1`;
- `last_over_time(routercloud_backup_last_rc[24h]) = 0`.

The provisioned rule `routercloud_backup_bad` evaluates
`last_over_time(routercloud_backup_last_run_success[24h])`, uses threshold
`< 1`, `for: 1m`, `noDataState: OK`, and routes to
`ASUS Edge Gateway Email`.

## Controlled fault

Only the coarse success metric was injected into the local VictoriaMetrics
instance with value `0`. No RouterCloud file data, credentials, SSH keys or
restic secrets were modified.

The live E2E test waited for Grafana to expose the rule as
`Alerting/Firing`. This avoids treating the generic
`ngalert.sender.router: Sending alerts to local notifier` log line as proof of
the alert state by itself.

## Recovery

The test restored the real metric from the existing RouterCloud backup
`status.env` via the project metrics publisher. The healthy metric returned to
`1`.

Recovery was accepted only when Grafana reported `Normal` or no active
`alert_instance` row for `routercloud_backup_bad`. The final direct database
check returned no active instance.

The live test installs an EXIT/HUP/INT/TERM cleanup trap that attempts to
restore the real metric even when the test is interrupted.

## Provisioning and regression checks

The same validation session confirmed:

- 9 Grafana alert rules in the source-controlled baseline;
- exactly 4 RouterCloud rules:
  - `routercloud_backup_bad`;
  - `routercloud_backup_stale`;
  - `routercloud_maintenance_bad`;
  - `routercloud_maintenance_stale`;
- all 9 rules route to `ASUS Edge Gateway Email`;
- repository alert provisioning equals the live Grafana provisioning;
- repository e-mail contact provisioning equals the live contact provisioning;
- resolved notifications remain enabled;
- `tests/test-static.sh` passes;
- shell syntax and staged diff checks pass.

PR #190 was merged to `main` as commit
`c43a760d076998196367ba7e4d1d51b1aeef76b4`.

## Claim boundary

This validation proves the controlled `routercloud_backup_bad`
`healthy -> Firing -> recovered` rule path and its routing into the existing
Grafana notification path.

It does **not** claim that:

- a real RouterCloud backup was intentionally broken;
- a separate RouterCloud alert e-mail was captured in the inbox during this
  session;
- `routercloud_backup_stale`, `routercloud_maintenance_bad` or
  `routercloud_maintenance_stale` were individually fault-fired;
- grouping/anti-flap behavior has been fully validated;
- Telegram/mobile escalation is implemented.

Actual firing/resolved e-mail transport is established separately by the
2026-10-06 WAN-speed alert validation.
