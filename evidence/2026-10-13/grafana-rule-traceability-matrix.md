# Grafana alert traceability — source baseline / 2026-10-13

**Tracking:** [#236](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/236) (P2, open)  
**Evidence classification:** repository-source inventory + previously accepted dated evidence + 2026-10-13 operator-reported **read-only SQLite** inventory (UID/group/pause and field structure only; not a fresh API receiver/delivery acceptance).  
**No changes to production**, no test notifications sent, no DNS/RouterCloud/WAN failure injection, no Grafana service or provisioning reload.

## Source baseline and ownership

- Rule source: [`monitoring/grafana/provisioning/alerting/asus-tuf-alerts.yml`](../../monitoring/grafana/provisioning/alerting/asus-tuf-alerts.yml) (Git blob `8b683acbb0425cf1c53a6d39b0e8d1ad1ba31df8`).
- Exactly **15** source-controlled rules, one Grafana group `ASUS TUF-AX5400`, folder `Network`, evaluation interval `1m`, **0** source-paused rules.
- All 15 source rules use datasource UID `victoriametrics` with a per-rule direct receiver `ASUS Edge Gateway Email`; runtime state and runtime configuration must be checked separately.
- Source contact-point file: [`asus-email-contact.yml`](../../monitoring/grafana/provisioning/alerting/asus-email-contact.yml) — one Email integration, secrets externalized through `GF_SMTP_USER`. This does **not** reproduce the Email+Telegram integrations observed in the live Grafana API on 2026-10-12.
- Last documented **live** inventory (2026-10-12): 15 loaded/unpaused, 15 healthy/inactive at snapshot; 15 direct receivers; contact API displayed one logical contact point with Email and Telegram; UI-edited default policy pointed to the named receiver. See [audit](../2026-10-12/grafana-alerting-routing-audit.md). **2026-10-13 SQLite checks cover UID/group/pause but not these runtime health and contact-point/API routing claims.**
- Source YAML is not a statement that the live policy or integrations will persist after a provisioning reload/restart.

## Per-rule source and historic evidence matrix

All rules route in **source** to `ASUS Edge Gateway Email`. Notification policy overrides and live receiver contents require a fresh sanitized runtime audit. Threshold comparison is the Grafana threshold evaluator, not a claim about a live event.

| Rule UID / signal | Severity | Source comparator / pending `for` | Missing data | Per-rule status | Historic evidence / qualification |
|---|---|---|---|---|---|
| `tuf_collector_down` | critical | `lt 1`, `2m` | `Alerting` | PARTIAL | [Evidence](../../evidence/2026-09-27/grafana-alerting-validation.md) — Rule `Firing` and return to normal, 2026-09-27; notifications not tested |
| `tuf_wan_down` | critical | `lt 1`, `2m` | `OK` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `tuf_probe_failed` | warning | `lt 1`, `2m` | `Alerting` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `tuf_telemetry_stale` | warning | `gt 90`, `2m` | `Alerting` | PARTIAL | [Evidence](../../evidence/2026-09-27/grafana-alerting-validation.md) — Rule `Firing` and return to normal, 2026-09-27; notifications not tested |
| `tuf_wan_speed_degraded` | warning | `lt 900000000`, `3m` | `OK` | PARTIAL | [Evidence](../../evidence/2026-10-06/grafana-wan-speed-email-alert-validation.md) — Email `Firing` and `Resolved` PASS, 2026-10-06; Telegram on this rule untested |
| `dns_guard_sustained_failopen` | warning | `gt 0.5`, `10m` | `OK` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `dns_guard_bootstrap_unhealthy` | critical | `gt 0.5`, `2m` | `OK` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `dns_guard_telemetry_stale` | warning | `gt 180`, `5m` | `Alerting` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `dns_guard_state_unknown` | critical | `gt 0.5`, `2m` | `OK` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `dns_guard_watchdog_missing` | critical | `gt 0.5`, `2m` | `OK` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `dns_guard_recovery_flapping` | warning | `gt 0.5`, `2m` | `OK` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `routercloud_backup_bad` | warning | `lt 1`, `1m` | `OK` | PARTIAL | [Evidence](../../evidence/2026-10-07/grafana-routercloud-alerting-live-validation.md) — Rule `Firing` and recovered state PASS, 2026-10-07; per-rule inbox delivery not demonstrated |
| `routercloud_backup_stale` | critical | `gt 28800`, `5m` | `Alerting` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `routercloud_maintenance_bad` | critical | `lt 1`, `1m` | `OK` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |
| `routercloud_maintenance_stale` | warning | `gt 691200`, `30m` | `Alerting` | NOT_TESTED | No per-rule `Firing`/`Resolved` delivery evidence located |

**Status semantics:** `NOT_TESTED` means no individual managed rule firing/resolved proof available in the consulted evidence. `PARTIAL` denotes a proven subset: evaluation and/or one transport but not both Email and Telegram automatic `Firing` and `Resolved` for that rule. `PASS` is reserved for the complete explicitly scoped evidence chain; `WAIVED` requires recorded rationale. A healthy/inactive runtime snapshot is **not** equivalent to per-rule notification testing.

## Exact metric/probe expressions in source

| UID | VictoriaMetrics / PromQL signal |
|---|---|
| `tuf_collector_down` | `asus_wifi_exporter_up{job="asus_wifi_clients"}` |
| `tuf_wan_down` | `asus_router_wan_link_up{job="asus_wifi_clients"}` |
| `tuf_probe_failed` | `probe_success{job=~"internet_https&#124;internet_icmp&#124;internet_dns"}` |
| `tuf_telemetry_stale` | `time() - asus_wifi_exporter_last_success_unixtime_seconds{job="asus_wifi_clients"}` |
| `tuf_wan_speed_degraded` | `max(asus_router_wan_speed_bps{job="asus_wifi_clients"})` |
| `dns_guard_sustained_failopen` | `asus_edge_dns_guard_mode_bootstrap * (time() - asus_edge_dns_guard_collection_timestamp_seconds < bool 180)` |
| `dns_guard_bootstrap_unhealthy` | `asus_edge_dns_guard_mode_bootstrap * ((asus_edge_dns_guard_bootstrap_dns_healthy == bool 0) + (time() - asus_edge_dns_guard_bootstrap_dns_last_check_timestamp_seconds > bool 180)) * (time() - asus_edge_dns_guard_collection_timestamp_seconds < bool 180)` |
| `dns_guard_telemetry_stale` | `time() - asus_edge_dns_guard_collection_timestamp_seconds` |
| `dns_guard_state_unknown` | `(asus_edge_dns_guard_state_valid == bool 0) * (time() - asus_edge_dns_guard_collection_timestamp_seconds < bool 180)` |
| `dns_guard_watchdog_missing` | `(asus_edge_dns_guard_watchdog_present == bool 0) * (time() - asus_edge_dns_guard_collection_timestamp_seconds < bool 180)` |
| `dns_guard_recovery_flapping` | `(increase(asus_edge_dns_guard_fallback_transitions_runtime_total[15m]) > bool 2) * (time() - asus_edge_dns_guard_collection_timestamp_seconds < bool 180)` |
| `routercloud_backup_bad` | `last_over_time(routercloud_backup_last_run_success[24h])` |
| `routercloud_backup_stale` | `time() - last_over_time(routercloud_backup_last_run_timestamp_seconds[24h])` |
| `routercloud_maintenance_bad` | `last_over_time(routercloud_maintenance_last_run_success[30d])` |
| `routercloud_maintenance_stale` | `time() - last_over_time(routercloud_maintenance_last_run_timestamp_seconds[30d])` |

## Proven shared transport vs unproven individual routes

- On **2026-10-12**, a temporary independent `E2E-TEST-2026-10-12` rule triggered real Grafana `Firing` and automatic Gmail+Telegram delivery. Recovery to `Normal` and `Resolved` delivery on both channels were operator-confirmed; temporary rule removed, 15-rule baseline restored. See [routing audit](../2026-10-12/grafana-alerting-routing-audit.md).
- This proves **one temporary synthetic route**, not the 15 individual production rule paths. Do not upgrade the above statuses based on that shared test.
- Old WAN-speed Email `Firing/Resolved` and RouterCloud Backup BAD `Firing/recovery` findings are independently documented; they are not evidence of all channels.
- Source Email-only provisioning and 2026-10-12 live Email+Telegram are **not reconciled**. Treat controlled reload/restart persistence as `NOT_TESTED`.

## Operator-run read-only SQLite checks — 2026-10-13

The operator ran two **read-only** `sqlite3 mode=ro` checks on the live Fedora Grafana database, without service reload or notification tests:

- `LIVE_RULES=15`; `EXPECTED_RULES=15`; `MISSING_UID_COUNT=0`; `EXTRA_UID_COUNT=0`; `PAUSED_RULES=0`.
- All 15 expected UIDs reported `GROUP=MATCH`.
- The first script returned `RECEIVER=OTHER_OR_MISSING` for all 15, **but that result is not a proven routing failure**: it attempted `.get("receiver")` on a decoded JSON value without verifying object shape.
- The follow-up script verified `STORAGE=str`, `STRUCTURE=list` for **all 15** `alert_rule.notification_settings` values. Hence the earlier direct receiver check was **invalid for the observed representation**; the exact contents and interpretation of these arrays remain unknown.
- No raw JSON, recipient names other than the static source name, destination IDs, secrets, full labels, private paths or credentials were published in the result.
- The subsequent sanitized nested JSON scanner observed **all 15** rule settings as one-item lists (`ITEMS=1`), with **one** nested `receiver` field (`RECEIVER_KEYS=1`), exactly matching the configured source receiver `ASUS Edge Gateway Email` (`STATUS=MATCH`). Summary: `MATCH=15`, `TOTAL_RULES=15`, `DATABASE_MODIFIED=NO`.
- The initial `OTHER_OR_MISSING` finding is therefore **a script parsing false-positive**, not evidence of routing drift. **Configuration-level direct receiver name equality: PASS (15/15, operator-reported read-only SQLite).** Actual integration configuration, policy routing/overrides, contact-point persistence and individual end-to-end delivery remain separate gates.

**Live/source UID, group, pause state and nested direct receiver match: PASS (operator-reported).** This is a partial DB snapshot, not a fresh per-rule evaluation health or end-to-end notification audit.

## Next acceptance gates — safe sequence

1. Extend the **partial 2026-10-13 read-only Fedora SQLite inventory** (UID/group/pause/direct receiver already PASS) with loaded title, folder, thresholds, `for`, `noDataState` and runtime health/state; cross-check routing through the Grafana API where safe. Do not dump rule annotations, headers, secrets, local paths, addresses, or contact destination IDs.
2. Read-only inspect actual per-rule direct routing vs notification-policy fallback; inventory integration **types and counts only** (Email/Telegram). Determine configuration owner for contact point, default policy and secret storage without printing tokens.
3. Mark each path `NOT_TESTED`, `PARTIAL`, `PASS`, or `WAIVED` with timestamp and operator-confirmed delivery channel in a per-rule evidence ledger.
4. Design isolated/bounded negative fixtures for **stale telemetry**, **DNS Guard critical recovery route**, **grouping/repeat/anti-flap**, and receiver failure. **Explicit operator approval required** before live notification tests.
5. Review a safe Email+Telegram provisioning parity proposal and persistence test plan. **No blind reload/restart**, no overwriting manually configured Telegram credentials or default-policy edits.
6. After explicit approval and non-destructive testing, verify individual warning/critical paths and `Firing`/`Resolved` delivery, regression to exactly 15 permanent rules, and document gaps/waivers.

## Acceptance / non-claims

- `SOURCE_RULE_COUNT=15`; `SOURCE_PAUSED=0`; `SOURCE_DIRECT_RECEIVER_RESOLVED=15`.
- `FRESH_LIVE_2026_10_13=PARTIAL_UID_GROUP_PAUSE_RECEIVER_PASS`; `LIVE_NOTIFICATION_SETTINGS_JSON_TYPE=list`; `LIVE_RECEIVER_MATCH=15/15_PASS`; `PER_RULE_E2E_DELIVERY=UNVERIFIED`.
- `LIVE_EMAIL_TELEGRAM_PARITY=UNRESOLVED`.
- `PROVISIONING_RELOAD_PERSISTENCE=NOT_TESTED`.
- `ALL_15_PER_RULE_E2E=NOT_TESTED`.
- No live failure-injection, notifier send, service restart, config reload, or router mutation performed to create this document.
