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

## Operator-run read-only Contact Point / default policy snapshot — 2026-10-13

A follow-up operator-run SQLite audit read `alert_configuration` in `mode=ro` with `query_only=ON`, parsed the latest selected Alertmanager configuration and reported **only sanitized counts and boolean matches**:

| Check | Operator-reported result |
|---|---|
| `RECEIVERS_TOTAL` (named receiver entries in parsed config) | `2` |
| `EXPECTED_CONTACT_FOUND` (`ASUS Edge Gateway Email`) | `True` |
| `EMAIL_INTEGRATIONS` within the matching receiver | `1` |
| `TELEGRAM_INTEGRATIONS` within the matching receiver | `1` |
| `OTHER_INTEGRATIONS` within the matching receiver | `0` |
| `DEFAULT_RECEIVER_MATCH` | `True` |
| `CONFIG_PARSE` | `PASS` |
| `DATABASE_MODIFIED` | `NO` |

**Interpretation:** The current database snapshot contains the expected receiver, one Email and one Telegram integration under that receiver, and a matching default-route receiver. Together with `LIVE_RECEIVER_MATCH=15/15_PASS` this establishes **read-only configuration-level routing parity for all rules and both integration types**. The count `RECEIVERS_TOTAL=2` reflects named receiver entries in that config snapshot; it must not be misreported as two integrations or two separately validated delivery routes. The other receiver entry was not investigated in this sanitized snapshot.

**Limits:** A database snapshot does **not** establish actual ongoing transport health, the ability to deliver all production alerts, exact effective routing with every policy override, file-provisioning ownership, or persistence after a reload/restart. The existing 2026-10-12 synthetic test supports delivery for one specific temporary route only. Source `asus-email-contact.yml` still provisions Email only, so source-versus-live **durability/parity gap remains OPEN**. No production change, contact test, notification send, or service restart was performed.

## Operator-run read-only grouping/default-route snapshot — 2026-10-13

An additional operator-run SQLite `alert_configuration` read (no write/reload) reported the following sanitized values:

| Parameter | Observed |
|---|---|
| `DEFAULT_ROUTE_PRESENT` | `True` |
| `GROUP_BY_COUNT` | `2` |
| `GROUP_BY_ALERTNAME` | `True` |
| `GROUP_BY_FOLDER` | `True` |
| `GROUP_WAIT` | `30s` |
| `GROUP_INTERVAL` | `5m` |
| `REPEAT_INTERVAL` | `4h` |
| `ROUTES_TOTAL` | `1` |
| `CHILD_ROUTES` / `CHILD_RECEIVER_OVERRIDES` | `0` / `0` |
| `AUDIT` / `DATABASE_MODIFIED` | `PASS` / `NO` |

**Interpretation:** The **default notification policy** has standard grouping by `alertname` and `grafana_folder`, a 30-second initial group wait, a 5-minute group update interval and a 4-hour reminder interval. This is **configuration evidence, not an anti-flapping runtime test**. Grouping by alert name/folder does **not** merge unrelated rules into a single group.

**Important routing boundary:** Per the [Grafana rule configuration documentation](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/), alert rules selecting a contact point **directly** do not use the notification-policy tree. The 15 production rules configure direct `notification_settings.receiver`; therefore the root-policy timing values cannot automatically be claimed as the **effective** per-rule timings. Each rule's own nested notification settings (keys such as `group_by`, `group_wait`, `group_interval`, `repeat_interval`) need a sanitized read-only inventory; no implicit inheritance is asserted.

**Next gate:** read only the types, timing values and group label *names* of the direct per-rule settings; never dump raw notification JSON or recipient details. Verify behaviour with an operator-approved bounded fixture later, without changing router/DNS production or flooding Email/Telegram.

## Direct rule notification settings — operator read-only SQLite check / 2026-10-13

A subsequent sanitized operator read of all fifteen `alert_rule.notification_settings` JSON arrays reports:

- `RECEIVER_MATCH=15`, `RULES_TOTAL=15`.
- `NO_EXPLICIT_OVERRIDES=15`: all fifteen matching receiver objects report `GROUP_BY=NOT_EXPLICIT`, `WAIT=NOT_EXPLICIT`, `INTERVAL=NOT_EXPLICIT`, `REPEAT=NOT_EXPLICIT`.
- `DATABASE_MODIFIED=NO`.

**Meaning:** the observed SQLite list items explicitly select the matching receiver but do not explicitly define their own grouping or timing values. **It does not mean notifications are ungrouped, disabled, or misrouted.** Nor does this observation alone prove effective timing/anti-flap behavior.

Grafana's [rule-level notification documentation](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/) states direct contact-point selection does not route through the notification-policy tree. Grafana's [upstream example provisioning file](https://github.com/grafana/grafana/blob/main/conf/provisioning/alerting/sample.yaml) also documents that unspecified direct rule notification timing fields use the corresponding **default policy setting** as their fallback. This is an important distinction: **fallback timing defaults are not proof that the alert routes through the default policy tree.** Local default-policy snapshot: group by `alertname` and `grafana_folder`, 30s/5m/4h. A live effective-config or controlled synthetic behavioral test is still required before marking anti-flap/grouping runtime delivery `PASS`.

**Recommended next work:** prioritize source-vs-live provisioning ownership and reboot/reload persistence risk (Email-only checked-in YAML vs Email+Telegram live) using only read-only, redacted file inventory. No live reload/restart or outbound message without explicit operator approval.

## Fedora local provisioning inventory — 2026-10-13 (structural-only)

The operator executed a read-only scan of files under `/etc/grafana/provisioning/alerting`. Reported results:

| Check | Observed |
|---|---|
| `YAML_FILES` | `3` |
| File 1: `contactPoints` / type markers | `True`; `EMAIL_TYPE_DECLARED=True`, `TELEGRAM_TYPE_DECLARED=True` |
| File 2: `groups` | `True`, no contact-point type markers |
| File 3: `contactPoints` / `groups` / `policies` | None found |
| `policies` / `resetPolicies` in all three | Not found |
| `FILES_MODIFIED` / `VALUES_OR_SECRETS_PRINTED` | `NO` / `NO` |

**Evidence boundary:** This was a **textual regex-based inventory**, not YAML parsing, runtime provenance verification, or proof the file was loaded. The live contact record separately contains one Email and one Telegram integration and a matching default receiver in Grafana SQLite, but that does not establish this local file as their source. The checked-in GitHub `monitoring/grafana/provisioning/alerting/asus-email-contact.yml` still declares **Email only**. Therefore the more precise finding is **repository file versus observed Fedora local file declaration drift**, not **Fedora local versus live Email/Telegram inconsistency**.

Neither a `policies` nor a `resetPolicies` declaration was found by the restricted textual scan. The UI-edited root policy is evidenced in Grafana DB, but its reproducibility in the repository remains unverified. Do not assume a Grafana restart necessarily resets this SQLite-backed policy; do not claim a clean-room restore could rebuild it, either.

Per [Grafana file provisioning documentation](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/), a provisioning reload/startup can modify resources, and provisioning a policy tree overwrites the whole policy tree; any solution requires a reviewed source-of-truth, secret-redaction and rollback. **No reload, restart or file copy was performed.**

**Next safe gate:** parse the local contact-point YAML (or mark parser missing); verify that Email and Telegram are receivers of the expected *same* named contact point, and assess secret handling and file permissions by boolean checks **without outputting token, chat ID, email address, file contents, or local paths**.

## Fedora local YAML parse, contact identity and permission audit — 2026-10-13

Operator executed PyYAML `safe_load` in read-only mode on the three locally present alerting YAML files:

| Observation | Reported |
|---|---|
| `YAML_FILES` and parsability | 3; `YAML_PARSE=PASS` for each |
| Expected contact-point name | `EXPECTED_CONTACT=MATCH`; `EXPECTED_CONTACT_DEFINITIONS=1` |
| Receiver types in that contact | `EMAIL_RECEIVERS=1`, `TELEGRAM_RECEIVERS=1` |
| Telegram token representation | `TELEGRAM_TOKEN_MODE=ENV_REFERENCE` |
| Contact YAML group-readable / other-readable | `True` / `True` |
| `POLICIES_DEFINED` across the three files | `False` |
| `FILES_MODIFIED` / `SECRETS_PRINTED` | `NO` / `NO` |

**Accepted limited finding:** Locally installed alerting YAML parses and contains exactly one contact definition with both Email and Telegram receivers under the expected name. The checked Telegram bot token is written as an environment-variable reference (not an inline literal in the tested key). A 2026-10-13 live database snapshot separately shows this logical contact and both types, consistent with—but not conclusive proof of—these particular file resources having been loaded. No file-reload/startup reapplication test occurred.

**Security caveat:** The contact YAML is readable by the filesystem group and other users. That alone is not proof of a token leak because the examined token uses an environment reference, but **other fields** (Telegram chat ID, email destination, API URLs/keys, variables expansion behavior) and the referenced variable's actual storage/perms are **not yet audited**. Do not publish the local YAML or apply permission changes blindly; assess only presence/modes and secret *reference-vs-inline* classification without disclosing contents. File-provisioning environment expansion is [documented by Grafana](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/).

**Remaining drift:** The public GitHub contact provisioning file remains Email-only. The observed Fedora local file includes Telegram; source-of-truth consistency and local secret/environment persistence remain open. UI-edited default-policy routing is stored in Grafana database but no YAML `policies` declaration was found: clean-room restoration of that policy is also unproven. Keep `PROVISIONING_RELOAD_PERSISTENCE=NOT_TESTED`, `ANTI_FLAP_DELIVERY=NOT_TESTED` and `ALL_15_PER_RULE_E2E=NOT_TESTED`.

## Fedora secret-reference check — operator-reported read-only / 2026-10-13

A narrowly scoped operator-run PyYAML audit of the matching local Contact Point reported:

| Key or file property | Result |
|---|---|
| `EXPECTED_CONTACT` | `FOUND` |
| `EMAIL_ADDRESSES` | `ENV_REFERENCE` |
| `TELEGRAM_BOTTOKEN` | `ENV_REFERENCE` |
| `TELEGRAM_CHATID` | `INLINE_VALUE` |
| `FILE_OTHER_READABLE` | `True` |
| `SECRET_VALUES_PRINTED` / `FILES_MODIFIED` | `NO` / `NO` |

**Finding GRAFANA-236-P1 (privacy/configuration hardening, not a confirmed exploit):** the Telegram chat identifier is a literal in a locally world-readable YAML file. A chat ID is a destination identifier, **not** equivalent to the Telegram bot token or an authentication credential; this is still unnecessary disclosure to local accounts and incompatible with publishing an otherwise portable sanitized source configuration. The bot token and e-mail addresses are stored as environment references in the inspected YAML fields, but the backing variables, actual runtime value injection and their storage permissions **have not yet been checked**. No exfiltration or unauthorized access was observed.

**Desired state:** preserve one Email and one Telegram receiver under the current Contact Point name; represent `settings.chatid` as a dedicated environment reference (e.g. `$GRAFANA_TELEGRAM_CHAT_ID`), store the actual chat ID in a private host-managed environment source with least-privilege file ownership/mode, and keep all destination IDs and tokens out of Git and logs. Grafana officially supports [environment interpolation in alerting provisioning properties](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/), including receiver settings. An undefined variable can become an empty value, so **do not modify the live YAML, restart or reload Grafana until the variable source, backup, rollback and stage tests are verified**. Review the necessity of world-readable YAML only after establishing Grafana service read permissions; do not blindly `chmod` a provisioned file.

**Status:** `LOCAL_YAML_PRIVACY_GAP=OPEN`; `CONTACT_CHAT_ID_INLINE=TRUE`; `CONTACT_YAML_OTHER_READABLE=TRUE`; `BOT_TOKEN_INLINE=FALSE` (in checked field only); `SECURE_ENV_SOURCE_PERMISSIONS=UNVERIFIED`; `SOURCE_RECONCILIATION=PENDING`; `PROVISIONING_RELOAD_PERSISTENCE=NOT_TESTED`.

## systemd EnvironmentFile ownership and mode audit — operator-reported / 2026-10-13

The operator corrected an audit-script unpacking error and ran a sanitized **read-only** `systemctl show grafana-server --property=EnvironmentFiles` plus `os.stat` inspection. Four files were present, all owned by root; none was group-/other-writable:

| Ordered env file | Mode | Root-owned | Group-readable | Other-readable | Group-/other-writable |
|---|---|---|---|---|---|
| 1 | `0644` | yes | yes | yes | no |
| 2 | `0600` | yes | no | no | no |
| 3 | `0600` | yes | no | no | no |
| 4 | `0640` | yes | yes | no | no |

Reported: `SYSTEMD_QUERY=PASS`; `ENVIRONMENT_FILES=4`; `ENV_VALUES_READ=NO`; `ENV_VALUES_PRINTED=NO`; `CONFIG_MODIFIED=NO`.

**Risk interpretation:** File 1 is readable by other local accounts; whether this represents sensitive exposure **depends on the assignments inside it** and remains `PENDING_KEY_ONLY_AUDIT`. It must not be labeled a confirmed credential leak. The exact owning group of File 4 and its members have not yet been audited. Root-only `0600` and root-owned `0640` with a suitably narrow group are typical restricted-file postures; no `chmod`, move or service restart is approved by this evidence.

**systemd semantics:** `EnvironmentFile` data is loaded by the service manager at service execution and multiple files are processed in order; later assignments override earlier assignments. File read permissions alone are not proof of what the already-running Grafana process received. Per [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html), environment variables should not be considered a full secret-isolation mechanism; review the effective service/exposure boundary separately without revealing values.

**Next safe gate:** key-name-only inventory (never emit values) of all four files, distinguish ordinary distro defaults from sensitive-looking assignments in world-readable File 1, check which source defines the variable names referenced in Grafana YAML and its *last effective definition*, and check File 4 group access. Preserve all four files, ensure no unrelated services are modified and avoid printing tokens, chat IDs or recipient addresses.

## systemd environment name-source mapping — operator-reported / 2026-10-13

The read-only operator check scanned **variable names only** (the variable values were read locally but not printed; no environment data was sent in the output), correlating Grafana Contact Point references to ordered systemd `EnvironmentFile` entries:

| Source | Mode | Variables | Sensitive-looking *names* | World-readable | Notes |
|---|---|---:|---:|---|---|
| ENV 1 | `0644` | 12 | 0 | yes | No matching names found by heuristic; **not proof content is non-sensitive** |
| ENV 2 | `0600` | 8 | 8 | no | Referenced email destination last defined here |
| ENV 3 | `0600` | 1 | 1 | no | Referenced Telegram bot token last defined here |
| ENV 4 | `0640` | 1 | 1 | no | File's owner group matches `grafana`; the specific variable/consumer remains unidentified |

Check result: `EMAIL_ENV_REFERENCE=True`, `EMAIL_DEFINED_IN_FILES=True`, `EMAIL_LAST_FILE_INDEX=2`, `EMAIL_LAST_SOURCE_WORLD_READABLE=False`; likewise `TELEGRAM_TOKEN_ENV_REFERENCE=True`, `TELEGRAM_TOKEN_DEFINED_IN_FILES=True`, `TELEGRAM_TOKEN_LAST_FILE_INDEX=3`, `TELEGRAM_TOKEN_LAST_SOURCE_WORLD_READABLE=False`. `VALUES_PRINTED=NO`, `FILES_MODIFIED=NO`, `SERVICES_RESTARTED=NO`.

**Risk conclusion:** no world-readable source is reported for the two referenced Email/Telegram bot token variables, and ENV 4 is readable by the `grafana` group but not by other users. The world-readable ENV 1 still merits a limited content/meaning review rather than automatic `chmod`: heuristic checking of variable **names** cannot prove its **values** harmless. The currently deployed YAML remains world-readable with an **inline Telegram chat ID**, which is a destination identifier (not a bot authentication token); this is the immediate privacy-hardening candidate.

**Planned remediation gate:** first check whether any existing private env file contains a usable chat-ID variable **by key name only**, then stage a fresh environment-reference version of Telegram `settings.chatid`. Ensure the referenced variable will be non-empty in the service launch environment; Grafana [replaces absent interpolation values with an empty string](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/). Keep all staged backups private, retain the current receiver UID and both integrations, and do not restart/reload production until separately approved with rollback and test notifications. A clean-room reprovisioning approach should also address the UI-edited policy.

## Telegram Chat ID variable-name preflight — 2026-10-13

Operator checked **all four** current Grafana `EnvironmentFile` entries for variable *names* containing `TELEGRAM`, `CHAT` and `ID`, without printing values:

| File index | Matching variable-name count |
|---|---:|
| ENV 1 | 0 |
| ENV 2 | 0 |
| ENV 3 | 0 |
| ENV 4 | 0 |
| **Total** | **0** |

Reported `EXISTING_CHATID_VARIABLE_CANDIDATES=0`, `VALUES_PRINTED=NO`, `FILES_MODIFIED=NO`, `SERVICES_RESTARTED=NO`.

**Scope:** A naming heuristic found no apparent Chat ID variable in these `EnvironmentFile` assignments. It does not rule out a differently named variable or values sourced via a service `Environment=`, manager environment or another mechanism. The already-reviewed local YAML explicitly stores Telegram `settings.chatid` inline.

**Staged remediation proposal (not applied):**

1. Adopt `GRAFANA_TELEGRAM_CHAT_ID` as a **new exact variable name**, after checking name collision, and retain the current working Telegram receiver UID/settings and current email receiver configuration.
2. Store the existing destination ID only in a protected, root-managed `EnvironmentFile` (typically `0600`), supplied to the Grafana service through a reviewed systemd drop-in or carefully reviewed existing file. Keep actual value, private destination and backups outside public Git/logs.
3. In the reviewed/local contact YAML, replace just Telegram `settings.chatid` literal with `$GRAFANA_TELEGRAM_CHAT_ID` and preserve existing Telegram bot-token reference, receiver UID and optional settings. Validate YAML syntax and variable availability using **sanitized** checks.
4. Publish a *sanitized* Email+Telegram provisioning specification in Git only after comparing all source-required nonsecret receiver fields and validating schema; never copy the live YAML verbatim. Keep the default-policy recreation/clean-room restore plan separately reviewed.
5. Have a backup+rollback, validate a safe staging load, and obtain **explicit operator authorization** before changing production files or reloading/restarting Grafana. Avoid any test notification without its own approval.

Grafana documentation confirms `contactPoints[].receivers[].settings.chatid` is the Telegram Chat ID and supports `$VARIABLE` interpolation; **missing variables are replaced with an empty string** ([provisioning documentation](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/)), so uncoordinated changes can silently break Telegram delivery. `ENV_VAR` expansion details also caution against unescaped dollar-sign templates in provisioned fields; review the interpolated result privately before a live reload.

`CHAT_ID_ENV_PREFLIGHT=NO_MATCHING_NAME`; `PROPOSED_NAME=GRAFANA_TELEGRAM_CHAT_ID`; `REMEDIATION=DESIGN_ONLY`; `PRODUCTION_MODIFIED=NO`.

## Telegram Chat ID dry-run — operator reported / 2026-10-13

An in-memory, read-only transformation of the **actual local contact provisioning YAML** yielded:

| Assertion | Result |
|---|---|
| `CONTACT_UNIQUE` | `PASS` |
| `EMAIL_COUNT` / `TELEGRAM_COUNT` | `1` / `1` |
| `RECEIVER_UIDS_UNIQUE` / `RECEIVER_UIDS_PRESENT` | `True` / `True` |
| `CHATID_PRESENT` / `CHATID_INLINE` / `CHATID_NUMERIC` | `True` / `True` / `True` |
| `DRAFT_YAML_VALID` | `True` |
| `ONLY_CHATID_CHANGED` | `True` |
| `DRAFT_WRITTEN_TO_DISK` / `SECRET_VALUES_PRINTED` / `PRODUCTION_MODIFIED` | `NO` / `NO` / `NO` |

**Scope:** in-memory PyYAML deep-copy replaced only the Telegram receiver's inline `settings.chatid` with `$GRAFANA_TELEGRAM_CHAT_ID`, then parsed its serialized YAML and reconstructed the exact original structure by restoring the old in-memory value. **PASS applies to YAML structure preservation only**, not variable interpolation, systemd service readiness, delivery, runtime persistence or the safety of applying this to production.

**Deployment gating:** No chat ID env var is currently known by the checked four `EnvironmentFile` sources. Prepare a private root-owned env source, verify variable presence/nonempty and Grafana's actual interpolation in a disposable isolated test; preserve existing receiver UIDs, create private rollback snapshot and obtain operator approval **before** any live YAML change, reload/restart, or test notification. Do not publish real Chat ID or Telegram token, including in test fixture logs.

## Secure host-only staging completed — operator-reported / 2026-10-13

The corrected **V2** staging routine ran successfully on Fedora after an initial **V1 unpacking exception** (`matches` was a one-item list; the corrected script used `matches[0]`). The V1 failure occurred before staging creation; there is no evidence of production changes by either version.

Sanitized V2 result:

| Validation | Operator result |
|---|---|
| `CONTACT_UNIQUE` | `PASS` |
| Email and Telegram receiver checks | `PASS` / `PASS` |
| `RECEIVER_UIDS_PRESERVED` | `PASS` |
| `CHATID_NUMERIC` | `PASS` |
| `CHATID_NEGATIVE` | `False` |
| `ONLY_CHATID_CHANGED` / `DRAFT_YAML_VALID` | `PASS` / `PASS` |
| Private staging directory mode | `0700` |
| `contact-original.yml`, `contact-candidate.yml`, `telegram-chatid.env` | all root-owned, `0600` |
| `STAGING_READY` | `PASS` |
| Active Grafana YAML/systemd edits | `NO` / `NO` |
| Service restart / notifications sent | `NO` / `NO` |
| Secret values printed | `NO` |

**Host-only artifacts (not public):** `/root/grafana-236-staging/contact-original.yml` (exact bytes of source YAML), `contact-candidate.yml` (draft YAML with Telegram Chat ID variable reference), and `telegram-chatid.env` (new `GRAFANA_TELEGRAM_CHAT_ID` assignment with **real numeric destination ID**). The environment assignment file is sensitive even though a Chat ID is not a bot credential. Do not copy it or either original/candidate YAML (which can contain private receiver metadata) into a public Git repository.

**Meaning:** staged rollback copy, candidate and private env file exist with restrictive filesystem permissions; the corrected preparatory script verified YAML structure and only the Chat ID field change. The candidate has **not** been loaded by Grafana. Root-owned backup and private env file existence alone do **not** establish service environment injection, alert receiver provisioning API compatibility, proper interpolation or Firing/Resolved delivery.

**Next gate:** execute a read-only consistency check: verify mode/owner and file types, that staged original matches the live source byte-for-byte, the new variable name has not been added to current systemd environment sources, and that injecting the staged value into a *copy in memory* reconstructs the original parsed YAML. Do not output the secret value or file contents. Isolated Grafana interpolation/provisioning testing and a reviewed rollback procedure are required before a production change.

`SECURE_STAGING=PASS`; `HOST_ONLY_ROLLBACK_COPY=CREATED`; `CHAT_ID_ENV_STAGE=CREATED_NOT_ACTIVATED`; `ACTIVE_YAML_MODIFIED=NO`; `SYSTEMD_MODIFIED=NO`; `GRAFANA_RELOADED=NO`; `PER_RULE_E2E_DELIVERY=UNVERIFIED`.

## Staging integrity readback — operator-reported / 2026-10-13

An additional read-only staging-integrity audit returned **twelve PASS assertions**:

| Assertion | Result |
|---|---|
| Private staging directory `0700`, root-owned | `PASS` |
| Original YAML, candidate YAML, Chat ID environment file: regular, root-owned `0600`, link count 1 | `PASS` for each |
| Staged Contact Point unique | `PASS` |
| Staged Telegram receiver unique | `PASS` |
| Environment assignment format | `PASS` |
| Staged env value equals original Chat ID | `PASS` |
| Candidate references exactly `$GRAFANA_TELEGRAM_CHAT_ID` | `PASS` |
| Reconstructing staged original by restoring Chat ID field only | `PASS` |
| Unique matching live contact YAML | `PASS` |
| Original backup bytes match the current live YAML | `PASS` |

Reported final fields: `STAGING_INTEGRITY=PASS`, `GRAFANA_FILES_MODIFIED=NO`, `SYSTEMD_MODIFIED=NO`, `SERVICES_RESTARTED=NO`, `NOTIFICATIONS_SENT=NO`, `SECRET_VALUES_PRINTED=NO`; `GRAFANA_RUNTIME_INTERPOLATION=NOT_TESTED`; `PRODUCTION_DEPLOYMENT=NOT_STARTED`.

**What this proves:** the original YAML backup is byte-identical with live local source *at the audit time*; the draft changes only the Telegram Chat ID field; the staged environment assignment supplies the same numeric destination value; file modes and ownership are constrained. It does **not** prove the stage can be read by the running Grafana process; the staged env file is **not attached to the service**, and neither Grafana's contact-point parser nor delivery was exercised.

**Next bounded step:** collect **read-only Grafana version, installed binary, systemd run-as user/group, homepath and isolation prerequisites** without printing environment content. Then build a fully isolated local scratch Grafana experiment using **synthetic** Email and Telegram credentials, synthetic Chat ID, a separate database, no alert rules and no network notification transport, so interpolation/receiver-schema behavior can be tested independently of production. Avoid running production Grafana against the staged real-contact YAML, switching live EnvironmentFiles or reloading live provisioning without separate operator approval.

## Installed Grafana and isolated-test preflight — 2026-10-13

The operator ran read-only Fedora preflight checks and reported:

| Check | Result |
|---|---|
| `GRAFANA_BINARY_FOUND` | `True` |
| `GRAFANA_VERSION` | `13.2.3` |
| `VERSION_CHECK_RC` / `SYSTEMD_QUERY_RC` | `0` / `0` |
| `SERVICE_ACTIVE` / `SERVICE_RUNNING_PID` | `True` / `True` |
| `SERVICE_USER_GRAFANA` / `SERVICE_GROUP_GRAFANA` | `True` / `True` |
| `GRAFANA_DEFAULTS_PRESENT` / `GRAFANA_CONFIG_PRESENT` | `True` / `True` |
| `PODMAN_AVAILABLE` / `DOCKER_AVAILABLE` | `True` / `True` |
| `PRODUCTION_CONFIG_MODIFIED` / `SERVICES_STARTED_OR_STOPPED` / `FILES_CREATED` / `NOTIFICATIONS_SENT` | All `NO` |

**Interpretation:** prerequisites exist for testing a separate Grafana instance, but a matching cached container image and working container daemon/user permissions have **not** been verified. Installed Grafana v13.2.3 is the host version; it does not imply any local container image at that version. Avoid downloading a different image without review.

**Safest next sequence:** read-only `podman images`/`docker images` inventory (report only Grafana image counts and a matching-version boolean; do not output unrelated image names), choose an already local compatible image, then construct test-only data and environment artifacts in a separate disposable scratch volume. Start isolated runtime with `--network none`, **no host-published port**, no host Grafana SQLite, service configuration, live contact YAML or real Telegram secrets mounted. Use placeholder Email/token/chat ID, no alert rules, and no outbound notification attempt. Explicitly validate parsed receiver types, correct Chat ID expansion, and non-empty value in the **test** service; no live reload/restart.

**Upstream caution:** [Grafana issue #69950](https://github.com/grafana/grafana/issues/69950) reports a prior YAML numeric coercion failure with negative Telegram Chat IDs (reported for an older Grafana version); this remains a reason to test the actual runtime separately and does not prove that v13.2.3 is affected. The operator-reported real Chat ID is nonnegative, but it must still not be echoed or sent. The official [alerting file provisioning docs](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/) explain variables can be interpolated from the environment and must be checked after provisioning.

`ISOLATED_TEST_PREFLIGHT=PASS`; `GRAFANA_HOST_VERSION=13.2.3`; `CACHED_MATCHING_IMAGE=UNKNOWN`; `ISOLATED_GRAFANA_RUNTIME=NOT_STARTED`; `PRODUCTION_UNTOUCHED=YES`.

## Local Grafana OCI image availability — operator-reported / 2026-10-13

The operator checked cached Grafana image tags on Fedora without pulling images or starting containers:

| Engine | Read-only query | Grafana images | Exact `13.2.3` |
|---|---|---:|---:|
| Podman | `IMAGE_QUERY=PASS` | `0` | `0` |
| Docker | `IMAGE_QUERY=FAILED` | unknown | unknown |

Reported safety: `IMAGES_DOWNLOADED=NO`, `CONTAINERS_STARTED=NO`, `PRODUCTION_CHANGES=NO`.

**Interpretation:** No cached Grafana image was found in the queried Podman image store. Docker query failure is **not** proof that Docker lacks an image; no assumption about its daemon/permissions should be made from this result. An exact-version Podman container test is not immediately available without acquiring or building an image; avoid silently switching to a different Grafana version and attributing test results to host `13.2.3`.

**Next proposed route without image download:** Use the **already installed Grafana 13.2.3 binary**, but only in a separate transient systemd unit with a verified `PrivateNetwork=yes` network namespace and restricted filesystem access (`ProtectSystem=strict`, explicit private writable scratch paths, no production `/etc/grafana/grafana.ini` or `/etc/grafana/provisioning` access). First run an innocuous *non-Grafana* transient sandbox preflight to verify OS support for these restrictions. Then prepare a synthetic contact-only provisioning fixture and an empty SQLite DB in isolated directories, with SMTP disabled, no real alert rules/credentials/chat IDs, no published host port, and explicit shutdown/cleanup. Do not proceed to Grafana runtime with any failed preflight or missing control. 

Grafana documents independent provisioning/data paths and config controls ([Configure Grafana](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/)); systemd documents isolated network namespace and restricted host filesystem ([systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)).

`LOCAL_PODMAN_GRAFANA_IMAGE=ABSENT`; `DOCKER_IMAGE_INVENTORY=UNVERIFIED`; `ISOLATED_HOST_BINARY_TEST=NOT_STARTED`; `PRODUCTION_UNTOUCHED=YES`.

## systemd isolated-host smoke preflight — operator-reported / 2026-10-13

A transient systemd unit ran a **non-Grafana** Python isolation test. The first attempt stopped due to an assistant-authored Python quoting error in a status `f`-string (`PASS` was interpreted as a symbol); this was **a test-script failure, not evidence of a sandbox policy failure**. The corrected `--pipe` + heredoc V2 test reported:

| Assertion | V2 |
|---|---|
| `DYNAMIC_USER` | `PASS` |
| `NETWORK_LOOPBACK_ONLY` | `PASS` |
| `ROOT_FILESYSTEM_READONLY` | `PASS` |
| `PRODUCTION_CONFIG_HIDDEN` | `PASS` |
| `PRODUCTION_DATABASE_HIDDEN` | `PASS` |
| `PRIVATE_STAGING_HIDDEN` | `PASS` |
| `ISOLATION_PREFLIGHT` | **`PASS`** |

The V2 test used `DynamicUser=yes`, `PrivateNetwork=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `PrivateDevices=yes`, `NoNewPrivileges=yes`, and `InaccessiblePaths=/etc/grafana /var/lib/grafana`, in a transient `systemd-run --pipe --wait --collect` unit. The operator explicitly reported `PRODUCTION_GRAFANA_STARTED_OR_STOPPED=NO`, `PRODUCTION_CONFIG_MODIFIED=NO`, `NOTIFICATIONS_SENT=NO`, `SECRETS_READ=NO`.

**Evidence boundary:** This proves isolation primitives were effective in the corrected test process; it does not prove the Grafana runtime will start correctly, that provisioning will parse its test-only fixture, or that a production restart/reload is safe. Next test may start a **separate sandboxed host-binary Grafana** in a transient unit, with `RuntimeDirectory` scratch-only configuration/SQLite DB, synthetic Email/Telegram credentials and chat ID, no alert rules, `PrivateNetwork=yes`, no host port publish, and no production paths available.

`SYSTEMD_ISOLATION_V2=PASS`; `GRAFANA_SANDBOX_RUNTIME=NOT_STARTED`; `PRODUCTION_UNTOUCHED=YES`.

## Grafana 13.2.3 isolated synthetic provisioning runtime — operator-reported / 2026-10-13

The user ran a short-lived second Grafana instance from the installed **13.2.3 host binary** inside a transient systemd service, without downloading a container image. The sandbox enforced `DynamicUser=yes`, `PrivateNetwork=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `PrivateDevices=yes`, `NoNewPrivileges=yes` and `InaccessiblePaths=/etc/grafana /var/lib/grafana /root`. A dedicated `RuntimeDirectory` held its configuration, temporary SQLite database, logs and test-only provisioning. The service listened only on loopback **within the private network namespace**. The fixture defined one fake Email and one fake Telegram receiver, with synthetic recipient, bot token and numeric Chat ID. SMTP and update checks were disabled; the fixture contained **no alert rules**, and no notification was sent.

| Operator-printed check | Result |
|---|---|
| `PRIVATE_NETWORK` | `PASS` |
| `DYNAMIC_USER` | `PASS` |
| `PRODUCTION_CONFIG_HIDDEN` / `PRODUCTION_DB_HIDDEN` | `PASS` / `PASS` |
| `SCRATCH_DIRECTORY` / `GRAFANA_BINARY` | `PASS` / `PASS` |
| `ISOLATED_GRAFANA_READY` | `True` |
| `CONTACT_API_READ` | `PASS` |
| `EMAIL_PROVISIONED` | `True` |
| `TELEGRAM_PROVISIONED` | `True` |
| `TELEGRAM_CHATID_INTERPOLATED` | `True` |
| **`SYNTHETIC_PROVISIONING`** | **`PASS`** |
| `SYNTHETIC_DATA_ONLY` / `REAL_SECRETS_USED` | `YES` / `NO` |
| `SMTP_DISABLED` / `NO_ALERT_RULES` | `YES` / `YES` |
| `PRODUCTION_FILES_MODIFIED` / `PRODUCTION_SERVICES_RESTARTED` / `NOTIFICATIONS_SENT` | **All `NO`** |

**Evidence meaning:** Grafana v13.2.3, not just PyYAML, actually accepted a Contact Point containing two integrations and expanded a synthetic `$GF236_TEST_CHAT_ID` value; its provisioning API returned the expected numeric-string Chat ID. The transient process terminated through the test's `finally` handler. This is strong evidence of **mechanism/schema compatibility for synthetic data**, **not** proof that the real `GRAFANA_TELEGRAM_CHAT_ID` will be supplied to the production service, that the active YAML will apply without drift, or that post-change Email/Telegram Firing and Resolved delivery will succeed. No negative Chat ID was tested; operator's actual Chat ID was previously reported nonnegative.

**Next gate:** keep the production service unchanged while confirming the staged original still matches live source, `GRAFANA_TELEGRAM_CHAT_ID` is not defined by a conflicting current service assignment, and Grafana is healthy. Develop a reviewed, private and atomic deployment/rollback plan covering: root-only env source, explicit systemd `EnvironmentFile` loading, one-field YAML swap, a monitored Grafana restart (necessary for a newly supplied service environment variable), post-start contact API inspection and operator-confirmed synthetic Firing/Resolved Email+Telegram. Avoid blindly applying checked-in Email-only YAML; preserve receiver UIDs and existing policy tree. Request explicit operator approval for a live restart/reload and message sending. Grafana [file-provisioning documentation](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/) notes that startup/reload can create, update or delete alerting resources and that file-provisioned resources are managed by the file.

`SANDBOX_RUNTIME_GRAFANA_13_2_3=PASS`; `SYNTHETIC_EMAIL=PASS`; `SYNTHETIC_TELEGRAM=PASS`; `SYNTHETIC_CHAT_ID_EXPANSION=PASS`; `PRODUCTION_CHANGE=NOT_STARTED`; `POST_MIGRATION_DELIVERY=NOT_TESTED`.

## Production deployment preflight — operator-reported / 2026-10-13

The operator ran the final read-only readiness checks and reported **all ten PASS**:

| Check | Result |
|---|---|
| `SYSTEMD_QUERY` / `GRAFANA_RUNNING` | `PASS` / `PASS` |
| `NO_DIRECT_ENV_COLLISION` | `PASS` |
| `ENVIRONMENT_SOURCES_PRESENT` / `ENVIRONMENT_SOURCES_READABLE` | `PASS` / `PASS` |
| `NO_ENVFILE_NAME_COLLISION` | `PASS` |
| `LIVE_CONTACT_UNIQUE` | `PASS` |
| `BACKUP_STILL_MATCHES_LIVE` | `PASS` |
| `CANDIDATE_REFERENCE_VALID` | `PASS` |
| `PERMANENT_ALERT_RULES_15` | `PASS` |
| **`DEPLOYMENT_PREFLIGHT`** | **`PASS`** |

`CONFIG_MODIFIED=NO`, `GRAFANA_RESTARTED=NO`, `NOTIFICATIONS_SENT=NO`, `SECRET_VALUES_PRINTED=NO`.

**Approved finding:** pre-change inventory is consistent. **Not yet authorized:** modifications to `EnvironmentFile` wiring, live YAML or a Grafana restart. The earlier two-restart conceptual approach was revised to a *single controlled restart* that applies the environment and one-field YAML change together, after final review and authorization. This reduces interruption but requires a complete private rollback plan, systemd drop-in inventory and SELinux safeguards.

A separate **review-only** guide has been committed: [`docs/grafana-236-telegram-chatid-deployment-runbook.md`](../../docs/grafana-236-telegram-chatid-deployment-runbook.md). It specifies source-of-truth limitations, host-only secure storage, one restart (after approval), post-boot contact/rule/policy validation and single-restart rollback; **no production change was applied from this GitHub commit**.

`DEPLOYMENT_PREFLIGHT=10/10_PASS`; `DEPLOYMENT_RUNBOOK=PREPARED`; `LIVE_RESTART_AUTHORIZATION=PENDING`; `PRODUCTION_MIGRATION=NOT_STARTED`.

## SELinux and systemd deployment-path audit — operator report / 2026-10-13

The operator checked loaded unit state and migration target paths in read-only mode:

| Check | Observation |
|---|---|
| `SYSTEMD_QUERY` | `PASS` |
| `UNIT_LOADED` / `SERVICE_ACTIVE` / `UNIT_FILE_PRESENT` | all `True` |
| `EXISTING_DROPINS` | `5` |
| `EXISTING_ENVIRONMENT_FILES` | **`1`** |
| `TARGET_DROPIN_EXISTS` / `TARGET_SECRET_EXISTS` | both `False` |
| `DROPIN_PARENT_EXISTS` / `SECRET_PARENT_EXISTS` | `True` / `False` |
| `DROPIN_NAME_COLLISIONS` | `0` |
| `SELINUX_MODE` / `RESTORECON_AVAILABLE` | `Enforcing` / `True` |
| **`DEPLOYMENT_PATH_PREFLIGHT`** | **`REVIEW_REQUIRED`** |
| Files created, systemd modified, Grafana restarted, notifications sent | all `NO` |

**Blocking discrepancy:** An earlier `systemctl show ... EnvironmentFiles` audit reported **four** sources and their modes, whereas this check reports **one** source from another query of the same unit. This is **not reconciled**; do not assume that all four remain effective, that three were removed or that it is merely a parsing quirk. The presence of five systemd drop-ins also requires checking ordering, additive vs reset `EnvironmentFile=` assignments and effective source references. Do not log raw systemd environment properties, file contents or secret-bearing paths.

**Additional deployment caveat:** SELinux `Enforcing` is active, and the prospective private directory does not exist. Before deploying any new env file, determine systemd's effective access and expected SELinux context and validate a private path. The currently missing target directory is not a failure: no production writes are authorized.

**Action:** suspend production migration, collect a **sanitized read-only comparison** of the effective `EnvironmentFiles` list from `systemctl show` and the unit/drop-in `EnvironmentFile` directives from `systemctl cat` (counts, resets and per-file booleans; never raw lines or paths). Check whether variables referenced by the live YAML occur in the newly reported effective sources and verify whether the Grafana service has been reloaded/changed externally. Reassess staging integrity before deployment. No restart, reload or notification until discrepancy is resolved.

`PATH_PREFLIGHT=REVIEW_REQUIRED`; `SYSTEMD_ENVFILE_COUNT_DISCREPANCY=4_VS_1_OPEN`; `SELINUX=ENFORCING`; `PRODUCTION_UNTOUCHED=YES`.

## Reconciliation follow-up — 2026-10-13: likely audit parser artifact, still unclosed

A new **read-only** operator diagnostic returned:

- `SINGLE_QUERY_SOURCES=4`; `SOURCE_PARSE_COMPLETE=True`.
- `MULTI_QUERY_SOURCES=1`; `SOURCE_LISTS_EQUAL=False`. The script assembled multi-property output into a Python dictionary using `properties[key] = value`; if `systemctl show` emits multiple `EnvironmentFiles=` lines, earlier records are overwritten. Therefore the reported count `1` does **not** establish that only one file is effective.
- `ENVFILE_DIRECTIVES=4`; `ENVFILE_NONEMPTY_DIRECTIVES=4`; `ENVFILE_RESET_DIRECTIVES=0`, from `systemctl cat`.
- `SERVICE_ACTIVE=True`; `NEED_DAEMON_RELOAD=no`; `LOADED_DROPINS=5`; `CONTACT_UNIQUE=True`; `EMAIL_REFERENCE_VALID=True`; `TELEGRAM_REFERENCE_VALID=True`.
- The reference-source loop then crashed with `ValueError: too many values to unpack (expected 2)`. This is a **script unpacking defect**: `re.findall` has only one capturing group and returns individual path strings, not `(path, ignore_errors)` tuples. No effective-source ownership/readability comparisons from this interrupted run are valid.

**Preliminary interpretation:** the new evidence makes a **parsing bug** considerably more likely than genuine Grafana service configuration loss, but does not conclusively reconcile the multi-query serialization nor prove both referenced variables are presently supplied to the running service. The production deployment gate remains **on hold**. Next read-only script should collect **all** `EnvironmentFiles=` lines in multi-property output, compare their ordered path list against the one-property query, and iterate `for filename in sources` without unpacking. Do not reveal paths, environment assignments, contact values, tokens or IDs.

`SYSTEMD_ENVFILE_COUNT_DISCREPANCY=LIKELY_SCRIPT_ARTIFACT_PENDING_CONFIRMATION`; `SYSTEMD_DIRECTIVES=4_NONEMPTY_0_RESET`; `SOURCE_RESOLUTION_AUDIT=INCOMPLETE_SCRIPT_ERROR`; `PRODUCTION_UNTOUCHED=YES`.

## Resolved systemd EnvironmentFiles parsing discrepancy — operator-reported / 2026-10-13

A corrected read-only **V2** reconciliation resolved the earlier `4 vs 1` inconsistency as a **parser defect** rather than a demonstrated systemd change:

| Check | Operator result |
|---|---|
| `SINGLE_SOURCES` / `MULTI_PROPERTY_LINES` / `MULTI_SOURCES_TOTAL` | `4` / `4` / `4` |
| `SOURCE_ORDER_MATCH` | `True` |
| `ENVFILE_DIRECTIVES` / `ENVFILE_RESETS` | `4` / `0` |
| All four source files readable/root-owned | `PASS` / `True` |
| Ordered modes | `0644`, `0600`, `0600`, `0640` |
| Contact name unique | `True` |
| Email env source found/private | `True` / `True` |
| Telegram token env source found/private | `True` / `True` |
| **`ENV_RECONCILIATION`** | **`PASS`** |
| Values printed / files changed / systemd reloaded / Grafana restarted / notifications | all `NO` |

In the previous flawed script, constructing a dictionary from repeated multi-property `EnvironmentFiles=` lines discarded all but the last property occurrence. Another prior script tried to unpack a one-group regex return (path string) as two values and crashed. Neither represents a genuine loss of three sources. **The environment-file count discrepancy is now CLOSED.**

**Remaining gates:** SELinux `Enforcing` means a reviewed private file location, safe context and unit drop-in wiring must be checked before deployment; operator-approved production restart/reload and separate post-change notification tests remain **NOT EXECUTED**. Re-run live backup-to-file byte comparison immediately before implementation.

`SYSTEMD_ENV_RECONCILIATION=PASS`; `ENVFILE_COUNT_DISCREPANCY=RESOLVED_PARSER_BUG`; `ENVFILE_COUNT=4`; `REFERENCED_EMAIL_PRIVATE=PASS`; `REFERENCED_TELEGRAM_TOKEN_PRIVATE=PASS`; `SELINUX_TARGET_VALIDATION=PENDING`; `PRODUCTION_UNTOUCHED=YES`.

## SELinux context policy/readback preflight — operator-reported / 2026-10-13

A read-only Fedora SELinux query was run with **SELinux Enforcing** active:

| Proposed path or existing source | SELinux **type** / result |
|---|---|
| New `/etc/grafana/private` directory (currently absent) | `etc_t` (predicted by `matchpathcon`) |
| New `/etc/grafana/private/telegram-chatid.env` (currently absent) | `etc_t` (predicted) |
| New `/etc/systemd/system/grafana-server.service.d/90-grafana236-telegram-chatid.conf` (currently absent) | `systemd_unit_file_t` (predicted) |
| Existing EnvironmentFile sources #1–#4 (actual labels) | `etc_t`, `etc_t`, `etc_t`, `etc_t` |
| `ENV_FILES` | `4` |
| `TARGET_POLICY_LOOKUP` | **`PASS`** |
| `EXISTING_LABELS_READ` | **`PASS`** |
| `FILES_CREATED`, `LABELS_CHANGED`, `SYSTEMD_MODIFIED`, `GRAFANA_RESTARTED` | all **`NO`** |
| `SECRETS_PRINTED` | `NO` |

**Finding:** The predicted future `etc_t` context matches the type of all four readable current environment sources, and the prospective unit drop-in has the expected `systemd_unit_file_t` type. There are no file collisions for the prospective names. **This does not prove SELinux permissions for a newly created file, its eventual actual label, or Grafana start and notification delivery after deployment.** Those remain a controlled implementation gate requiring `restorecon`, verifying actual types and full service health/receiver checks. Do not create target paths or restart/reload Grafana without operator-approved change window and tested rollback.

`SELINUX_PREDEPLOY_POLICY=PASS`; `SELINUX_MODE=ENFORCING`; `TARGET_PRIVATE_FILE_POLICY_TYPE=etc_t`; `TARGET_SYSTEMD_DROPIN_TYPE=systemd_unit_file_t`; `SELINUX_POST_INSTALL_LABELS=NOT_TESTED`; `PRODUCTION_UNTOUCHED=YES`.

## Next acceptance gates — safe sequence

1. Extend the **partial 2026-10-13 read-only Fedora SQLite inventory** (UID/group/pause/direct receiver already PASS) with loaded title, folder, thresholds, `for`, `noDataState` and runtime health/state; cross-check routing through the Grafana API where safe. Do not dump rule annotations, headers, secrets, local paths, addresses, or contact destination IDs.
2. The 2026-10-13 read-only DB confirms expected direct rule receiver, both Email/Telegram integration types, and default receiver; **remaining**: inspect notification-policy child routes/grouping and contact point/default-policy provisioning ownership without displaying contact destinations or secrets.
3. Direct rule notification settings were inspected: all 15 lack explicit grouping/timing overrides. Confirm effective Grafana fallbacks and runtime behaviour **separately** from root-policy routing; then mark each notification path `NOT_TESTED`, `PARTIAL`, `PASS`, or `WAIVED` with timestamp and operator-confirmed delivery channel in a per-rule evidence ledger.
4. Design isolated/bounded negative fixtures for **stale telemetry**, **DNS Guard critical recovery route**, **grouping/repeat/anti-flap**, and receiver failure. **Explicit operator approval required** before live notification tests.
5. Read-only checks and in-memory **single-field Telegram Chat ID migration dry run are PASS**, but a world-readable local YAML still has Chat ID inline, while Email and Telegram token settings use environment references. Inspect environment-source ownership/modes and the Grafana service read boundary **without logging values**, then stage a reviewed dedicated chat-ID environment reference and reconcile the **local Fedora Email+Telegram** configuration vs checked-in Email-only YAML. Separately document how the UI-edited default notification policy will be restored in disaster recovery, and plan a staged/reviewed provisioning persistence test. **No blind reload/restart**, no overwriting credentials or policy edits.
6. After explicit approval and non-destructive testing, verify individual warning/critical paths and `Firing`/`Resolved` delivery, regression to exactly 15 permanent rules, and document gaps/waivers.

## Acceptance / non-claims

- `SOURCE_RULE_COUNT=15`; `SOURCE_PAUSED=0`; `SOURCE_DIRECT_RECEIVER_RESOLVED=15`.
- `FRESH_LIVE_2026_10_13=PARTIAL_UID_GROUP_PAUSE_RECEIVER_PASS`; `LIVE_NOTIFICATION_SETTINGS_JSON_TYPE=list`; `LIVE_RECEIVER_MATCH=15/15_PASS`; `PER_RULE_E2E_DELIVERY=UNVERIFIED`.
- `LIVE_EMAIL_INTEGRATIONS=1`; `LIVE_TELEGRAM_INTEGRATIONS=1`; `LIVE_DEFAULT_RECEIVER_MATCH=PASS` (operator-reported read-only DB).
- `REPO_CONTACT_SOURCE=EMAIL_ONLY`; `FEDORA_LOCAL_FILE_CONTACT_TYPES=EMAIL_PLUS_TELEGRAM_TEXT_MARKERS` (structural scan, not yet parsed); `LIVE_CONTACT_DB=EMAIL_PLUS_TELEGRAM`; `LOCAL_YAML_AUTHENTICITY_AND_LOADED_PROVENANCE=UNVERIFIED`.
- `FEDORA_LOCAL_YAML_PARSE=3/3_PASS`; `EXPECTED_CONTACT_DEFINITIONS=1`; `LOCAL_CONTACT_EMAIL=1`; `LOCAL_CONTACT_TELEGRAM=1`; `TELEGRAM_BOTTOKEN_MODE=ENV_REFERENCE`; `CONTACT_YAML_GROUP_READABLE=TRUE`; `CONTACT_YAML_OTHER_READABLE=TRUE`; `OTHER_SECRET_FIELDS_AUDIT=PENDING`.
- `ROOT_POLICY_FILE_DECLARATION=NOT_OBSERVED`; `CLEAN_ROOM_RESTORE_POLICY_REPRODUCIBILITY=NOT_TESTED`.
- `DEFAULT_POLICY_GROUPING_CONFIG=PASS` (30s / 5m / 4h, grouped by alertname+grafana_folder); `DIRECT_RULE_NO_EXPLICIT_OVERRIDE=15/15_PASS`; `DIRECT_RULE_EFFECTIVE_GROUPING=NOT_LIVE_VALIDATED`; `ANTI_FLAP_DELIVERY=NOT_TESTED`.
- `EMAIL_ADDRESSES=ENV_REFERENCE`; `TELEGRAM_BOTTOKEN=ENV_REFERENCE`; `TELEGRAM_CHATID=INLINE_VALUE`; `CONTACT_YAML_OTHER_READABLE=TRUE`; `CHATID_PRIVACY_REMEDIATION=PENDING`.
- `SYSTEMD_ENVFILE_COUNT=4`; `ENVFILE_ROOT_OWNED=4/4`; `ENVFILE_0644=1`; `ENVFILE_0600=2`; `ENVFILE_0640=1`; `EMAIL_LAST_ENV_SOURCE=ENV2_PRIVATE`; `TELEGRAM_BOTTOKEN_LAST_ENV_SOURCE=ENV3_PRIVATE`; `ENV4_GROUP=GRAFANA`; `WORLD_READABLE_ENV_CONTENTS=NOT_AUDITED`.
- `EXISTING_TELEGRAM_CHATID_ENV_NAME_CANDIDATES=0_OF_4_FILES`; `GRAFANA_TELEGRAM_CHAT_ID=PROPOSED_NOT_DEPLOYED`.
- `TELEGRAM_CHATID_YAML_IN_MEMORY_DRY_RUN=PASS`; `DRAFT_YAML_VALID=TRUE`; `ONLY_CHATID_CHANGED=TRUE`; `LIVE_INTERPOLATION=NOT_TESTED`.
- `HOST_SECURE_STAGING_V2=PASS`; `STAGING_ROOT_MODE=0700`; `STAGING_FILE_MODES=0600`; `STAGED_CHATID_NONNEGATIVE=TRUE`; `STAGED_ENV_SOURCE=NOT_ACTIVE`; `STAGING_INTEGRITY=12_CHECKS_PASS`; `BACKUP_MATCHES_LIVE=PASS`; `LIVE_GRAFANA_INTERPOLATION=NOT_TESTED`.
- `ISOLATED_TEST_PREFLIGHT=PASS`; `GRAFANA_INSTALLED=13.2.3`; `PODMAN_AVAILABLE=TRUE`; `DOCKER_AVAILABLE=TRUE`; `CONTAINER_IMAGE_CACHE_STATUS=UNKNOWN`; `ISOLATED_RUNTIME_PROVISIONING=NOT_TESTED`.
- `PODMAN_GRAFANA_IMAGE_CACHE=0`; `PODMAN_VERSION_MATCH_IMAGES=0`; `DOCKER_IMAGE_QUERY=FAILED`; `ISOLATED_HOST_BINARY_TEST=NOT_STARTED`.
- `SYSTEMD_DYNAMICUSER_PRIVATE_NETWORK_SANDBOX=6_6_PASS`; `SANDBOX_GRAFANA_RUNTIME=NOT_STARTED`.
- `SYNTHETIC_GRAFANA_13_2_3_PROVISIONING=PASS`; `SYNTHETIC_API_CONTACT_READ=PASS`; `SYNTHETIC_EMAIL_AND_TELEGRAM=PASS`; `SYNTHETIC_CHATID_INTERPOLATION=PASS`; `PRODUCTION_MIGRATION=NOT_STARTED`.
- `DEPLOYMENT_PREFLIGHT=10_10_PASS`; `ONE_RESTART_RUNBOOK=PREPARED_NOT_EXECUTED`; `SYSTEMD_DROPIN_AND_SELINUX_PREFLIGHT=PENDING`.
- `DEPLOYMENT_PATH_PREFLIGHT=REVIEW_REQUIRED` (historical result invalidated by parser defect); `ENVFILES_RECONCILIATION_V2=PASS`; `ENVFILES_CURRENT=4`; `MULTI_PROPERTY_LINES=4`; `DISCREPANCY=RESOLVED_SCRIPT_BUG`; `SELINUX=ENFORCING`; `NO_PRODUCTION_WRITES=TRUE`.
- `SELINUX_POLICY_LOOKUP=PASS`; `EXISTING_ENVFILE_TYPES=4_X_etc_t`; `TARGET_ENVFILE_EXPECTED=etc_t`; `TARGET_DROPIN_EXPECTED=systemd_unit_file_t`; `POST_INSTALL_REAL_LABELS=NOT_TESTED`.
- `PROVISIONING_RELOAD_PERSISTENCE=NOT_TESTED`.
- `ALL_15_PER_RULE_E2E=NOT_TESTED`.
- No live failure-injection, notifier send, service restart, config reload, or router mutation performed to create this document.
