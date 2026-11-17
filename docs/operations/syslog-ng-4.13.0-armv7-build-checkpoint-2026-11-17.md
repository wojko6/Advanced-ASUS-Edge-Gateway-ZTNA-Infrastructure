# syslog-ng 4.13.0 — Fedora collector acceptance and ARMv7 Entware build checkpoint (2026-11-17)

> **Scope and evidence:** this is a sanitized, operator-reported checkpoint from a Fedora 45 workstation and an ASUS TUF-AX5400 (ARMv7, Entware). Terminal results and manifests were supplied by the operator; this repository publication is not an independently executed host/router audit.
>
> **Production boundary:** the Fedora collector is reported updated and boundedly tested with the existing ASUS client. The ASUS still runs **syslog-ng 4.12.0-3**. There is **no** ARMv7 syslog-ng 4.13.0 IPK, no ARM cross-toolchain build, no router-side syslog-ng change, and **no approval to deploy** one.

## Objective

Prepare a compatible, independently testable Entware `syslog-ng 4.13.0-1` package for the existing ARMv7 router without changing the router's current logging path during the build. The 4.13.0 workstream includes the source-side `extended-key-usage-verify(yes)` TLS feature, with peer trust and certificate EKU validation handled separately.

## Fedora collector — bounded live checkpoint

- The upstream `syslog-ng-4.13.0.tar.gz` source archive matched SHA-256 `e82daa3139d1cd790f2d8f2699c70b56a521d8e5218f7e52633dfad1b1f63297`.
- A Fedora 45 x86_64 package `syslog-ng-4.13.0-0.1.fc45.x86_64` was reportedly built and validated with an isolated Mock test before a controlled production installation and configuration backup.
- The collector TLS configuration uses `peer-verify(required-trusted)` and `extended-key-usage-verify(yes)`.
- Operator-reported tests: `S13_F17D2=PASS_ASUS_TO_FEDORA_AFTER_EKU` and `S13_F17E2=PASS_NEW_TLS_MESSAGE_DELIVERED`. These cover a new TLS connection and delivery of a real router-originating test message, not a long-duration reliability/restore test.
- The ASUS syslog-ng client remains on `4.12.0-3`; its TLS credentials, service configuration and running daemon were not changed by the ARMv7 build-lab stages.

## Isolated Entware source provenance

| Component | Pinned version/revision |
| --- | --- |
| Entware build system | `541289a115d32d1ab044e87608bc0ca6b2154ee9` |
| Entware package feed | `f2728214b8a3109e89dcfa188a3cedcf4edf2e57` |
| Candidate recipe | `syslog-ng 4.13.0-1`, isolated feed |
| Target | `armv7-3.2`, soft float, `gnueabi` |
| GNU Binutils | `2.34` |
| Cross GCC | `8.4.0` |
| Target glibc | `2.27` |

The original package feed was kept unchanged. Only the syslog-ng version, package release, and upstream source hash were changed in the isolated recipe. Entware's `500-fix-paths.patch` passed a no-fuzz dry-run against the 4.13.0 source. The package and its feed dependencies were registered in the build tree.

## Operator-reported lab results

| Stage | Outcome and limits |
| --- | --- |
| S13-A2–A9C | Fedora build-host inventory, pinned Entware and package-feed sources, isolated syslog-ng recipe, package index and symlink registration; missing Perl/development prerequisites installed on the build host |
| S13-A10R | `PASS_ENTWARE_PREREQUISITES` after resolving missing `Time::Piece`; no cross-toolchain build |
| S13-A11–A13 | Reduced the preselected package set from 3,054 to a seven-package candidate, then Kconfig resolved it to **28** selected packages; `make defconfig` passed with target ABI and required syslog-ng dependencies preserved |
| S13-A14 | Static build readiness PASS: operator snapshot of 16 CPU threads, about 8.6 GiB available RAM and 335 GiB available storage; planned conservative `-j2` |
| S13-A15–A17 | SHA-256-validated source archives for syslog-ng, Binutils, GCC, glibc, GMP, MPFR and MPC |
| S13-A18 | Read-only inventory: 48 host-tool recipes in static scope, 38 missing archives, seven dynamic/unresolved recipes, no corrupted archive detected; **not** a full Make dependency graph |
| S13-A19 | SHA-256-validated `libdeflate 1.26` and `zstd 1.5.7` sources |
| S13-A20 | `PASS_HOST_BOOTSTRAP`: `flock`, `libdeflate-gzip`, `zstd` built as **x86_64 host utilities** inside Entware staging; not ARM binaries |
| S13-A21/A21R | `make -j2 tools/download V=s` PASS; offline inventory repair PASS after a `comm` locale/sort-order mismatch; source count **9 → 46**, **37 new**, **0 removed**, configuration unchanged |

Known environmental issues were diagnosed rather than bypassed: the Entware prerequisite script needed Fedora Perl modules, and the post-download inventory comparison needed `LC_ALL=C` consistently for both `sort` and `comm`.

The 28-package configuration retains `syslog-ng=m` and the required runtime dependencies, including `glib2`, `ivykis`, `libpcre2`, `libcurl`, `libdbi`, `libjson-c` and `libuuid`. The report indicates `CONFIG_LIBCURL_ZLIB=y` and no selected syslog-ng logrotate option. This **does not yet prove** ABI compatibility of a built binary with the router.

## Explicit hold and next-session entry point

**Last completed stage:** `S13_A21R=PASS_INVENTORY_REPAIRED`.

**Next prepared but NOT EXECUTED:** `S13-A22`, an isolated `make -j2 toolchain/download V=s` on Fedora. Inspect its download log, inventory delta and source hashes before proceeding. A staged command or plan is not a completed result.

Subsequent gates: verify remaining host/toolchain sources; build the ARM cross-toolchain in controlled steps; compile the syslog-ng package; inspect ELF architecture, ABI, dynamic library requirements and TLS support; document backup/rollback; only then consider a separately authorized router maintenance window.

```text
FEDORA_COLLECTOR_4_13=PASS_BOUNDED_OPERATOR
ENTWARE_HOST_BOOTSTRAP=PASS
ENTWARE_TOOLS_DOWNLOAD=PASS
ARM_TOOLCHAIN_BUILT=NO
SYSLOG_NG_4_13_ARMV7_IPK_BUILT=NO
ASUS_SYSLOG_NG_VERSION=4.12.0-3
ASUS_SYSLOG_NG_DEPLOYMENT=HOLD
NEXT_STAGE=S13-A22_NOT_EXECUTED
```

**Security and evidence boundaries:** no private certificate or key content, Tailscale IP, public WAN identifier, raw log stream, local home-directory path or on-router backup location is included. Source publication and operator transcript review do not authorize production changes or demonstrate long-term reliability. The separate [November 17 ASUS worklog](../worklog/2026-11-17.md) covers the Tailscale ARMv7 maintenance; its acceptance gates are independent of this syslog-ng workstream.
