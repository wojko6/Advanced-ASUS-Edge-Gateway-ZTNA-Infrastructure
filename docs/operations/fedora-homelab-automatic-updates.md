# Fedora Homelab — controlled updates for off-router observability

> **Status:** PARTIALLY DEPLOYED / MANUAL GRAFANA PILOT ACCEPTED / UNATTENDED INSTALLATION **HOLD**  
> **Evidence date:** 2026-10-18 (operator-pasted Fedora terminal output and operator-confirmed notification receipt).  
> **Platform:** Fedora 44 monitoring host. This page does **not** authorize or change ASUS firmware, Entware, DNS Guard, RouterCloud, Tailscale, NVIDIA, kernel, SSD permissions or Issue #235.  
> **Evidence:** [2026-10-18 worklog](../worklog/2026-10-18.md) and [sanitized operator observations](../../evidence/2026-10-18/fedora-update-operator-validation.md). For the current router and wider project, see [project status](../../PROJECT-STATUS.md).

## Scope and currently running components

This workflow keeps package **discovery**, operator-approved **installation**, and possible future **unattended installation** separate. The Fedora host is an observability/recovery dependency; its outage reduces visibility and alerting, but does not demonstrate an ASUS dataplane fault. The router remains the production gateway.

| Component | Operator-observed package, 2026-10-18 | Policy / remaining gate |
| --- | --- | --- |
| Grafana | `13.2.3-1` upgraded to `13.2.4-1` | **APPROVAL**; one manual pilot completed; database migrations and rollback need separate DR tests |
| syslog-ng | `4.11.0-1.fc44`, Fedora Project | **HOLD for AUTO** until source-authenticated ASUS → Fedora → Loki continuity is proved |
| Loki | `3.7.8-1` | **APPROVAL**; compatibility, ingester and storage/recovery gates outstanding |
| Alloy | `1.20.1-1` | **APPROVAL**; log pipeline E2E acceptance outstanding |
| Caddy | `2.11.7-1.fc44`, Fedora Copr `@caddy` | **HOLD for AUTO**; approve third-party repository policy and HTTP-over-HTTPS end-to-end test |
| Restic | `0.19.1-1.fc44`, Fedora Project | **HOLD for AUTO**; RouterCloud wrapper coordination, repo identity, integrity and restore drill outstanding |
| Tailscale | `1.98.8-1.fc44` on Fedora | **EXCLUDED**; networking/remote administration change control |
| Kernel / NVIDIA | independent host stack | **EXCLUDED**; separate stability/rollback workflow |

Version numbers are a **dated observation**, not a standing assertion of what is installed later. `victoria-metrics` was not identified as an RPM package under that exact name and the probed `victoria-metrics.service` was inactive; **no claim about its full runtime packaging or current operation is made**.

## Production versus laboratory boundary

**Production (operator-confirmed on Fedora):**

- `homelab-update-check.timer` is enabled/active and invokes `homelab-update-check.service`; `OnCalendar=*-*-* 13:00:00`, `RandomizedDelaySec=15min`, `Persistent=true`. It checks **syslog-ng, Grafana, Loki, Alloy, Caddy and Restic** with `dnf5 check-upgrade`, but **installs nothing**.
- On 2026-10-18 Update Watch v1 detected the `grafana` 13.2.4 candidate. Later manual Grafana Pilot **v2.3** performed the approved single-package upgrade. No separate unattended installer/timer or background update-agent deployment is evidenced.
- Production effects of the manual pilot: temporary Grafana stop/start for a consistent backup, DNF transaction of **Grafana only**, package upgrade and service restart. The operator installed the prerequisite `sqlite` package manually. These are real Fedora changes, not a read-only lab.
- The backup at `/var/backups/grafana/pilot-v2.3-20261018-195224-243712` was marked `COMPLETE` with SQLite integrity and archive verification PASS. **Never publish archive contents, environment values or private host paths beyond the sanitized evidence needed for recovery.** Backup presence does not prove a full restore.
- Post-upgrade: RPM `grafana-13.2.4-1.x86_64`; API HTTP 200; Grafana, syslog-ng, Loki, Alloy, Caddy active; 15 Grafana rules in SQLite, 0 paused; Grafana error-priority journal lines in the checked hour: 0; email and Telegram test messages operator-confirmed. **Per-rule delivery, all direct receiver mappings, provisioning reload persistence and rollback after schema migration were not independently revalidated.**

**Laboratory only (2026-10-18, no production integration):**

| Gate | Operator-reported outcome | Strict limit |
| --- | --- | --- |
| Engine v0.1 | `SELFTEST_TOTAL=10/10`; read-only `plan` PASS | No `apply` |
| Engine v0.2 | `SELFTEST_TOTAL=20/20`; `CANDIDATE_COUNT=0` | No live non-empty solver preview; backup check was a snapshot only |
| v0.3 same-UID locklab | 20/20 parser + `LOCKLAB_TOTAL=9/9` | Synthetic processes only |
| v0.4 root/non-root cross-UID | `CROSS_UID_LOCKLAB_TOTAL=13/13` | Temporary lock inode, not RouterCloud production |
| v0.5 cooperative exec jobs | `COOPERATIVE_JOB_TOTAL=15/15` | Synthetic job lifetime and failure handling |
| v0.6 descendant handoff | `DESCENDANT_LAB_TOTAL=12/12` | Synthetic fork/exec; includes `CLOEXEC` counterexample; actual wrappers not executed |
| v0.7 specifier audit | Both backup services `%h` entrypoints resolved to regular files | Static only |
| v0.8 existing-lock audit | `SELFTEST_TOTAL=10/10`; both wrappers show `flock`, FD and nonblocking hints | Same lock expression *textually*, not proven same inode |
| v0.9 lock-flow audit | `SELFTEST_TOTAL=10/10`; valid Bash, 1 `flock` hint in each wrapper | Runtime acquisition, duration and release **unproven** |

The v0.6 first static parser failed to recognize `%h` entrypoints (`STATIC_AUDIT_HOLD`). Subsequent v0.7 correctly resolved both. Do not treat these separate outputs as contradictory evidence of a failing backup.

**All laboratory engine variants are non-installing:** `APPLY_IMPLEMENTED=NO`; `AUTO_INSTALL_ENABLED=NO`. These tests do not grant production approval.

## Caddy, syslog-ng and Restic evidence boundary

**Caddy:** service `active` as user `caddy`, `/etc/caddy/Caddyfile` selected, `caddy adapt` and validation as `caddy` PASS. Three local certificate/SNI handshakes succeeded with TLS 1.3. **No HTTP request was sent**, so neither route handling, upstream health nor ASUS service behavior was proven. Running without explicit `EnvironmentFiles` is not proof of no environment variables at all.

**syslog-ng / Loki:** listener TCP/6514 and local Loki TCP/3100 were present. Loki HTTP 200 returned **721** source-query log entries in a 15-minute sample, but the exact ASUS sender identity was not verified. A positive Loki count is **not** end-to-end attribution. Revalidate router-source identity, continuity, and Alloy/Loki health independently before allowing automatic syslog-ng updates.

**Restic:** `restic 0.19.1` was present; no process named `restic` and both user backup services were inactive **at the sampled instant**. Both RouterCloud units launch `%h`-relative shell scripts containing Restic and `flock` hints. Static lock expressions match; runtime lock path/inode, critical-section lifetime, nested scripts and cross-UID production ownership were **not proved**. No `restic check` or restore drill ran; credentials/repository profile remain unknown. Do not reuse or replace existing RouterCloud locks without a separately reviewed integration.

## Fail-closed update design (not deployed)

1. Allowlist exact packages, version transitions, vendors and repositories; distinguish Fedora Project packages from Caddy COPR. Do not enable blanket `dnf5 upgrade`.
2. Before any update, verify prerequisites, host free space, disk/SQLite/backup consistency, configuration and no conflicting maintenance jobs.
3. Parse candidate metadata with `dnf5 check-upgrade --json`, but treat this only as **discovery**. Before applying a candidate, validate the *actual solved transaction* (including dependencies, removals, obsoletes, architecture, vendor and version) and **recheck** immediately before change. Reject unknown formats or any drift.
4. Use a stable, root-controlled **shared advisory lock** that both the updater and **all** RouterCloud backup entrypoints voluntarily acquire before beginning work and retain for their complete lifetime, including descendants where applicable. The existing update-watch lock protects only Watch/update-engine concurrency, **not** backup jobs. A process snapshot cannot close the race.
5. Preserve existing RouterCloud backup locks and timers; coordinate any new cross-UID lock wrapper with the independent RouterCloud project and test copies first. Never treat a lock's mere presence as enforced protection against non-cooperating processes.
6. Update one service at a time; perform service-specific checks. Any failed preflight/postflight stops the queue, produces an independent notification and requires explicit recovery decision. Never promise automatic downgrade of a migrated database without a restore test.
7. Grafana: backup database and private provisioning with strict permissions; check 15-rule baseline, active alert contacts, real message delivery and receiver parity. Be aware: checked-in `monitoring/grafana/provisioning/alerting/asus-email-contact.yml` is **Email-only**; it must **not** replace live Email+Telegram configuration.
8. Do not expose internal addresses, paths with confidential values, contact IDs, passwords, tokens, recipient addresses or log content in public evidence. The update stack has **not** been connected to its own Telegram/e-mail notifier.

## Pilot failure lessons

- Pilot v2.1 failed to place `--no-allow-downgrade` after `upgrade`; v2.2 corrected parser strictness. Human-oriented DNF5 output is variable; a fail-closed validator must distinguish malformed output from valid transactions.
- v2.2 refused to continue without `sqlite3`. Prerequisite validation belongs in `plan`, not just `apply`.
- An initial live `tar` of `/var/lib/grafana` reported `file changed as we read it`. v2.3 briefly stopped Grafana to make a consistent backup, then restarted/health-checked it before DNF. Failed/incomplete backups must never be treated as restoration points.
- `--assumeno` intentionally aborted preview with return code 1; *reviewed output*, not a raw zero return code, was the necessary plan gate.
- Positive service checks and message receipt do not certify full restore, all 15 rule deliveries or the currently untested Caddy/Restic/syslog-ng E2E gates.

## Pending work / explicit HOLDs

- Close the v0.6/v0.9 runtime gap using **isolated copies** of the actual RouterCloud wrapper shapes; establish real resolved lock inode and lifetime, descriptor inheritance, missing/untrusted-file handling and child exit behavior.
- Prove safe cooperation across root updater and user backup units, including scheduling races and all scripts that may invoke Restic. Obtain separate authorization before touching live units or timers.
- Test a scoped, approved HTTPS **HTTP** request through Caddy and source-authenticated fresh ASUS→syslog-ng→Alloy/Loki delivery, without exposing private endpoints or accidentally contacting the router.
- Verify the right Restic profile, a bounded `check` and isolated restoration sample; define a recovery procedure.
- Test candidate-bearing solver output on this Fedora host, DNF failure injection, queue-stop behavior, postflight and independent alerts. Explicitly approve each package's unattended eligibility.
- Only then design and authorize an unattended `systemd` installer service/timer. **None is deployed as of this evidence date.**

See [operational index](../operations.md), [monitoring README](../../monitoring/README.md), [worklog](../worklog/2026-10-18.md), and [audit](../audits/2026-10-18-fedora-update-documentation-review.md).
