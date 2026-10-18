# Fedora Homelab Update — sanitized operator-observed results (2026-10-18)

> **Evidence class:** values transcribed from terminal output supplied by the operator in this session, plus explicitly confirmed external notification receipt. This file is a **sanitized summary**, not an exported journal, a signed log, a second independent execution, or an ASUS production test. The individual scripts and outputs are not included as runnable deployment instructions.

## Manual production operations on Fedora

| Operation | Reported observation | Confidence boundary |
| --- | --- | --- |
| Update Watch v1 | timer enabled/active; first check detected `grafana 13.2.4-1`; `PACKAGES_INSTALLED=NO` | check-only watchdog |
| Initial Grafana pilot attempts | v2.1 option syntax error; v2.2 fixed parser and stopped on `sqlite3` or mutable live tar | fail-closed, no upgrade at those gates |
| `sqlite` package | installed `sqlite-3.51.2-2.fc44.x86_64`, program `/usr/bin/sqlite3` | CLI dependency installed |
| Grafana Pilot v2.3 | `BACKUP_SERVICE_QUIESCE=PASS`, `SQLITE_INTEGRITY=PASS`, `BACKUP_VERIFICATION=PASS`, `DNF_TRANSACTION=COMPLETE`, `POST_HEALTH=PASS` | manual real package upgrade; no tested automatic rollback |
| Grafana postflight | `grafana-13.2.4-1.x86_64`, HTTP 200; `ALERT_RULES_TOTAL=15`, `ALERT_RULES_PAUSED=0`, `GRAFANA_ERROR_LOG_COUNT=0` | point-in-time database and health checks |
| Notifications | operator confirmed email and Telegram both working after upgrade | receipt of notifications, not individual test of all standing rules |
| Service states | `grafana-server`, `syslog-ng`, `loki`, `alloy`, `caddy` all `active` | point-in-time status |
| Grafana backup | `BACKUP_STATUS=COMPLETE` for v2.3 pilot | integrity checked; restoration **not** tested |

## Candidate and E2E gates

- DNF5 structured preflight: `DNF_CHECK_RC=0`, `DNF_JSON_CHECK=PASS`, `UPGRADE_COUNT=0` for **Restic/Caddy/syslog-ng**; not proof that other packages had no updates.
- Caddy: `CADDY_USER_VALIDATE=PASS`; local TLS/SNI: `TLS_PROBES_PASS=3`, `TLS_PROBES_REVIEW=0`, TLSv1.3. `CADDY_HTTPS_HTTP_E2E=NOT_TESTED_NO_HTTP_REQUESTS`.
- syslog-ng/Loki: `TCP_LISTEN_6514_COUNT=1`, `LOKI_HTTP=200`, `LOKI_SOURCE_LOGS_15M=721`; `SYSLOG_ROUTER_TO_LOKI_E2E=UNPROVEN_SOURCE_IDENTITY_NOT_VERIFIED`.
- Restic: both user backup units inactive on sample; Restic process count 0; profile/check/restore **not verified**. These are only snapshots.

## Laboratory timeline

| Test | Reported result |
| --- | --- |
| Engine v0.1 | `SELFTEST_TOTAL=10/10`; `CANDIDATE_COUNT=0`; `AUTO_DEPLOYMENT_GATE=HOLD` |
| Engine v0.2 | `SELFTEST_TOTAL=20/20`; `BACKUP_COORDINATION=HOLD_RACE_NOT_ELIMINATED` |
| Engine v0.3 | `SELFTEST_TOTAL=20/20`, `LOCKLAB_TOTAL=9/9`, same UID |
| Cross-UID v0.4 | `CROSS_UID_LOCKLAB_TOTAL=13/13` |
| Cooperative job v0.5 | `COOPERATIVE_JOB_TOTAL=15/15`; synthetic single process job |
| v0.6 descendantlab | `DESCENDANT_LAB_TOTAL=12/12`; `ACTUAL_ROUTERCLOUD_WRAPPERS_EXECUTED=NO` |
| v0.7 | `ENTRYPOINT_SPECIFIER_RESOLUTION=PASS` for both `%h` wrappers |
| v0.8 | `SELFTEST_TOTAL=10/10`, `LOCK_EXPR_LEXICAL_OVERLAP=YES_STATIC_ONLY` |
| v0.9 | `SELFTEST_TOTAL=10/10`, `LOCK_EXPR_EQUALITY=EQUAL_STATIC_ONLY`, `ACTUAL_LOCK_PATH_AND_INODE=NOT_VERIFIED` |

**Explicit non-results:** no shared root/user production lock, no production auto-installer, no full Restic restore, no full Caddy HTTPS HTTP test, no source-authenticated ASUS→Loki E2E, no live nonempty candidate preview in v0.2, no RouterCloud backup wrapper execution or edit, no ASUS contact.

**Safety:** no secrets, private IPs, Telegram Chat ID, SMTP destinations or full command lines from backup wrappers are published here.
