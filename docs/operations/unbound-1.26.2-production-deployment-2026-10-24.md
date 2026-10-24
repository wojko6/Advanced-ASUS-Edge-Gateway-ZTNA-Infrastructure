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
