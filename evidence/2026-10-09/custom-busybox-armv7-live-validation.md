# Optional BusyBox ARMv7 — sanitized live validation (2026-10-09)

**Source:** operator-provided terminal output, **not** an independently captured router session or automated CI result.

**Platform:** ASUS TUF-AX5400, GNUton firmware 388.11 / Linux 4.1.52 / armv7l. Fedora x86_64 build host, Podman, qemu-arm-static.

## Artifact
- Source: BusyBox 1.36.1; source tarball SHA-256 `b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314`.
- Cross compiler: `arm-linux-gnueabi-gcc`; ELF ARM EABI5, 32-bit, static, declared GNU/Linux 3.2.0 minimum.
- Size: 2,153,552 bytes.
- Binary SHA-256: `08929e6cf52e8ed49ea46f1945ac51193613550099a2bbec24f90b0c1c58763a`.
- Versioned JFFS installation: `/jffs/addons/asus-edge/tools/busybox/1.36.1/busybox`.
- System binary remains firmware BusyBox 1.25.1; root mount confirmed `squashfs ro` and `/bin/sh -> busybox`.

## Accepted observed checkpoints

| Gate | Reported result |
| --- | --- |
| Source archive SHA-256 | PASS |
| ARM static build + config verification | PASS |
| QEMU applet / FIND / TIMEOUT / hash tests | PASS |
| One-time isolated /tmp execution and cleanup | PASS |
| Separate staging transfer, SHA-256, FIND and TIMEOUT | PASS |
| JFFS preflight, >=10 MiB planned reserve | PASS |
| Versioned JFFS publication and post-install checksum | PASS |
| Firmware /bin/busybox hash unchanged | PASS |
| Global PATH and firmware shell unchanged | PASS |
| Temporary staging cleanup | PASS |
| JFFS remaining | 19.8 MiB (58% used) |
| Project healthcheck | 0 failures, 0 warnings |

## Issue #200 follow-up

Using the newly available FIND -type and FIND -perm on the live router:
- root-owned backup/, backups/, legacy/ and rollback/ top-level directories: all mode 0700;
- reported symlink count **0** and world-writable object count **0** inside each of the four trees;
- after auditing, project healthcheck **0 failures, 0 warnings**.

**At this earlier tool-validation checkpoint**, this four-tree scan did **not** yet establish per-path ownership, write-path compatibility or #200 closure. Later on 2026-10-09, a separate 698-entry read-only metadata audit and merged PR #209 isolated installer/restore tests supported **closing #200** for its world-writable permission scope. The #200 closure does **not** prove a production emergency rollback. See [later final #200 evidence](issue-200-final-permissions-acceptance.md).

## Boundaries and gaps

- Original applet list: 156; custom applet list: 402; **bash** and **ntp** names present in original but missing from custom. No assurance of compatible semantics.
- Persistence across a fresh reboot **after this optional tool installation** has not been shown.
- The project CORE archive excludes tools/: rebuilding from a verified, separately retained workstation artifact remains necessary.
- Production rollback/removal has **not** been exercised; full blank-device/blank-SSD DR #129 remains open.
- Only sanitized outcomes are recorded: no router address, user identifier, private service settings, keys or archive contents.

See [custom BusyBox operator/build contract](../../docs/custom-busybox-armv7.md), [#200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200) and [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129).
