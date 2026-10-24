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
