# Fedora Recovery — 2026-10-19 operator checkpoint

> **Scope:** Fedora 44 observability/workstation host only; supplemental resilience milestone for the separate **service-scoped automatic update** design. **Evidence:** operator-pasted Fedora terminal outputs from local scripts V10–V20B; no independently rerun commands, CI acceptance or restored OS boot. **Current action:** preserve the tested baseline, refresh it when materially needed, and **return to service updates**. `AUTO_INSTALL_GATE=HOLD`.

## Why this exists

The update project is meant to update **allowlisted off-router services**, not perform unattended Fedora system/kernel/NVIDIA upgrades. After investigating safe recovery prerequisites, the operator prepared a local Btrfs root snapshot and an independently stored, encrypted recovery copy on a second physical NVMe in the **same computer**. This is meaningful disk-level redundancy, not off-site backup or a full disaster-recovery guarantee.

The output does **not** replace RouterCloud's own Restic schedules, its application data retention, service-specific consistent database exports, or backups of the separately mounted home volume.

## Verified phases and evidence class

| Phase | Result received from operator | What is and is not established |
| --- | --- | --- |
| Baseline layout | Btrfs root/home separate, nested `systemd-machines`; boot ext4 and EFI vfat; UEFI/Secure Boot active and SELinux Enforcing | Static/storage discovery only |
| Root boot state | Current/default kernel files and matching BLS/GRUB entries checked with adequate privileges; NVIDIA runtime usable | No change of default kernel; alternate-kernel stability not proven |
| V10 | Read-only Btrfs root + nested-machines snapshot; boot/EFI archives and checksums created | No system rollback performed |
| V11–V13 | Snapshot properties/metadata, archive hashes and boot identity checked; representative boot files restored and byte-compared in isolation | Sample restore only, not boot test |
| V14–V16 | Storage topology profiled; independent target NVMe/ext4 validated | Not off-site protection |
| V17A–V17B | Overstrict initial target-owner preflight resolved; separate encrypted Restic repository initialized and checked; ephemeral password file removed | The user-owned target parent can still delete or rename the child; encryption alone does not defend against deletion |
| V18 | Root and machines Btrfs send streams, plus boot/EFI bundle stored as three Restic components | Metadata check, not yet full data read |
| V19 | `restic check --read-data`, Btrfs stream structural validation and boot/EFI checksums PASS | Stream validation is not `btrfs receive` |
| V20A–V20B | Resource sizing and **actual isolated Btrfs receive** of both streams in a disposable loop-backed filesystem PASS; restored identity/read-only metadata and sample content PASS; temporary device/image removed | No running-system modifications; no Live USB boot or live restoration |
| V21 | Offline recovery runbook drafted for operator | Live USB test V21A and full restored-system boot **NOT TESTED** |

**Provenance:** all PASS markers above are operator-supplied test results. They are not an assertion that the assistant had shell access to Fedora or that GitHub CI independently verified the recovery scripts.

## Safety and trust boundaries

- The separately mounted `/home` is not included in a root snapshot; nested Btrfs volumes must be treated separately during recovery.
- Restoring a filesystem snapshot taken while databases are active is **not** a tested application-consistent Grafana, Loki or VictoriaMetrics restore. Service-specific backups and validation remain required.
- Independent physical SSD protection is not a defense against whole-device loss, theft, power events or complete host compromise. Keep the Restic passphrase in a secure password manager accessible after host failure; **no passphrase or secret-derived data belongs in Git**.
- Separate boot/EFI files and Secure Boot/SELinux policy require careful offline procedure. A successful `btrfs receive` is not equivalent to a bootable restored system.
- This checkpoint includes **no** ASUS/JFFS/Entware/SSD permission action, RouterCloud wrapper change, service restart, unattended DNF transaction, kernel or NVIDIA change.

## Operational disposition (2026-10-19)

**Recovery baseline: retained.** It can be refreshed after material system or configuration updates, with new operator checks and a new independent copy; historical snapshots remain dated evidence rather than silently being reclassified as current. Operator deferred Live USB validation and further recovery development.

**Service update project: still pending.** Existing `homelab-update-check.timer` is check-only. Introduce any future installation path only with reviewed per-package allowlist, version/vendor/solver checks, coherent backups, lock coordination with existing user backup services, service-specific health checks, independent notification and explicit authorization.

`AUTO_INSTALL_GATE=HOLD`; no automatic host-wide `dnf upgrade` and no automatic kernel/NVIDIA updates.

## Links

- [Fedora Homelab controlled-update runbook](fedora-homelab-automatic-updates.md)
- [October 19 engineering worklog](../worklog/2026-10-19.md)
- [October 18 service-update evidence](../../evidence/2026-10-18/fedora-update-operator-validation.md)
- [Public/private worklog publication policy](../audits/2026-10-18-public-worklog-coverage-audit.md)
