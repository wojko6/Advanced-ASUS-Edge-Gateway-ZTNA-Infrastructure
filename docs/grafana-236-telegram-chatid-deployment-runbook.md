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

### Production Phase 2 attempt — gate failed BEFORE live YAML/restart; rollback PASS

Operator output for a SHA-verified `grafana236_stage2.py` invocation:

- Pre-install and service gates: all `PASS`, including `RULES_CONTACT_POLICY_BASELINE`, `PRIVATE_SQLITE_SNAPSHOT`, `DEPLOYMENT_PREFLIGHT`, and `SYSTEMD_DAEMON_RELOAD`.
- The first post-reload gate failed: **`ENVIRONMENT_FILES_5_ADDITIVE=FAIL`**, raising `RuntimeError`; `PRODUCTION_STAGE2=FAIL`.
- Automatic rollback ran: `ROLLBACK_DAEMON_RELOAD=PASS`, `ROLLBACK_ENVFILES_RESTORED=PASS`, `ROLLBACK_ORIGINAL_YAML=PASS`, **`ROLLBACK=PASS`**.
- The gate failed **before** the candidate YAML installation and before `systemctl restart grafana-server`; neither was requested by the script. The script also reported no secrets printed. No controlled notification test was attempted.
- A **private Grafana SQLite snapshot now exists** in the root-only staging directory; the original Stage 2 helper requires the snapshot path to **not already exist**. **Do NOT rerun the same Stage 2 script** or delete that backup in order to bypass the check. Stage 1 objects were removed during the scripted rollback (pending host readback).

**Potential explanation, NOT a confirmed cause:** the Stage 2 helper's validation checks more than additive inclusion. It requires the fifth EnvironmentFile to appear **at the end**, i.e. `current_sources[:4] == baseline_sources` and `current_sources[4] == new_secret_path`. systemd drop-ins are applied in name ordering, and an existing later-named drop-in may legitimately contribute one or more EnvironmentFile entries **after** the new `90-...` drop-in. In that case all **five** entries can be present, all four existing entries preserved, yet this unnecessarily strict position check rejects the safe configuration. Alternatively, the newly installed drop-in may not have been loaded, may have been superseded or the count may actually differ. **Do not assume which** until a read-only diagnosis.

**Immediate next gate:** verify Grafana active/healthy and 15 rules, staged backup still matches live contact YAML, loaded EnvironmentFile list back to four, proposed private secret and drop-in now absent and private SQLite backup present/integrity valid; inspect only **relative drop-in name ordering** and the count of entries declared in later drop-ins. Never print paths, settings, tokens or raw unit contents. Do not modify running service or restore the old Stage 1 automatically. If the fifth source was present out of order, fix only the gate to check that the **original list is an ordered subsequence** and the new source occurs **exactly once** with no unexpected sixth source; do not weaken owner/SELinux/secret constraints. Change will require another reviewed script and a new backup path strategy with existing snapshot protected.

`STAGE2_ATTEMPT=FAILED_PRE_YAML_PRE_RESTART`; `FAILING_GATE=ENVIRONMENT_FILES_5_ADDITIVE`; `ROLLBACK=PASS`; `PRODUCTION_SWITCH=NOT_COMPLETED`; `BACKUP_DB=CREATED_PRIVATE`; `NEXT_ACTION=READ_ONLY_DIAGNOSIS`.

## Stage 1 — planned single production switch (PHASE 1 PASS; PHASE 2 PENDING)

1. Re-validate private original against live source; fail closed if changed since backup.
2. From the root-only private stage, install the Telegram Chat ID assignment to the reviewed stable root-only file, preserving the exact non-empty decimal string. **Never print assignment lines, Chat ID, bot token or destination metadata.** systemd environment variables are configuration, not a secret store; restrict host/process access appropriately.
3. Create only the reviewed systemd service drop-in containing an **additive** `EnvironmentFile=/etc/grafana/private/telegram-chatid.env`. Verify that effective `EnvironmentFiles` still includes all four existing sources and this new one, in suitable order. Do not reset the `EnvironmentFile` directive list or the `ExecStart` command.
4. Install the verified single-field candidate YAML at the **same production contact-point file path**, preserving required ownership/mode/SELinux context. Do not add a second contact file or change receiver UIDs. Confirm no extra `policies` file is introduced.
5. `systemctl daemon-reload`, then **one controlled restart of grafana-server** after explicit approval and backup checks. Adding `EnvironmentFile` alone does not update the environment of a previously started process; an alerting-provisioning hot reload without process restart cannot be assumed to pick it up.
6. Immediately inspect `ActiveState`, process liveness and `/api/health`; verify 15 non-paused rules, matching receiver UID/type/count, expected policy tree/grouping and that the **Telegram Chat ID is present and unchanged** via a boolean comparison performed locally without printing either value. Never expose contact API raw JSON in logs.
7. Require an operator-confirmed, scoped synthetic test of **Email + Telegram Firing and Resolved** notifications only with its own authorization. Restore normal state/remove any temporary rule. Do not claim all 15 rule-specific E2E paths from one shared synthetic alert.

### Post-rollback evidence and planned corrected attempt (V3)

Independent operator readback after the failed phase-2 attempt returned **`POST_ROLLBACK_AUDIT=PASS`**: Grafana active, systemd metadata synchronized, four original EnvironmentFiles restored, migration drop-in/env file absent, contact YAML byte-identical to the private original, 15 non-paused rules, and the retained private SQLite backup root `0600` plus `quick_check=ok`.

There are **five existing drop-ins**, and **two sort after** the proposed migration `90-grafana236-telegram-chatid.conf`. The old Stage 2 script demanded that the newly inserted fifth `EnvironmentFile` always occupy the last position. That positional requirement is invalid for sorted systemd drop-ins; it likely explains the failure, though the failed script did not print the then-current list.

The revised downloaded helper `grafana236_stage2_v3.py` has SHA-256 **`355fbc847e350fea6f3d463ca98c6dd6fc5a718a7e8fc540cad8893dc07d28f6`**, passed `py_compile`, and ran a pure-function fixture of five legal insertion positions and five invalid source sets. It verifies **exactly five effective EnvironmentFiles**, the new source appearing **once** and the original four surviving as an **ordered subsequence**; does not require fifth-place insertion. It additionally confirms the old backup `grafana-pre-stage2.db` remains `0600` and SQLite `quick_check=ok`, and creates a **new** non-overwriting `grafana-pre-stage2-v3.db` backup. If the new backup already exists, it fails closed.

**Retry sequence:** first re-run Stage 1 (previous rollback removed the two installed files) and inspect `PRODUCTION_STAGE1=PASS`. Only then run SHA-verified Stage 2 V3 under the existing operator-approved single restart. **Never** rerun original `grafana236_stage2.py`, overwrite/delete the existing backup, or bypass any failing preflight. Do not claim V3 PASS until the operator provides its result; separately authorize real Email/Telegram notification test messages.

### Operator confirmation — Phase 1 reinstallation PASS (V3 retry preparation)

After the previous Phase 2 aborted before YAML replacement and the independent `POST_ROLLBACK_AUDIT=PASS` readback, the operator **re-executed Stage 1** and reported:

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

This reinstalls the private host-only env source and additive drop-in; it does **not** activate the new variable in the running service. **Stage 2 V3 is now eligible for execution under the prior operator authorization, but has not yet been reported as run.** V3 must still pass all its own preflight checks, preserve the earlier SQLite snapshot, create a new independent backup and, if safe, do one planned Grafana restart. On any failed check, stop and inspect rollback status; do not rerun blindly.

### Phase 2 V3 attempt — blocked before any live change

The operator's V3 result has only `ROOT_REQUIRED=PASS`, `STAGING_PRIVATE=PASS`, `STAGE_FILES_PRIVATE=PASS` before `PRODUCTION_STAGE2=FAIL`, `FAILED_CLASS=FileNotFoundError`, `STARTING_ROLLBACK=NO` and `ROLLBACK=NOT_REQUIRED_NO_LIVE_YAML_CHANGE`. Inspection of the exact downloaded V3 source places this failure at the first checks of `/etc/grafana/private` or the previously created private env/drop-in file. No `daemon-reload`, candidate YAML replacement, Grafana restart or new V3 SQLite snapshot was reached.

**HOLD:** Do not re-run Stage 1 or V3 until a read-only path-state and service-state audit establishes which Stage 1 target is missing, whether service health/config are intact, and why the target is unavailable after the prior Stage 1 PASS. The script's rollback-not-required message does **not** prove the Stage 1 files still exist.

### V3 missing-directory forensic checkpoint — deployment still on hold

The operator reports that `/etc/grafana/private`, `telegram-chatid.env`, and the unique systemd drop-in are **all absent**, while Grafana is active, 4 original EnvironmentFiles are loaded, the live contact YAML equals the original, and 15 rules are present/unpaused. **Both** private SQLite backups are present.

Inspection of the downloaded Phase 2 V3 source (SHA-256 `355fbc847e350fea6f3d463ca98c6dd6fc5a718a7e8fc540cad8893dc07d28f6`) shows the failed invocation stopped at `SECRET_DIR.lstat()` immediately after `STAGE_FILES_PRIVATE=PASS`. The `ROLLBACK=NOT_REQUIRED_NO_LIVE_YAML_CHANGE` branch does **not** remove Stage 1 files, and this invocation never reached the V3 backup creation code. Therefore **the Stage 1 objects were already missing as observed by V3**, and the V3 backup existed independently of that failed invocation. Their provenance cannot be inferred from this output.

**HOLD ALL REDEPLOYMENTS.** Perform a read-only timeline/provenance audit (file metadata, private backup integrity, sanitized system journal invocation counts/timestamps) before touching these paths. Do not delete, rename, rerun, chmod, reload systemd or restart Grafana for diagnosis. Restore strategy will be revisited only after the discrepancy is understood.

### Updated chronology: two V3 invocations, not one (2026-10-13)

The operator's read-only metadata/journal summary found two V3 command records at `21:04:37` and `21:05:14` (CEST). The private `grafana-pre-stage2-v3.db` was created at **21:04:37**, exactly with the **first** invocation; Grafana's current `ActiveEnterTimestamp` is **21:04:42**. Stage 1 had been invoked at `21:03:42`. The **second V3 invocation** stopped at `SECRET_DIR.lstat()` because the three Stage 1 objects were absent; it did not create the backup or restart Grafana.

**Important correction:** Earlier broad claims that Grafana had not restarted during the V3 sequence were overconfident. The 21:04:42 activation strongly suggests the **first V3 invocation did restart Grafana**, but the exact first-run output is not yet available. The V3 rollback code explicitly removes the new env, drop-in, and private dir when a prior live change/reload triggers rollback, which plausibly accounts for their absence before the second attempt. Avoid attributing this to an external process without evidence. Post-rollback readback is currently healthy, 15 rules unpaused, YAML original and 4 EnvironmentFiles.

**STOP further attempts:** first retrieve the earliest V3 output if available and run a **read-only sanitized** service-lifecycle/contact/health check for the 21:04:30–21:05:15 interval. Determine which first-run acceptance gate failed and whether its rollback succeeded before planning any new script or deployment.

### Confirmed service chronology and post-rollback health

The operator's filtered `journalctl -u grafana-server.service` query confirms two **distinct restarts**: service stopped/started `21:04:38–21:04:40`, then stopped/started `21:04:40–21:04:42` on 2026-10-13 (CEST). With V3 first invocation `21:04:37` and two prior backups created as documented, this supports **first V3 production restart followed by its rollback restart**. Second V3 invocation `21:05:14` failed during initial missing-directory preflight and did not restart the service. The first V3's failing assertion remains **unproven** without the terminal output.

Current operator-reported status: Grafana 13.2.3 active, HTTP health/database OK, 15 non-paused alert rules, matching single Contact Point containing one Email and one Telegram integration, daemon reload clean. Independently, post-rollback source checks confirm original YAML, four environment files and removal of Stage 1 resources. This establishes infrastructure recovery but does **not** prove post-restart actual notification delivery.

**No further attempt is permitted before identifying the first V3 `FAILED_GATE`.** Prefer retrieving that first command's output (no secrets). If unavailable, a limited journal error-category audit can narrow hypotheses but cannot substitute for the exact failed assertion. Preserve both root-owned private SQLite backups.

### Journal keyword classifier not sufficient to diagnose Phase 2 V3 failure

The operator's read-only 21:04:35–21:04:45 Grafana journal scan contained **527 application entries** and `STARTUP_ERROR_MATCHES=53` based on the broad regex `error|failed|panic|fatal`; no entries had syslog severity 0–3. These are **text match counts, not actual errors**, and do not establish the Python script's first `FAILED_GATE`. Other keyword matches: provisioning 29, database 54, environment 24 and alerting 37.

V3 first-run `FAILED_GATE` remains unknown. **No new service restart or Stage 1 reinstall is permitted** until the earliest first-run terminal output is retrieved or a narrowly scoped read-only analysis establishes an actionable defect. Prefer the first output over speculative code changes.

### Existing process environment parity PASS; V3 startup readiness concern

Read-only audit of the **current restored** Grafana process returned `EMAIL_REFERENCE_FOUND=True`, `TELEGRAM_REFERENCE_FOUND=True`, `EMAIL_VARIABLE_IN_PROCESS=True`, `TELEGRAM_VARIABLE_IN_PROCESS=True`, `ACTIVE_SERVICE=True`, `DAEMON_RELOAD_NEEDED=no`; no secrets/names, writes or restarts. This proves baseline Email+Telegram token references reach the running process, **not** that a transient migrated Chat ID variable was present during the first V3 attempt.

Offline source inspection shows V3's `check_service_ready()` can return as soon as systemd reports `active` and the SQLite rule/contact/policy snapshot matches; **it does not wait for HTTP readiness**. The HTTP test, when enabled, is one request with a 2-second timeout after the service-ready and process-environment checks. The service restarted and was stopped again within the same second (21:04:40), so this is a **credible readiness race**, but the exact first-run `FAILED_GATE` is unknown. Do **not** assume `GRAFANA_HTTP_HEALTH` was the failing gate: `RUNNING_ENV_CONTAINS_CHATID` and other post-restart gates could fail too.

Until the first-run output is found (or a reviewed offline fix is devised and tested), **do not re-run production scripts or restart Grafana**. Next script design must explicitly poll both process environment and HTTP readiness with a bounded deadline before interpreting early startup as failure. Such a proposal needs separate review before use.

### V4 readiness design — source weakness fixed offline, no production deployment

Code review confirmed a V3 defect: its `check_service_ready()` considers systemd `active` plus a SQLite baseline snapshot sufficient; Grafana HTTP readiness is checked only once **after** that assertion, with a two-second timeout. A premature post-start rollback is therefore plausible (but the first V3's actual `FAILED_GATE` is still unknown).

A **standalone read-only** V4 stable-readiness probe is prepared for the operator (`grafana236_readiness_v4.py`; SHA-256 `3c14a10674d9d852299acf3a8fb149c00025e8c9c31ada8784d86f6c9435d93f`). It requires three consecutive fully passing samples from the same PID for systemd, existing Email/Telegram env names, 15 non-paused rules, matching DB contact and Grafana 13.2.3 HTTP health, without printing names/values. Its pure polling helper passed **11 offline isolated fixture tests** (`test_grafana236_readiness_v4.py`, SHA-256 `1fac8ec17e46b7a131905451aafe60c9fc342c0ea830df3987289a7c89a07e50`).

**Next action: read-only Fedora host validation of the probe.** No production V4 switch helper has yet been created or run, and no restart is part of this probe. Keep Stage 1/V3 off, preserve root-only SQLite backups and require another reviewed change decision before a restart.

### Fedora V4 baseline confirmed; Phase 2 V4 candidate prepared offline

The operator's **read-only** Fedora V4 probe passed three consecutive identical-PID samples on its first three attempts, including systemd active, Email+Telegram process env names, 15 unpaused rules, DB receiver parity and Grafana 13.2.3 HTTP healthy. `STABLE_READINESS=PASS` without any reload/restart/file change/notification.

A self-contained **Phase 2 V4 candidate (NOT DEPLOYED)** is prepared offline, SHA-256 `7fa3866015893c34d44edef46b04d2cb20e266f277288f9fed211f5f8b931697`. Its new `stable_poll()` replaces V3's immediate post-start HTTP gate with at least three consecutive samples of **stable fresh PID**, unchanged 15-rule/contact/policy baseline, healthy HTTP and runtime Email+Telegram+new Chat ID environment. It validates the same stable readiness for rollback (without requiring the migration-specific Chat ID variable). Two previous root-only SQLite backups are preserved and separately integrity-checked; a new `grafana-pre-stage2-v4.db` would be created, never overwritten. Adds a V4 execution lock. The pure/helper/static safety fixture passed **27/27 offline tests**; these do not prove a complete deployment.

**Do not execute yet:** Stage 1 files are absent after rollback, and the previous operator restart authorization has already been used. The V4 candidate requires a new explicit maintenance approval and renewed Stage 1 PASS before any production use. No Firing/Resolved test has been authorized.

### Fedora V4 offline tests PASS and parser interpretation corrected

The operator ran V4's synthetic offline suite on Fedora and got **`Ran 27 tests ... OK`**, with no Grafana service changes. An independent isolated test of the **unmodified** V4 `env_sources()` implementation confirmed that its systemd regex has **one** capture group: `(?:yes|no)` is noncapturing. Earlier speculation that it returned path/ignore-error tuples was incorrect and was **retracted before any code was deployed**. Full source-contract fixture: original four ordered paths parsed as strings, five legal new-source positions accepted and four malformed source sets rejected. Keep the existing V4 candidate SHA-256 `7fa3866015893c34d44edef46b04d2cb20e266f277288f9fed211f5f8b931697` unchanged.

**Deployment is still HOLD.** Both the prior two SQLite backups remain preserved, Stage 1 private env and drop-in are absent after rollback, and the first V3 failing post-restart gate has not been recovered. The 27 checks do not simulate provisioning/restart end-to-end. Any new Stage 1/Phase 2 restart attempt requires a **fresh explicit operator approval**, a restricted maintenance window and safeguarded failure recovery. No test notifications authorized yet.

### Fresh V4 maintenance authorization — 2026-10-13

The operator expressly authorized another V4 migration attempt, **one planned service restart and one rollback/recovery restart if necessary**. The earlier V3 authorization is not reused. Start by running Stage 1 **on its own**, validating root-only file permissions/SELinux and unchanged active YAML and confirming `PRODUCTION_STAGE1=PASS`. Stage 1 does not reload systemd or restart Grafana. Only after this result and renewed preflight may the reviewed Stage 2 V4 candidate be run. Keep prior SQLite backups, root-only staging, the original four EnvironmentFiles and the sole live Email+Telegram Contact Point. No approval has been given for synthetic alert delivery or unrelated production edits.

**Actual execution:** Not yet reported under this authorization.

### Operator reports V4 Stage 1 PASS; stage 2 may proceed under existing approval

Under renewed user approval, the Stage 1 installer completed `PREINSTALL_VALIDATION=PASS`, `ROOT_ONLY_ENV_FILE=PASS`, `DROPIN_CREATED=PASS`, `SELINUX_NEW_OBJECTS=PASS`, `ORIGINAL_LIVE_YAML_UNCHANGED=PASS`, `PRODUCTION_STAGE1=PASS` with no daemon reload, Grafana restart, notifier send or secret-value print.

**Next guarded action:** launch only the reviewed `grafana236_stage2_v4_candidate.py` whose SHA-256 is `7fa3866015893c34d44edef46b04d2cb20e266f277288f9fed211f5f8b931697`, **one time**, as root on the Fedora host. The script will revalidate the private files, SELinux and four original sources, create a **third distinct** backup (no overwrite), require five additive sources on reload, perform the single approved restart, and poll stable readiness. Failure may trigger one recovery restart. Do not blindly retry; save `FAILED_GATE` and rollback status. The project repository's Email-only YAML is **not** a substitute for the live two-receiver contact file. Notification-send E2E validation remains separately gated.

**Stage 2 status:** NOT YET REPORTED.

## Fail-safe stop and rollback triggers

**STOP and return to the documented baseline** if the active contact YAML no longer matches backup, any required file is missing/insecure, `EnvironmentFile` ordering is unknown, Grafana start fails, the contact loses an integration or changes a receiver UID, the routing policy differs, rules no longer total 15, or either channel's delivery is unexpectedly broken.

**Rollback plan:** using the private copies, restore only this migration's contact YAML from `contact-original.yml`; remove or disable only the new migration-specific systemd drop-in (do not delete any preexisting overrides) and optionally the new environment file after it is no longer referenced; reload systemd unit metadata and restart Grafana **once**, then verify health, original Contact Point Email+Telegram, 15 rules, default policy and both channels. Preserve separate copies of pre-/post-change evidence (without secrets) and note any interruption. If rollback cannot restore the service, stop rather than trying blind unrelated configuration rewrites.

## Evidence and acceptance gate

Log timestamps and sanitized PASS/FAIL booleans: YAML + EnvironmentFile verified; restart once; service ready; rule count 15; receiver UID/name/type parity; Chat ID numeric and equivalent **without disclosure**; policy/grouping unchanged; scoped Firing and Resolved confirmed through both channels; no additional persistent alerts; no unexpected log errors.

**Do not mark Issue #236 closed solely from this migration:** direct-per-rule routing, grouping/repeat/anti-flap behavior and full clean-room policy/contact restore remain independent acceptance gates.

References: [Grafana alerting file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/), [Grafana admin provisioning reload](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/admin/), [systemd unit drop-ins](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html), [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html).
