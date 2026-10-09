# Issue #200 — protected addon directory audit and acceptance (2026-10-09)

**Scope:** `/jffs/addons/asus-edge/{backup,backups,legacy,rollback}` on the reference ASUS TUF-AX5400.  
**Disposition:** [Issue #200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200) **closed as completed** for the original world-writable directory exposure.  
**Evidence class:** operator-provided read-only terminal output, reviewed source code and isolated GitHub Actions fixtures; **not** an independent live installer/rollback exercise.

## Background

The 2026-10-08 preflight identified four root-operated addon directories initially exposing mode `0777`. An operator-held, encrypted off-router snapshot was hash-checked and successfully extracted/restored in a disposable Fedora test. A 698-entry permission manifest found 76 planned changes (59 directory modes, 17 file modes). The first intended live apply **stopped at preflight** because the expected corrections were already present. A later full 698-entry comparison reported zero remaining metadata differences; the identity of the actor or exact prior command applying the changes is **not established**. Do not imply that the aborted apply made the corrections.

## Final read-only router audit

The optional, separately installed ARM EABI5 BusyBox 1.36.1 was verified against its pinned binary SHA-256 before its FIND implementation was used for the recursive inventory. The firmware `/bin/busybox` and system `PATH` were unchanged.

| Object set | Entries | Top-level owner | Top-level mode |
| --- | ---: | --- | --- |
| `backup/` | 72 | root:root | 0700 |
| `backups/` | 544 | root:root | 0700 |
| `legacy/` | 3 | root:root | 0700 |
| `rollback/` | 79 | root:root | 0700 |
| **Total** | **698** | — | — |

- **697** entries owned by UID:GID 0:0.
- **1** deliberate unchanged owner exception, described below.
- **0** group-writable entries, **0** world-writable entries, **0** symlinks and **0** invalid inventory records.
- Final project healthcheck reported **0 failures, 0 warnings** after the hardening checkpoint, including its configured network/DNS/service checks. This does not constitute an end-to-end recovery rehearsal.

### Owner exception

The sole exception is `backups/pihole-session-before-7d.toml`:

| Attribute | Observed |
| --- | --- |
| UID:GID | 999:999 (the Pi-hole service identity in this environment) |
| Mode | 0640 |
| Hard-link count | 1 |
| Size | 72,153 bytes |
| Modification time | 2026-09-28 17:30:58 +02:00 |
| Parent `backups/` | root:root, 0700 |

A read-only, filename-only search found **0** exact-basename matches in the inspected active `/jffs/scripts/*`, addon `bin/*` and Entware `/opt/etc/init.d/S*` scripts, and **no** exact match in `cru l`. This is not a proof of no dynamic, archived, manually invoked or historical consumers. Neither the contents nor the exact creation provenance were inspected. The file is **retained**, without `chown`, `chmod` or deletion.

## Writer/consumer review

- `scripts/install.sh` creates root-run snapshots in `backups/install-*`, prunes only managed snapshot names, preserves previous hooks in `legacy/`, and has a transactional file rollback path.
- `scripts/uninstall.sh` reads preserved hooks from `legacy/`.
- `scripts/backup.sh` includes `legacy/` in the CORE archive (but not the optional `tools/busybox/` tree).
- `scripts/restore.sh` uses a separate private temporary rollback workspace; restore may reconstruct archived `legacy/` after successful validation.
- Active managed `firewall-start` and `wan-event` wrappers have the expected `ASUS_EDGE_MANAGED_HOOK` marker, preserved legacy-path reference and `EDGE_RUN_LEGACY_HOOKS` guard; two observed assignments were both `0` and none `1`.
- Active process-identity samples included root-operated `tailscaled`/`syslog-ng` and non-root `unbound` (65534) and `pihole-FTL` (999). The latter cannot ordinarily traverse the root-only 0700 directory; these bounded snapshots are not complete process syscall tracing.
- Exact directory-prefix cron references: 0 observed; the search did not trace dynamically constructed paths.

## Isolated regression and recovery boundaries

- [PR #209](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/209) merged two test-only changes on 2026-10-09; the final CI reported **8/8 successful checks**.
- The test harness exercised 0700 private directory/sentinel preservation through a successful isolated install, rejected corrupted artifact and deliberate installer-failure rollback; separate clean-room restore retained a 0700 archived `legacy/` while leaving three unrelated protected trees untouched.
- These tests use disposable runner filesystems. They do **not** prove a production rollback, service-identity permission parity on the router or a full empty-device reconstruction.
- Issue #129 remains open for clean-device Pi-hole-aware Disaster Recovery, package/account/FTL-capability reconstruction and full restored-target acceptance. The independently successful 2026-10-09 production reboot on the *existing* router does not close #129.
- Live emergency install/uninstall/restore was intentionally **not performed** just to close #200.

## Decision and follow-up

**Accepted for the original #200 scope:** the world-writable backup/legacy/rollback exposure is absent in the complete, operator-reported 698-object audit; no further permission change is warranted. Off-router backup integrity, bounded code review, isolated regression and a clean healthcheck support closing the permission-hardening issue. The initial modification provenance and production emergency rollback remain **explicit limitations**, not silent PASS results.

If future changes introduce a non-root writer, a path-mode regression, or dynamically generated references that conflict with 0700, open a new tightly scoped issue or reopen #200. Do not lower directory modes or delete the Pi-hole metadata exception without a dedicated consumer/retention review.

Related documentation: [current project status](../../PROJECT-STATUS.md), [router recovery contract](../../docs/router-disaster-recovery.md), [optional BusyBox validation](custom-busybox-armv7-live-validation.md), and [2026-10-09 worklog](../../docs/worklog/2026-10-09.md).
