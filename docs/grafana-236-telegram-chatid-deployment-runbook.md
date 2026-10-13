# Grafana #236 — Telegram Chat ID provisioning migration (deployment & rollback plan)

**Status:** REVIEW ONLY — production switch **not authorized or executed**  
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

## Stage 0 — immediately before implementation (read-only; STOP on failure)

1. Confirm Grafana v13.2.3, active `grafana-server.service`, count **exactly 15** rules, no failures, correct receiver counts and current delivery status. Do not dump contact-point settings or credentials.
2. Verify unique matching contact YAML, exact equality with `contact-original.yml`, private stage file modes/ownership and Chat ID match; re-run the approved `STAGING_INTEGRITY` and `DEPLOYMENT_PREFLIGHT` scripts **just before deployment**.
3. Inspect **effective systemd drop-in names** and `EnvironmentFile` ordering **without printing Environment values**; check candidate drop-in basename for collisions and confirm configured `EnvironmentFile` paths can coexist without resetting original sources.
4. Choose a stable protected path such as `/etc/grafana/private/telegram-chatid.env` (0600 root/root) and a unique named systemd drop-in under `/etc/systemd/system/grafana-server.service.d/`. Ensure backup/rollback of all existing contents and correct SELinux labeling on Fedora. If names already exist, STOP for operator review.
5. Confirm a controlled maintenance window and **explicit operator approval** for a short production Grafana restart and for any separate test notification. Identify how operator will reach Grafana if it fails.
6. Prepare and validate an **offline** rollback: revert the exact active contact YAML from the private original byte copy; remove only this migration's drop-in/env source; run `daemon-reload` and **one controlled restart**; re-verify 15 rules and expected contact/policy. Do not overwrite unrelated overrides or remove preexisting files.

## Stage 1 — planned single production switch (NOT YET EXECUTED)

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
