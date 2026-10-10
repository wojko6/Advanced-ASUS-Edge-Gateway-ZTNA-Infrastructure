# Issue #129 — optional BusyBox latest-reboot persistence (2026-10-10)

**Evidence class:** sanitized **operator-reported, read-only live** checks on the existing ASUS TUF-AX5400. This is a follow-up to the dated [2026-10-09 installation and validation](../2026-10-09/custom-busybox-armv7-live-validation.md), not a retroactive change to that earlier report.

## Observed checks

| Check | Result | Meaning |
|---|---|---|
| Explicit JFFS invocation | **PASS** | `/jffs/addons/asus-edge/tools/busybox/1.36.1/busybox` ran and identified itself as 1.36.1 |
| SHA-256 | **PASS** | `08929e6cf52e8ed49ea46f1945ac51193613550099a2bbec24f90b0c1c58763a` matched separately staged artifact |
| Vendor firmware BusyBox | **UNCHANGED** | `/bin/busybox` remained 1.25.1 |
| Boot-before-file timing | **PASS** | Inode change timestamp `stat -c %Z` predates current `/proc/stat` `btime` |
| Reported acceptance gate | **BUSYBOX_REBOOT_PERSISTENCE=PASS** | Optional file existed before the most recent router boot and was executable afterward |

The timing gate indicates **persistence across the latest reboot on the existing router**, in conjunction with the post-boot executable and hash checks. It does not independently establish the exact installation/deployment time beyond those observed timestamps; no second reboot was performed solely for this check.

## Limits and recovery requirements

- This on-demand utility is **not** an automatically started service or a native firmware replacement; global `PATH`, `/bin/sh` and boot DNS behavior remain unchanged.
- The existing CORE `scripts/backup.sh` does **not** include `/jffs/addons/asus-edge/tools/`. A separately verified workstation artifact or rebuild remains necessary after total device loss.
- A clean-device reinstall, optional utility removal/rollback, a full Pi-hole recovery and a blank-router/blank-SSD drill remain **NOT TESTED**. Keep **#129 OPEN**.
- Historical 2026-10-09 documentation correctly called reboot persistence **untested at that time**. Preserve that dated claim; use this document for the later result.

Source: [#129 verified operator follow-up](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129#issuecomment-6094506654).
