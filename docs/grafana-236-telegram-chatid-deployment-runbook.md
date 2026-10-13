# Grafana #236 — Telegram Chat ID provisioning migration (deployment & rollback plan)

**Status:** OPERATOR AUTHORIZED migration with one planned Grafana restart; **NOT YET EXECUTED**  
**Prepared:** 2026-10-13  
**Tracking:** [Issue #236](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/236), [draft PR #237](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/237)  
**Target:** Fedora Grafana 13.2.3, `grafana-server.service`; production ASUS TUF router is **out of scope**.

## Verified evidence (operator-reported, read-only except private staging)

- **15/15** permanent Grafana rules loaded and not paused; **15/15** use the expected direct receiver `ASUS Edge Gateway Email`.
- Current live contact: one Email and one Telegram receiver in the **same** contact point. Grafana database has a matching default route and default grouping snapshot; actual anti-flap and per-rule delivery remain untested.
- Local Fedora YAML parses, has one Email + Telegram contact point, with Telegram bot token and Email addresses already using environment references. **Telegram Chat ID is still inline** in a local world-readable file.
- Four pre-existing Grafana `EnvironmentFile` sources: root-owned; modes `0644`, `0600`, `0600`, `0640`. Email reference last defined in file #2 and Telegram bot token in #3, both `0600`. File #4 group is `grafana`. No currently checked source has a matching `GRAFANA_TELEGRAM_CHAT_ID` name.
- Host-only staging: `/root/grafana-236-staging` is root-owned `0700`; `contact-original.yml`, `contact-candidate.yml`, `telegram-chatid.env` are root-owned `0600`. Copy of the original matched live YAML **byte-for-byte**. Candidate structurally differs only at Telegram `settings.chatid`, now `$GRAFANA_TELEGRAM_CHAT_ID`. Staged environment assignment has the same positive numeric Chat ID as original. `STAGING_INTEGRITY=PASS`.
- An isolated, short-lived **Grafana 13.2.3** ran with `PrivateNetwork=yes`, `DynamicUser=yes`, no visibility into production config/DB/staging, synthetic credentials/Chat ID, SMTP disabled, no alert rules or notifications. Its Contact Points API verified Email + Telegram and numeric Chat ID environment interpolation: `SYNTHETIC_PROVISIONING=PASS`.
- Latest operator report: `DEPLOYMENT_PREFLIGHT=PASS` (10/10 checks), active service, no env name collisions, original backup still matches live YAML, candidate references new variable, 15 live rules, no production changes.

## Desired state and scope

The single existing Contact Point keeps its **name, org ID, receiver UIDs, existing Email and Telegram fields**, and route. The **only** desired live YAML difference is `settings.chatid: $GRAFANA_TELEGRAM_CHAT_ID`. The actual Telegram chat ID is supplied through a **root-only systemd EnvironmentFile** and stays outside Git and all logs. Neither Email configuration, Telegram token, rule definitions, alert policies nor the running ASUS router are modified as part of this migration.

The checked-in `monitoring/grafana/provisioning/alerting/asus-email-contact.yml` is currently **Email-only** and is not an authoritative live-replacement source. **Never deploy it directly over the Fedora local Email+Telegram file.** The public-repository follow-up should use a separately reviewed sanitized representation, not a verbatim copy of any host file.

## Resolved audit anomaly (2026-10-13): systemd EnvironmentFiles

An initial operator-read path preflight reported only one EnvironmentFile, conflicting with four previously observed sources. The follow-up identified two **assistant-authored diagnostic script defects**: repeated `EnvironmentFiles=` properties were overwritten when parsed into a dictionary, and a one-group regex return was incorrectly unpacked as two values. The corrected **V2** read-only test definitively reported:

- `SINGLE_SOURCES=4`; `MULTI_PROPERTY_LINES=4`; `MULTI_SOURCES_TOTAL=4`; `SOURCE_ORDER_MATCH=True`.
- `ENVFILE_DIRECTIVES=4`; `ENVFILE_RESETS=0`.
- All four files read successfully, root-owned, modes `0644/0600/0600/0640`.
- Both Email destination and Telegram bot-token references resolved to world-inaccessible files.
- **`ENV_RECONCILIATION=PASS`**; no changes, daemon reload, Grafana restart, or sent messages.

**Disposition:** The `4 vs 1` blocker is **CLOSED — script parsing false positive**. The earlier `DEPLOYMENT_PATH_PREFLIGHT=REVIEW_REQUIRED` is a historical invalidated source-count snapshot.

**Current hold remains:** the server runs SELinux in `Enforcing`, the proposed private environment directory does not yet exist, and live changes/restart/testing have not been authorized. Next perform a **read-only file-context policy lookup** (`matchpathcon -n -m dir|file`) and inspect current private EnvironmentFile context *types* without logging file paths/values; the policy's default label prediction by itself does **not** demonstrate actual service read access. Review systemd unit ordering, maintain all four existing EnvironmentFile entries, and plan label restoration and rollback before a single operator-approved Grafana restart. A synthetic isolated Grafana test already passed; it does not replace production post-change acceptance.

### SELinux lookup result — policy preflight PASS

The operator verified that proposed private directory and environment file paths have predicted type `etc_t`, matching the **actual** SELinux type of each of the four existing `EnvironmentFile` sources. The proposed systemd unit drop-in has predicted type `systemd_unit_file_t`. `TARGET_POLICY_LOOKUP=PASS`, `EXISTING_LABELS_READ=PASS`, with SELinux `Enforcing`; no paths created, contexts changed, service restarts or messages sent.

This clears the **predicted-label policy lookup**, not actual post-install labels or service access. A reviewed deployment should create only the chosen root-owned private environment path, apply `restorecon` to newly created objects and check actual labels and ownership/mode *before* the single approved restart; revert immediately on any mismatch. Do not assume a future label is correct merely because `matchpathcon` predicted it.

### Operator approval and controlled two-phase implementation — 2026-10-13

The operator explicitly approved production deployment **including one Grafana service restart**. This is authorization, **not** evidence of deployment success. Earlier preflights confirmed 4 effective EnvironmentFile sources, zero reset directives, SELinux label-policy lookups PASS, same-type `etc_t` for all four current env files, `systemd_unit_file_t` expected for a new drop-in, and 15 permanent rules.

**Execution is split into safety gates:**

- **Phase 1 (first):** create only an additive protected `/etc/grafana/private/telegram-chatid.env` (root 0600), private dir (0700) and uniquely named systemd drop-in (root 0644) referencing that env file; `restorecon` and verify labels; preserve live YAML, do **not** run `daemon-reload` or restart. If any check fails, clean up only newly created files and STOP. Existing Grafana process is unaffected.
- **Phase 2 (after operator reports Phase 1 PASS):** revalidate the backup, candidate, all four original sources, new labels and projected five-file additive ordering, atomically replace the **single existing live contact YAML**, `daemon-reload`, verify systemd effective five env sources, execute the **one approved restart**, and check service/rules/contact and matching Chat ID without printing values. On start failure, restore original YAML/remove only newly added files and drop-in, `daemon-reload`, restart for rollback (extra restart only when failure recovery requires it). Never replace using the Email-only repository source.
- Sending Firing/Resolved test notifications **not covered by the restart approval**; request a separate authorization for the notifier exercise.

No live service change has yet been reported.

## Stage 0 — immediately before implementation (read-only; STOP on failure)

1. Confirm Grafana v13.2.3, active `grafana-server.service`, count **exactly 15** rules, no failures, correct receiver counts and current delivery status. Do not dump contact-point settings or credentials.
2. Verify unique matching contact YAML, exact equality with `contact-original.yml`, private stage file modes/ownership and Chat ID match; re-run the approved `STAGING_INTEGRITY` and `DEPLOYMENT_PREFLIGHT` scripts **just before deployment**.
3. Inspect **effective systemd drop-in names** and `EnvironmentFile` ordering **without printing Environment values**; check candidate drop-in basename for collisions and confirm configured `EnvironmentFile` paths can coexist without resetting original sources.
4. Choose a stable protected path such as `/etc/grafana/private/telegram-chatid.env` (0600 root/root) and a unique named systemd drop-in under `/etc/systemd/system/grafana-server.service.d/`. Ensure backup/rollback of all existing contents and correct SELinux labeling on Fedora. If names already exist, STOP for operator review.
5. Confirm a controlled maintenance window and **explicit operator approval** for a short production Grafana restart and for any separate test notification. Identify how operator will reach Grafana if it fails.
6. Prepare and validate an **offline** rollback: revert the exact active contact YAML from the private original byte copy; remove only this migration's drop-in/env source; run `daemon-reload` and **one controlled restart**; re-verify 15 rules and expected contact/policy. Do not overwrite unrelated overrides or remove preexisting files.

### Operator confirmation — production Phase 1 PASS (2026-10-13)

The operator ran the previously reviewed Stage 1 script (`grafana236_stage1.py`) and reported:

```text
PREINSTALL_VALIDATION=PASS
ROOT_ONLY_ENV_FILE=PASS
DROPIN_CREATED=PASS
SELINUX_NEW_OBJECTS=PASS
ORIGINAL_LIVE_YAML_UNCHANGED=PASS
SYSTEMD_DAEMON_RELOAD=NO
GRAFANA_RESTARTED=NO
NOTIFICATIONS_SENT=NO
VALUES_PRINTED=NO
PRODUCTION_STAGE1=PASS
```

**Interpretation:** The protected Chat ID environment source and additive unit drop-in are **installed on Fedora** and new-file SELinux labels were verified. Active contact YAML remains the original. No `daemon-reload` or restart has occurred, so the loaded Grafana process has **not** received the new env assignment. Phase 2 must recheck file modes, labels, binary freshness and the byte-identical original against live, then perform **one** approved restart, after validating five effective EnvironmentFile references. If preflight fails, leave the original running and do not touch its YAML. Real alert Firing/Resolved notifications remain separately gated.

### Phase 2 script prepared — awaiting Fedora execution

The prepared downloadable helper `grafana236_stage2.py` (SHA-256 `c7aff81a2aab215deec702328580dfe327f3e74f85356a1c42e42fcba674571d`) is a **host-local deployment command** supplied to the operator; this note is **not evidence of execution**. The helper is guarded by stage1 private-file, labels, original-live byte identity, existing four source ordering, no name collision, SQLite 15-rule/direct receiver and Alertmanager contact/policy baseline checks.

It creates a **root-only sensitive** `/root/grafana-236-staging/grafana-pre-stage2.db` SQLite hot backup before touching active files. It then performs systemd `daemon-reload` and requires **five additive** EnvironmentFile entries (four original plus the migration file) *before* atomically replacing the active contact YAML, preserving original owner/mode/SELinux context. It requests **one** authorized Grafana restart. Postchecks include active service, 15 permanent rules, unchanged policy and contact receiver UIDs/types, new variable present in the Grafana MainPID process environment, and an opportunistic Grafana HTTP health check only if the baseline on localhost port 3000 was verifiable.

If any post-change gate fails, it attempts to restore the original YAML and remove only the migration drop-in/env file; after restart attempt it may require **one additional rollback restart**. If no restart was attempted, no rollback restart should be issued. `ROLLBACK=FAILED_NEEDS_OPERATOR` is an emergency condition requiring manual review; do not run automated repair repeatedly. The script **does not send test notifications**. Natural alert notifications might nevertheless occur across a service restart; operator confirmation is still needed for real delivery.

**Caution:** no systemd or container tool in this chat can execute on the user's Fedora host; only the operator can execute and inspect its output. Do not claim Stage 2 PASS until the operator has run it. The private SQLite backup contains sensitive application configuration and must remain outside Git and any shared logs. The script's approval covers the one planned restart and necessary failure recovery, not a standalone synthetic Firing/Resolved delivery test.

## Stage 1 — planned single production switch (PHASE 1 PASS; PHASE 2 PENDING)

1. Re-validate private original against live source; fail closed if changed since backup.
2. From the root-only private stage, install the Telegram Chat ID assignment to the reviewed stable root-only file, preserving the exact non-empty decimal string. **Never print assignment lines, Chat ID, bot token or destination metadata.** systemd environment variables are configuration, not a secret store; restrict host/process access appropriately.
3. Create only the reviewed systemd service drop-in containing an **additive** `EnvironmentFile=/etc/grafana/private/telegram-chatid.env`. Verify that effective `EnvironmentFiles` still includes all four existing sources and this new one, in suitable order. Do not reset the `EnvironmentFile` directive list or the `ExecStart` command.
4. Install the verified single-field candidate YAML at the **same production contact-point file path**, preserving required ownership/mode/SELinux context. Do not add a second contact file or change receiver UIDs. Confirm no extra `policies` file is introduced.
5. `systemctl daemon-reload`, then **one controlled restart of grafana-server** after explicit approval and backup checks. Adding `EnvironmentFile` alone does not update the environment of a previously started process; an alerting-provisioning hot reload without process restart cannot be assumed to pick it up.
6. Immediately inspect `ActiveState`, process liveness and `/api/health`; verify 15 non-paused rules, matching receiver UID/type/count, expected policy tree/grouping and that the **Telegram Chat ID is present and unchanged** via a boolean comparison performed locally without printing either value. Never expose contact API raw JSON in logs.
7. Require an operator-confirmed, scoped synthetic test of **Email + Telegram Firing and Resolved** notifications only with its own authorization. Restore normal state/remove any temporary rule. Do not claim all 15 rule-specific E2E paths from one shared synthetic alert.

## Fail-safe stop and rollback triggers

**STOP and return to the documented baseline** if the active contact YAML no longer matches backup, any required file is missing/insecure, `EnvironmentFile` ordering is unknown, Grafana start fails, the contact loses an integration or changes a receiver UID, the routing policy differs, rules no longer total 15, or either channel's delivery is unexpectedly broken.

**Rollback plan:** using the private copies, restore only this migration's contact YAML from `contact-original.yml`; remove or disable only the new migration-specific systemd drop-in (do not delete any preexisting overrides) and optionally the new environment file after it is no longer referenced; reload systemd unit metadata and restart Grafana **once**, then verify health, original Contact Point Email+Telegram, 15 rules, default policy and both channels. Preserve separate copies of pre-/post-change evidence (without secrets) and note any interruption. If rollback cannot restore the service, stop rather than trying blind unrelated configuration rewrites.

## Evidence and acceptance gate

Log timestamps and sanitized PASS/FAIL booleans: YAML + EnvironmentFile verified; restart once; service ready; rule count 15; receiver UID/name/type parity; Chat ID numeric and equivalent **without disclosure**; policy/grouping unchanged; scoped Firing and Resolved confirmed through both channels; no additional persistent alerts; no unexpected log errors.

**Do not mark Issue #236 closed solely from this migration:** direct-per-rule routing, grouping/repeat/anti-flap behavior and full clean-room policy/contact restore remain independent acceptance gates.

References: [Grafana alerting file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/), [Grafana admin provisioning reload](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/admin/), [systemd unit drop-ins](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html), [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html).
