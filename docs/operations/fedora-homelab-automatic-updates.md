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

---

## 2026-10-19 addendum — Fedora Recovery validation and return to service-scoped updates

> **Later operator-reported checkpoint, not a retroactive change to the 2026-10-18 evidence above.** The operator verified a separate **Fedora host Recovery** mechanism through a real isolated Btrfs receive. This does **not** prove that the **RouterCloud backup repository** was restored or that its `flock` mechanism is coordinated with a root updater.

- User-space RouterCloud backup/maintenance units and persistent timers were verified in the **user** systemd manager. Journals and bounded application markers for recent scheduled runs were successful. System-manager `not-found` and initial script-path lookup failures were **diagnostic context/specifier errors**, not failures of the real user units. Static Bash/DAC/Restic/flock checks passed; actual shared cross-UID lock lifetime and RouterCloud restore remain unproven.
- The host recovery baseline includes read-only Btrfs snapshots of Fedora's system root and separately managed nested machines volume, with separate boot/EFI archives. The operator reported successful independent integrity checks, representative file restoration, a second physical NVMe encrypted Restic repository, full `restic check --read-data`, and **successful real `btrfs receive` of both exported subvolumes into an isolated disposable image**.
- **Strict limits:** This recovery repository is separate from RouterCloud application backups. It is on a second NVMe **inside the same workstation**, not off-site; live databases are not asserted application-consistent, separate `/home` is not included, and complete Live USB recovery / a booted restored Fedora are **NOT TESTED**. The operator deferred V21A Live USB testing and chose to retain/refresh the baseline later.
- The declared main goal is **automatic installation of explicitly allowed individual homelab service updates only**. The historical Fedora Recovery work is a completed prerequisite/checkpoint, not authorization for unattended OS-wide `dnf upgrade` or automatic kernel/NVIDIA changes. Grafana, Loki, Alloy and other higher-risk components still require separate approvals and verified service-specific recovery paths.
- No 2026-10-19 package installation, production RouterCloud wrapper edit, ASUS mutation, firmware change or service reboot was reported in this update/recovery workstream. The previous-day manually approved Grafana pilot remains dated 2026-10-18.

**Decision:** preserve the existing `homelab-update-check.timer` in check-only mode; continue solver transaction preview, package allowlisting, cooperative locking, per-service pre/postflight and notification design. No general unattended installer exists. **`AUTO_INSTALL_GATE=HOLD`.**

See the [dated Fedora Recovery checkpoint](fedora-recovery-checkpoint-2026-10-19.md) and [October 19 sanitized worklog](../worklog/2026-10-19.md).


## Later 2026-10-19 checkpoint — live DNF5 watcher remediation

Evidence: operator-executed Fedora terminal outputs, not GitHub CI. This later checkpoint supersedes only the earlier statement that the watcher's production source was untouched on October 19.

- Non-root DNF5 discovery initially failed: six libdnf5 state TOML files were root-owned mode 0600 versus installed RPM manifest 0644. A targeted operator-approved permission repair restored all six files to 0644. Subsequent DNF5 JSON discovery exited 0 with zero update candidates; no package installation occurred. Original creation cause remains unproven.

- The root systemd check-only watcher retained UMask=0077. Laboratory policy tests, Bash quoted-array replay, child umask scope and static symlink trust checks passed. A v2.2.1 installer receipt-serialization error occurred AFTER backup creation but BEFORE live replacement; it did not patch production.

- Operator-approved v2.2.2 production deployment changed exactly one DNF invocation line, setting umask 0022 only for the DNF child; parent service UMask=0077, timer and all backup jobs remained unchanged. Durable backup, patch checksum, Bash syntax, SELinux/xattr metadata and static postflight were accepted. Rollback receipt remains private.

- The operator then ran the actual systemd check-only unit: Result=success, ExecMainStatus=0, normal oneshot inactive/dead afterwards. Post-run patch checksum, six DNF state file modes and non-root DNF5 JSON discovery all passed (zero candidates). This proves one successful live check-only invocation; it does not prove a future file recreation, live candidate-bearing DNF solver, unattended install, backup cooperation or application restore.

- Next: read-only root/user-manager backup lock coordination review. Do not execute or modify backup wrappers, take a production lock, reveal credentials, alter timers, or touch ASUS, RouterCloud, Issue #235 or Fedora Recovery. AUTO_INSTALL_GATE=HOLD.


### 2026-10-19 later backup runtime mapping audit (static only)

- Operator-run non-root V1.0 coordination audit: 10/10 self-tests passed. The two live user-manager backup/maintenance units and timers were loaded/active as appropriate; both installed wrapper shapes used the same XDG_RUNTIME_DIR-or-/tmp and UID-based advisory lock name with fd 9 and nonblocking flock. User lock file was absent at the sampled instant. This supports source-level similarity only, not same runtime inode or root-user coordination.

- Operator-run V1.1 user-manager runtime mapping audit: 8/8 self-tests passed; manager and login XDG_RUNTIME_DIR resolved to the same standard owner-0700 location. Both backup services use PrivateTmp=yes, UMask=0077 and were inactive at the instant sampled. Fallback /tmp separation risk was not needed under the observed manager environment, but actual service-process environment was not observed.

- Existing root Update Watch is check-only and uses UMask=0077. A future root installer cannot assume that expanding the user's UID-based lock expression yields the same pathname or inode: root UID and environment differ. Neither the user backup tasks nor root updater has deployed a shared cross-UID cooperation lock.

- Next test is an isolated root-owned fixture under /run with a controlled user-group-accessible advisory lock to establish bidirectional flock contention in lab only. No live backup process, unit, timer, file, or lock should be touched. The real resolved inode/descriptor lifetime and production coordination remain HOLD. AUTO_INSTALL_GATE=HOLD.


### 2026-10-19 cross-UID lock test V1.2 (isolated root-owned fixture)

- Operator reported 8/8 policy self-tests PASS and a successful real root/user advisory flock test in a disposable /run fixture: same root-owned group-accessible lock inode, root-held/user-blocked and user-held/root-blocked, controlled directory nonreplaceability, successful reacquisition, and cleanup PASS.

- This is an isolated fixture and does not execute either production backup wrapper, the check-only Update Watch, Restic or DNF. It does not demonstrate production user-manager to root-installer coordination, descendant fd9 lifetime in the live wrappers or safe reconfiguration of their locks. The root updater still lacks a live shared cooperative lock. AUTO_INSTALL_GATE=HOLD.

- Follow-up synthetic Bash lifetime test planned against the observed fd9/flock -n/exit-zero-on-busy shape. A busy backup wrapper's exit 0 must not be interpreted as completed backup; collect app result markers separately.
