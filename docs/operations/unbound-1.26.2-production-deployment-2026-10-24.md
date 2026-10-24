# Unbound 1.26.2 — production deployment and bounded acceptance (2026-10-24)

> **Status:** DEPLOYED / bounded production acceptance PASS on the ASUS TUF-AX5400 (GNUton Asuswrt-Merlin, Entware ARMv7).
> **Evidence source:** operator-provided command output on the real router and Fedora workstation. This is a sanitized documentary record, not execution by the GitHub workflow.
> **Change scope:** exactly five Unbound packages from `1.26.1-1` to `1.26.2-1`. No DNS Guard policy, RouterCloud, SSD-security, #235/#278/#287 or unrelated firmware change.
> **Historical context:** the first October 24 attempt failed, was rolled back, and required an RFC 5011 trust-anchor directory repair. See the [incident case study](../case-studies/unbound-dnssec-autotrust-opkg-incident-2026-10-24.md). The **later**, corrected R2 update was successful.

## 1. Pre-deployment safety and isolated validation

- After the initial incident, the production daemon was restored on five `1.26.1-1` packages with an active automatic trust anchor inside a dedicated `dnssec-auto` directory, owned by the unprivileged service account and with restricted permissions. The historical root-level anchor remained separate; the active anchor was neither overwritten with the old copy nor published.
- Fedora-only full-dependency ARMv7/QEMU/rootless-Podman lab:
  - V6: exact 1.26.2 IPK `libunbound`, real staged dependencies, chroot, UID/GID 65534, zero effective capabilities, UDP/TCP DNS and 30-second stable process identity PASS.
  - V7.1: standalone local signed DNSSEC validation with correct `AD=1` and corrupted RRSIG `SERVFAIL` on UDP/TCP; 16/16 self-tests PASS.
  - V8.1: three local authoritative tiers (synthetic ROOT → TLD → CHILD) visited by iterative recursion, signed DS/DNSKEY chain, correct AD/SERVFAIL on UDP/TCP; 22/22 self-tests PASS.
  - V9: RFC 5011 old root KSK `VALID`, new KSK `ADDPEND`, writable anchor-state persistence and preservation across a **process restart within the same disposable container**; 26/26 self-tests PASS. The real 30-day acceptance interval was **not** completed.
- These tests do **not** establish public Internet DNSSEC behavior or any ASUS reboot persistence.

## 2. Controlled R2 maintenance on the real ASUS

- R2 scripts were unpacked and their source SHA-256 manifest passed.
- Before any new install: direct existing Unbound 1.26.1 TCP DNSSEC valid `AD=1` and bogus `SERVFAIL` PASS; router dnsmasq and Pi-hole client DNS PASS.
- A separate private R2 staging directory received ten local IPKs (five upgrade and five downgrade) plus the preserved custom `S61unbound`; full 11/11 checksums PASS. The **earlier** failed-transaction directory and its `ROLLBACK_RUNNING_1261` journal were left intact.
- Fresh read-only D0: 11/11 staged artifacts PASS, all five installed old package versions `1.26.1-1`, active `dnssec-auto` anchor owner/mode PASS, custom service Manager checksum/metadata PASS, live processes and DNS sockets PASS, local DNS Guard cron registration present, disk-space margin PASS.
- Attended D1: controlled service stop, exact local `opkg` transaction, custom Manager restoration and fresh daemon start. Reported results:

~~~text
OPKG_UPGRADE_RC=0
UNBOUND_PACKAGE_VERSION=1.26.2-1_5_OF_5
MANAGER_RESTORED=PASS_SHA_MODE_OWNER
UNBOUND_1262_BASIC_SERVICE_CHECK=PASS
D1_RESULT=PASS_1262_RUNNING_AWAIT_D2_DNSSEC
~~~

- No automatic rollback was needed in the successful R2 transaction.

## 3. Independent production DNSSEC and client-path acceptance

The separate, read-only D2 confirmed version/Manager/socket checks and tested direct Unbound DNSSEC through an IP-based SSH **TCP** tunnel. Subsequent read-only `dig` commands executed on the ASUS queried the Unbound loopback listener directly over **UDP**.

| Actual test | Result |
| --- | --- |
| Five installed Unbound packages report `1.26.2-1` | **PASS** |
| Preserved custom `S61unbound`, active config, process and sockets | **PASS** |
| Direct Unbound TCP: valid DNSSEC `NOERROR` / `AD=1` | **PASS** |
| Direct Unbound TCP: bogus DNSSEC `SERVFAIL` | **PASS** |
| Direct Unbound UDP: valid DNSSEC `NOERROR` / `AD=1` | **PASS** |
| Direct Unbound UDP: bogus DNSSEC `SERVFAIL` | **PASS** |
| Router dnsmasq client DNS | **PASS** |
| Pi-hole client DNS | **PASS** |

Bounded acceptance markers:

~~~text
D2_RESULT=PASS_TCP_DNSSEC_AND_CLIENT_DNS
UNBOUND_1262_DIRECT_UDP_AD1=PASS
UNBOUND_1262_DIRECT_UDP_SERVFAIL=PASS
~~~

## 4. Remaining untested gates and retention

- **DNS Guard at original D2 cutoff:** only cron registration was observed; the D2 acceptance itself did **not** test failover. **Later October 24 read-only incident-log analysis** independently identified a spontaneous production system-resolver transition to WAN bootstrap at **10:25:02** and promotion to local Pi-hole at **11:08:01** during the earlier failed update. This is actual historical behavior, **not a deliberate outage-injection test**; LAN/Tailscale client DNS continuity and watchdog per-minute execution were not proven. See the [companion monitoring case study](../case-studies/dns-guard-grafana-alert-delivery-dns-failure-2026-10-24.md).
- **Persistence:** no router reboot/cold power-cycle after the R2 production upgrade, no long-duration soak or full blank-router recovery was tested here.
- **RFC 5011:** the laboratory proved `ADDPEND` and same-container process-restart persistence, **not** 30-day key promotion or router reboot persistence.
- **Historical root-cause boundary:** missing pre-incident production directory ownership metadata remains unknown; the isolated `opkg` reproduction must not be presented as that missing observation.
- **Backups:** preserve the five previous-version rollback IPKs, the original incident journal, the R2 maintenance backup/journal, original custom Manager and active-anchor protection. Keep binary backups, private configs, key contents, host specifics and operator logs **outside the public repository**.
- Existing config/permissions hardening (including historical `0666` config), DNS Guard policy, SSD security work and other projects are excluded from this completed version upgrade.

**Final classification:** `PRODUCTION_UNBOUND=1.26.2-1`; `D1=PASS`; `D2_TCP_DNSSEC_AND_CLIENT_DNS=PASS`; `DIRECT_UDP_DNSSEC=PASS`; `DNS_GUARD_UNPLANNED_FAILOPEN_FAILBACK=OBSERVED_POSTHOC`; `DNS_GUARD_CONTROLLED_FAULT_INJECTION=NOT_TESTED`; `ASUS_REBOOT_PERSISTENCE=NOT_TESTED`; `ROLLBACK_REQUIRED=NO`.

This document closes **the authorized Unbound package-upgrade and bounded DNSSEC/client acceptance task**, not the separate recovery/failover or reboot-validation tasks.


## 5. Later actual ASUS reboot: functional persistence with an RFC 5011 file-mode exception

**Evidence collected after the earlier R2 D1/D2 acceptance:** the operator subsequently rebooted the real router. The following was measured after the new boot (initial post-boot test at approximately 3 minutes of uptime, October 24 CEST). It **changes** the historical `ASUS_REBOOT_PERSISTENCE=NOT_TESTED` acceptance boundary for the **specific restart observed**, but is not evidence of a cold power-loss boot, repeated boots, uninterrupted DNS during restart, or long soak.

| Actual post-reboot test | Observation |
| --- | --- |
| Five Entware Unbound packages still report `1.26.2-1` | **5/5 PASS** |
| Unbound and Pi-hole FTL process presence; checkconf; Unbound TCP/UDP loopback listener | **PASS** |
| Active automatic trust-anchor directive points once to `dnssec-auto/root.key` | **PASS** |
| DNSSEC good `NOERROR` with `AD` vs bogus `SERVFAIL` via direct Unbound **UDP** | **PASS / PASS** |
| Same positive/negative DNSSEC via direct Unbound **TCP** | **PASS / PASS** |
| Router dnsmasq and dedicated Pi-hole client-path DNS | **PASS / PASS** |
| Router system DNS selected local Pi-hole; DNS Guard watchdog registered; break-glass inactive | **PASS / PASS / INACTIVE** |
| Chroot root `root:root 0755`, private anchor subdirectory `65534:65534 0700` | **PASS** |
| Active RFC 5011 `root.key` file owner `65534:65534` | **PASS** |
| Active RFC 5011 `root.key` file **mode** | **0666, NOT the expected 0600 — HARDENING CHECK OPEN** |

The later read-only metadata audit found `root.key` to be a nonsymlink regular file, owned by UID/GID 65534, **mode 0666**, 1,251 bytes; `mtime` **15:48:55.133 +0200**, `ctime` **15:48:55.140 +0200**. The estimated boot time, derived from the collected clock and `/proc/uptime`, was **15:48:03 CEST**: file modification and metadata changes occurred roughly **52 seconds after boot**. The data do not individually prove whether the original inode was replaced or which process set the mode. The startup Manager contained no literal `umask`, `unbound-anchor`, `chmod` or `chown` keyword in the bounded scan; the running daemon's reported UID was 65534, but the router's `/proc/<pid>/status` did not provide a `Umask` field.

**Independent source-level explanation:** upstream Unbound **release-1.26.2** function `validator/autotrust.c:autr_write_file()` writes the automatic trust-anchor state to a temporary sibling via `fopen(tempf, "w")`, then replaces the original through `rename(tempf, fname)`. The function does not preserve the prior file's `0600` mode or call `chmod/fchmod`. Newly created files are therefore governed by the effective process creation mask (and any inherited pre-existing temporary-file state); a fresh regular file at `0666` is *consistent with* `umask 000`, **not proof of the daemon's actual umask**. Upstream code: [Unbound 1.26.2 autotrust.c](https://github.com/NLnetLabs/unbound/blob/release-1.26.2/validator/autotrust.c). Public root DNSSEC trust-anchor material is not a secret; unauthorized modification is the concern. The parent directory `0700` owned by the daemon UID prevents ordinary other users from traversing to the file, materially limiting exposure despite its `0666` bits.

**Safety decision:** no `chmod`, daemon restart, startup-mask change or key-content read was performed. Functionality and bounded restart persistence are **PASS**, but **file-mode hardening remains unresolved** and might revert upon subsequent atomic anchor replacement. Assess a process-level `umask 077` change in an isolated Fedora/ARMv7 lab and evaluate effects on other daemon-created files *before* any separately approved router deployment.

**Updated gate:** `ASUS_REBOOT_2026_10_24_FUNCTIONAL=PASS`; `RFC5011_ANCHOR_PARENT_DAC=PASS`; `RFC5011_ANCHOR_FILE_MODE_0600=NOT_MET_CURRENT_0666`; `REBOOT_PERSISTENCE_REPEATED_COLD_BOOT=NOT_TESTED`; `PRODUCTION_CHANGES_DURING_POSTBOOT_AUDIT=NO`.


## 6. Fedora-only actual ARMv7 RFC 5011 umask comparison — V1/V2

**New post-reboot hardening investigation (operator-run October 24; no ASUS contact):** a synthetic `fopen("w")` + atomic `rename()` model V1 passed **3/3**: with a prepared `0600` initial anchor and a newly created replacement inode, `umask 000` produced `0666`, `022` produced `0644`, and `077` produced `0600`. Corresponding new-file/new-directory modes were `0666/0777`, `0644/0755`, `0600/0700`. V1 ran an unprivileged Fedora-only synthetic writer; it is not a daemon runtime result.

**V2 used the previously hash-pinned V9 Fedora rootless Podman/QEMU fixture and real Unbound 1.26.2 ARMv7, with the exact verified IPK libunbound and staged real ARM dependencies.** `--self-test` passed the pinned V9 26/26 fixture checks and both patch contracts; `--inspect` confirmed local staging, no pull and the rootless container prerequisites; `--run` executed two separately patched, disposable V9 cases, inserting `umask 000` or `umask 077` immediately before **both** real daemon launch commands. Original V9 was not modified.

| V2 production-independent runtime check | `umask 000` | `umask 077` |
| --- | --- | --- |
| Initial synthetic trust-anchor mode | `0600` | `0600` |
| Actual Unbound RFC 5011 auto-trust-anchor replacement | **0666 PASS** | **0600 PASS** |
| Different inode after atomic rewrite | **PASS** | **PASS** |
| Existing synthetic root KSK `VALID`, new root KSK `ADDPEND` | **PASS** | **PASS** |
| RFC 5011 state survives daemon **process restart** | **PASS** | **PASS** |
| Anchor mode after second actual daemon launch | **0666 PASS** | **0600 PASS** |
| Private trust-anchor parent remains `65534:65534 0700` | **PASS** | **PASS** |
| Newly created launcher log mode (demonstrates wider mask effect) | `0666` | `0600` |
| Chroot/UID and exact Unbound 1.26.2 ARMv7 runtime dependency checks | **PASS** | **PASS** |

Run verdict: `V2_FEDORA_REAL_ARMV7_UMASK=PASS_000_AND_077`; `V2_RFC5011_ADDPEND_AND_RESTART=PASS_BOTH_UMASKS`; `V2_RESULT=PASS_TWO_REAL_ARMV7_RFC5011_CASES`. `ASUS_CONTACTED=NO`, `PRODUCTION_CHANGES=NO`, `DEPLOYMENT_GATE=HOLD`.

**What this proves:** the observed `0666` post-reboot mode is reproduced by the **real** ARMv7 Unbound with `umask 000` in a controlled chroot; changing its startup mask to `077` causes real RFC 5011 atomic replacements to use `0600` and preserves the tested KSK transition and daemon-restart behavior. The test additionally shows a **potential compatibility impact**: all newly created files inherit the stricter mask, not just the anchor. The launcher log was `0600` in the `077` case.

**What remains unproven:** the actual effective `umask` of ASUS production Unbound at the moment of its 15:48:55 anchor rewrite; the identity of the production writer; full impact of `umask 077` on live router logs/sockets/PID files and startup orchestration; real 30-day RFC 5011 promotion; router persistence after changing a launcher; cold-power reboot after any prospective hardening. **Do not modify `S61unbound`, perform a router restart or set production chmod/umask on the basis of V2 alone.** A separately approved candidate would require static launch-chain review, isolated compatibility/negative regression tests, an explicit rollback plan and a post-change production acceptance window.

**Status:** `ARMV7_UMASK_MODEL_V1=PASS_3_OF_3`; `ARMV7_UMASK_REAL_V2=PASS_BOTH_MASKS`; `RFC5011_PRODUCTION_FILE_0600=OPEN`; `PRODUCTION_DEPLOYMENT_GATE=HOLD`.


## 7. Scoped umask: real ARMv7 V3 launcher and permission regression

**Date/evidence:** October 24, operator-run Fedora rootless Podman/QEMU test output, `--self-test`, `--inspect` and `--run`. V3 script checksum as supplied in the validated run workflow: `4b6f55b407325b870b38afca5bd2639f95f9acd4350eb51b52aa91a3cda4b51c`. The operator output confirms execution of the script's three modes; do not infer a new production deployment.

V3 patched a disposable copy of the same SHA-256-pinned **V9** source for both daemon launches. The **parent shell** used `umask 022` for the launcher-created artifacts, while a **subshell invoking the real Unbound 1.26.2 ARMv7** used `umask 077`. V9 original remained unchanged. Self-test: original V9 fixture **26/26 PASS**, source pin and patch-contract checks PASS. Inspect: staging hash, rootless Podman, locally available container image without pull, ARM32 NSS dependency and source gates PASS. Runtime:

| Scoped V3 check | Observed result |
| --- | --- |
| Real ARMv7 Unbound, exact verified IPK library and staged dependencies | **PASS** |
| RFC 5011 old root KSK `VALID` / new root KSK `ADDPEND` | **PASS** |
| First auto-trust-anchor mode (child `umask 077`) | **0600 PASS** |
| Parent launcher log, PID file and synthetic marker (parent `umask 022`) | **0644 PASS** |
| Read access for a separate UID 65534 to lab PID/log; no write to PID | **PASS** |
| RFC 5011 state preserved after **process** restart | **PASS** |
| Anchor mode after second launch | **0600 PASS** |
| Parent launcher log and PID file after second launch | **0644 PASS** |
| No parent `umask` leak in tested shell context | **PASS** |

Final marker: `V3_RESULT=PASS_SCOPED_CHILD_077_PARENT_022_ACTUAL_ARMV7`. `ASUS_CONTACTED=NO`, `PRODUCTION_CHANGES=NO`, `DEPLOYMENT_GATE=HOLD`.

**Important scope boundary:** V3's PID file is **written by its laboratory shell**, not the production `S61unbound` process manager. The test does **not** confirm the effective production daemon mask, startup orchestration, PID/log ownership, `rc.func` compatibility, full pre-/post-chroot FD behavior or watchdog recovery. The public `router/scripts/services-start` also has a separate **direct Unbound recovery** path which invokes the daemon without `S61unbound`; reviewing only the Entware Manager would be incomplete. Parent file modes observed in the disposable container are not a blanket recommendation to expose production logs/PID files.

**Next gate (read only):** inventory exact production Manager file and hash, `rc.func` start path, live PID file/daemon/diagnostic log DAC, and all startup paths including direct recovery; compare privately against staged rollback Manager. Then run Fedora-only static and runtime negative regressions for both paths before proposing any patch. No authorized `S61unbound` edit, no DNS Guard changes, no router service restart or further deployment at this stage.

**Status:** `RFC5011_SCOPED_UMASK_ARMV7_V3=PASS`; `PRODUCTION_MANAGER_VERIFIED=NO`; `PRODUCTION_UMASK_PATCH=NOT_DEPLOYED`; `DEPLOYMENT_GATE=HOLD`.


## 9. V4 real daemon PID: preflight failure and Fedora-only V4.1 correction

**Operator report, October 24:** V4 `--self-test` PASS (pinned V9 **26/26**) and `--inspect` PASS. Full `--run` **FAILED** before Unbound daemon PID-mode assertions. In the disposable Podman/QEMU guest, adding `pidfile: "/opt/var/run/unbound.pid"` caused `unbound-checkconf` to abort:

```text
/opt/var/run: No such file or directory
unbound-checkconf: fatal error: pidfile directory does not exist
LAB_RESULT=FAIL_PRECHECK_OR_RUNTIME:QEMU_CHECKCONF_FAILED
V4_RESULT=FAIL:REAL_ARMV7_RUNTIME_OR_PID_DAC
```

**Root cause in test harness:** the V4 patch created the directory `/opt/var/run` alongside the **first daemon launch**, which occurs **after** the earlier V9 `unbound-checkconf` step. This is a lab staging-order error, **not evidence of a router Unbound regression**. `RUNTIME_TREE_LIBUNBOUND_MATCH_IPK=NO` was also displayed, but V9 correctly reported `CONTAINER_EXACT_IPK_LIBUNBOUND=PASS` because it deliberately replaces the build-tree library with the verified IPK library in the container.

A separate Fedora-only V4.1 script was prepared without touching the original V4 or pinned V9. It moves directory creation to the **initial disposable-container setup**, before config validation, with `0:0 0755`, symlink and ordering checks. Local `bash -n`, V4.1 self-test/pinned V9 **26/26**, generated-copy syntax and static PID-directory-before-checkconf assertion: **PASS**. **Full ARMv7 runtime V4.1 remains NOT TESTED by the operator**, so the predicted real daemon PID `0600` and negative unprivileged-read regression are *not* recorded as PASS.

**Gate:** `V4_RUNTIME=FAIL_LAB_PIDDIR_PRECHECK`; `V4_1_PATCH_SELFTEST=PASS`; `V4_1_ARMV7_RUNTIME=PENDING`; `PRODUCTION_MANAGER_VERIFIED=NO`; `PRODUCTION_CHANGES=NO`; `DEPLOYMENT_GATE=HOLD`.

## 10. V4.1 actual ARMv7 daemon PID compatibility

**Operator-run Fedora-only V4.1:** all three modes (`--self-test`, `--inspect`, `--run`) passed; the prior missing PID directory was prepared before `unbound-checkconf` (`V41_PIDDIR_BEFORE_CHECKCONF=PASS_ROOT_0755`). Pinned V9 passed 26/26 self-tests.

Real Unbound 1.26.2 ARMv7, using the exact verified IPK library, created its **own** PID file with `root:root 0600` under a child-scoped `umask 077` in both modeled launch paths. UID 65534 could not read that PID file. The RFC 5011 anchor was `65534:65534 0600` after the initial launch and daemon restart. Synthetic old/new root KSK `VALID/ADDPEND` state survived restart. Parent-created log and helper PID remained `root:root 0644`, with no parent umask leakage.

Result: `V41_RESULT=PASS_REAL_ARMV7_PID_0600_REPRODUCED_WITH_SCOPED_077`; `V41_COMPATIBILITY=HOLD_PRODUCTION_PID_PERMISSION_REGRESSION_CANDIDATE`; `V4_PRODUCTION_PID_0644_COMPATIBILITY=NOT_MET_IN_FRESH_077_CASE`.

**Risk boundary:** This is a demonstrated **file-mode change**, not yet a demonstrated failure of a particular ASUS component. Repository search found `unbound.pid` references in `services-start` and configuration, while DNS Guard, web UI, WAN handler and healthcheck use process presence checks such as `pidof unbound`. The actual firmware/Entware PID consumers, startup Manager behavior, and need for world-readable PID have not been established. V4.1 modeled two launch paths but **did not execute** production `S61unbound`, `rc.func`, or `services-start`.

**Decision:** do not change live PID permissions, patch firmware, adjust daemon umask on ASUS or restart DNS. Complete a read-only inventory of actual PID readers before choosing whether `0600` is acceptable or whether a separate PID mode mechanism is necessary. `ASUS_CONTACTED=NO`; `PRODUCTION_CHANGES=NO`; `DEPLOYMENT_GATE=HOLD`.

## 11. Read-only production PID consumers audit

**Operator-observed on ASUS; read-only, no service restart.** Three bounded top-level script directories were scanned for literal `unbound.pid` or `EDGE_UNBOUND_PIDFILE`, excluding symlinks: `/opt/etc/init.d` **10 files, 0 matches**; `/jffs/scripts` **10 files, 1 match** (`services-start`); `/jffs/addons/asus-edge/bin` **26 files, 3 matches** (`services-start` plus two clearly named historical backup copies dated 2026-09-10 and 2026-10-06). **46 files / four matching files overall**, but only two current-path `services-start` copies; identical content/active execution relationship of those two copies has not been established by this scan.

Bounded literal keyword counts: live `S61unbound` had `pidfile=0`, `PIDFILE=0`, `PID_FILE=0`, `pidof=0`; sourced `rc.func` had all three PID-string counts 0, `pidof=6`. This is **not** a complete search of dynamically constructed names, unsearched directories, firmware binaries, cron jobs or open file descriptors.

**Public source-level check:** in the repository `router/scripts/services-start`, function `remove_stale_process_pidfile()` uses a filesystem existence test (`-f`), `pidof` to avoid removing the PID while a matching process exists, and `rm -f` for a stale PID. It **does not read PID file contents**. The direct recovery branch calls it before invoking the daemon. This public source does not independently prove that the router's SHA-pinned live copy is byte-identical with repository HEAD; the live copy's hash must be matched before treating this as exact code provenance. Directory ownership, parent execution rights and firmware/Entware readers remain outside the completed audit.

**Assessment:** the V4.1 change from a fresh daemon PID `0644` to `0600` is reproducible, but *no unprivileged reader requiring that file was found in these bounded locations*. `0600` is a **plausible** configuration, **not yet a production acceptance decision**. Do not introduce a PID chmod workaround or change Unbound's launch mask on ASUS on this evidence. `PID_CONSUMER_BOUNDED_SCAN=PASS_46_FILES`; `NEED_FOR_PID_0644=NOT_ESTABLISHED`; `PRODUCTION_CHANGES=NO`; `DEPLOYMENT_GATE=HOLD`.


## 12. Production services-start source match

Calculated SHA-256 of public `router/scripts/services-start` matches the operator-reported SHA-256 of actual `/jffs/scripts/services-start`: `026b3c18a950abd70ec86046b04c0015832289ec3ec886bcf4d25298aebf5616`. The active startup script is therefore byte-identical to the inspected repo source. Its stale-PID handler uses `-f`, `pidof` and `rm -f`; it does not read the PID content. The separately located add-on copy was not hash-compared. The effective caller UID and other firmware PID readers remain unverified. Production unmodified; deployment HOLD.

## 13. Two services-start copies: already-known split-path drift

**Real-router read-only comparison on 2026-10-24:** `/jffs/scripts/services-start` SHA-256 `026b3c18a950abd70ec86046b04c0015832289ec3ec886bcf4d25298aebf5616`; `/jffs/addons/asus-edge/bin/services-start` SHA-256 `51af014caa8675e3997aa2a6be4df0ab033d80a71b8ca6aeb0f229cf9a0271d4`; `cmp -s` returned **DIFFERENT**. No writes or restarts occurred.

**This divergence predates the current Unbound incident.** The October DNS Guard v3.2 recovery validation explicitly documented the active Merlin hook matching the reviewed source while a separate older add-on copy did not; no overwrite was done. Do not portray this as newly introduced by Unbound R2 or its reboot. The active `/jffs/scripts/services-start` remains SHA-256 identical to the reviewed repo file, but **that establishes no equivalence with the add-on copy**.

**Potential maintenance-path consequence, identified from source:** `scripts/update-tailscale.sh` defines `SERVICES_START=/jffs/addons/asus-edge/bin/services-start` and invokes that path for recovery after a Tailscale package upgrade. `docs/tailscale-maintenance.md` also names the add-on path in manual recovery instructions. Therefore calling the add-on copy simply 'inactive' would overstate the evidence; it is not the primary firmware boot hook, yet it is a **source-defined recovery dependency**. We have not proved the updater was executed or that its live router version is identical to repository source.

**Classification:** `FIRMWARE_BOOT_HOOK_SOURCE_MATCH=PASS`; `ADDON_COPY_DIFFERS=CONFIRMED_EXISTING_DRIFT`; `TAILSCALE_RECOVERY_PATH_REFERENCE=CONFIRMED_IN_REPO_SOURCE`; `ACTUAL_ADDON_RUNTIME_AND_UNBOUND_BEHAVIOR=NOT_VERIFIED`; `PRODUCTION_UMASK_PATCH=NOT_DEPLOYED`; `DEPLOYMENT_GATE=HOLD`. No copying, `chmod`, service restart, or path switch is approved. Compare the two versions' launch semantics off-router or by strictly bounded read-only probes before designing a single-source solution.

## 14. Scoped Unbound functions match in both actual startup copies

**Real ASUS read-only structural comparison, 2026-10-24:** the firmware hook `/jffs/scripts/services-start` and the add-on copy `/jffs/addons/asus-edge/bin/services-start` differ as whole files (SHA-256 `026b3c18...` versus `51af014c...`; sizes 21046 versus 20834 bytes), but both returned `sh -n=PASS`. The operator calculated SHA-256 over the exact AWK-delimited function text and reported identical digests for the two Unbound-related functions:

| Function | Lines in each copy | Function SHA-256 in both copies |
| --- | ---: | --- |
| `remove_stale_process_pidfile()` | 5 | `c20fe27c888d43960324381218671b86d6509519812c5f4600a36574337ae509` |
| `start_unbound_direct_if_stopped()` | 24 | `2126241490fcfd991fb4ea23c79a48f518def5442f28041623c6be599761f0da` |

The selected literal token counts also matched between copies: `unbound.pid=1`, `EDGE_UNBOUND_PIDFILE=2`, `pidof unbound=2`, `unbound-checkconf=2`, `restart_dnsmasq=1`, `umask=0`, `rc.unslung=1`. Active hook UID/GID `1000:1000 0755`; add-on copy UID/GID `0:0 0755`. Audit had `FILES_MODIFIED=NO` and `SERVICES_RESTARTED=NO`.

**Bounded conclusion:** both actual copies have **byte-identical Unbound direct-recovery and stale-PID function bodies** under this extraction method; the original observed split-path drift remains true for the other script bytes. This does not establish identical top-level behavior, shell environment, variable values, call ordering, security ownership or full runtime compatibility. It also does not establish firmware and Entware readers beyond the previously scoped search.

**Separate security boundary (Issue #235, not changed here):** the live firmware hook has owner UID 1000 and mode `0755`, allowing that account to write its content if DAC permits. Root execution of a non-root-writable hook is a distinct trust concern; do not silently `chown`, overwrite, or change either copy during the Unbound umask/RFC5011 investigation. The add-on copy remains a potential Tailscale recovery dependency.

**Status:** `UNBOUND_FUNCTION_CROSS_COPY_MATCH=PASS_TWO_FUNCTION_SHA256`; `FULL_STARTUP_CHAIN_EQUIVALENCE=NOT_PROVEN`; `ACTIVE_HOOK_OWNER_TRUST=SEPARATE_ISSUE235_HOLD`; `PRODUCTION_UMASK_PATCH=NOT_DEPLOYED`; `DEPLOYMENT_GATE=HOLD`.

## 15. BusyBox awk bounded startup-copy comparison

**Operator-run read-only comparison (real ASUS):** BusyBox `awk` compared both current startup files without exposing their contents or changing router state. Active firmware hook: **456** lines; add-on maintenance-path copy: **453** lines. Both share an **identical prefix of 310 lines** and an **identical suffix of 10 lines**. The broad first-to-last differing interval is **active lines 311–446 (136 lines)** versus **add-on lines 311–443 (133 lines)**; `LINE_CONTENT=DIFFERENT`. These are *bounding spans*, **not counts of individually changed lines**.

The corresponding source-matched active file has DNS Guard scheduling around line 311, Entware/AMTM coordination and Tailscale handling in the middle, the two previously hash-matched Unbound functions at lines 391–426, and final service-start orchestration before its identical suffix. No inference can yet be made about the actual changed lines beyond this bound. The two Unbound function SHA-256 matches remain independent PASS evidence.

First proposed `diff -u` command could not execute on the router (`DIFF_TOOL=NOT_AVAILABLE`); it did **not** mean scripts were invalid. The alternate bounded `awk` comparison succeeded. Further analysis should report only exact bounded line-range changes using a **read-only four-consecutive-line resynchronization heuristic**, which must return `HOLD_AMBIGUOUS_ALIGN` when a short safe anchor cannot be found. It is not a full diff or proof of complete semantics.

**Status:** `SCRIPT_PREFIX_MATCH=310`; `SCRIPT_SUFFIX_MATCH=10`; `DIFFERENCE_SPANS_KNOWN=YES`; `EXACT_CHANGE_HUNKS=PENDING`; `PRODUCTION_FILES_MODIFIED=NO`; `SERVICES_RESTARTED=NO`; `DEPLOYMENT_GATE=HOLD`.


## 16. V5 offline source gate: missing rc.func

Operator-run Fedora V5: Python syntax and self-test PASS. The offline inspect verified production-pinned `S61unbound` SHA-256 but returned `V5_RESULT=HOLD_RCFUNC_NO_PINNED_OFFLINE_COPY_IN_FIXED_LOCATIONS`. The exact live `rc.func` SHA-256 required is `5f5730cb58527c74f5da95f0cb37cde68426e25176ca34c34f9e8e3b4fe49f6d`. No `--run` followed because the operator chained commands with `&&`. No actual manager script execution, network access or ASUS changes occurred. Next step is to inspect the existing Fedora verified backup for the correct file. Deployment HOLD.


## 17. Exact upstream rc.func source found, byte identity verified

GitHub source lookup identified `Entware/rtndev`, `entware-opt/files/rc.func`, default branch `master`. The content SHA-256 was independently computed as `5f5730cb58527c74f5da95f0cb37cde68426e25176ca34c34f9e8e3b4fe49f6d`, **identical to the earlier live ASUS read-only rc.func SHA**. This resolves the source provenance blocker without requiring an ASUS connection. A user-controlled HTTPS retrieval onto Fedora with a strict SHA-256 and `sh -n` check is sufficient to present this exact source to V5 (`--rcfunc`); no remote source is ever executed. **The operator has not yet run V5 with the retrieved source; runtime still PENDING.** `ASUS_CONTACTED=NO`; `PRODUCTION_CHANGES=NO`; `DEPLOYMENT_GATE=HOLD`.
