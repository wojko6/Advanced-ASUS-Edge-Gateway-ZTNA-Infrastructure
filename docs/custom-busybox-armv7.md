# Optional BusyBox 1.36.1 for ASUS TUF-AX5400 (ARMv7)

**Status (2026-10-10):** separately installed optional BusyBox passed the 2026-10-09 live checksum/applet/healthcheck checks and a **later read-only latest-reboot persistence gate**. This remains an **on-demand operator tool**, not a firmware replacement or new early-boot DNS dependency.

**Reference platform:** ASUS TUF-AX5400; GNUton Asuswrt-Merlin 3004.388.11_1-gnuton1_tuf; ARMv7, Linux 4.1.52. See [dated evidence](../evidence/2026-10-09/custom-busybox-armv7-live-validation.md).

## Rationale and isolation contract

The built-in BusyBox 1.25.1 lacks usable FIND options (notably -type and -perm in this firmware), TIMEOUT, SHA256SUM, SETSID and WHOAMI. A standalone BusyBox 1.36.1 was cross-compiled on Fedora so the project can use these tools explicitly without replacing the firmware shell or firmware-specific applets.

- Firmware binary: /bin/busybox (1.25.1), with /bin/sh symlinked to BusyBox. The firmware root is a **read-only squashfs** mount.
- Optional binary: /jffs/addons/asus-edge/tools/busybox/1.36.1/busybox.
- Never overwrite /bin/busybox, change /bin/sh, globally prepend BusyBox symlinks to PATH, or rewire firmware/NTP/DNS boot hooks for convenience.
- Invoke desired functions with the explicit binary and applet name, for example: /jffs/addons/asus-edge/tools/busybox/1.36.1/busybox find ... .
- The optional binary must not become an early-boot, break-glass, or Entware dependency. DNS Guard's existing native supervisor remains authoritative.
- No automatic upgrades, post-mount hooks, startup links, or full BusyBox replacement are part of this deployment.

The firmware exposes 156 applets and the custom build exposes 402. Two firmware applet names, **bash** and **ntp**, are absent from this upstream build. Matching applet names do not guarantee matching semantics: the ASUS/Merlin firmware contains vendor-specific changes. **Do not use the custom binary as a drop-in substitute.**

## Provenance and artifact metadata

| Field | Operator-observed value |
| --- | --- |
| Upstream source | BusyBox 1.36.1; busybox-1.36.1.tar.bz2 |
| Source archive SHA-256 | b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314 |
| Build host | Fedora x86_64; Podman 5.8.7 |
| Build image/toolchain | Debian bookworm-slim; gcc-arm-linux-gnueabi; ARM EABI5, soft-float cross-toolchain |
| Target executable | 32-bit ARM EABI5, statically linked; ELF minimum GNU/Linux 3.2.0 |
| Binary size | 2,153,552 bytes |
| **Binary SHA-256** | **08929e6cf52e8ed49ea46f1945ac51193613550099a2bbec24f90b0c1c58763a** |
| Initial JFFS free space | 21.1 MiB |
| JFFS after installation | 19.8 MiB available (58% used) |

The private, already-built binary was produced outside this repository. Its file hash identifies that exact artifact; the build method described here is not yet established as **bit-for-bit reproducible**. No ARM binary, private router backup, host-specific SSH identifier or configuration secret is committed to the public repository.

## Build recipe (off-router only)

Build in a Fedora workspace using Podman with Debian bookworm-slim and these tools: build-essential, gcc-arm-linux-gnueabi, libc6-dev-armel-cross, binutils-arm-linux-gnueabi, bc, bzip2, ca-certificates, file and python3.

1. Download BusyBox 1.36.1 from https://busybox.net/downloads/busybox-1.36.1.tar.bz2; verify the **source SHA-256 above** before extracting.
2. Extract and run make defconfig with ARCH=arm and CROSS_COMPILE=arm-linux-gnueabi-.
3. Enable the following exact Kconfig symbols and verify they remain enabled after make oldconfig: STATIC, FIND, FEATURE_FIND_TYPE, FEATURE_FIND_PERM, FEATURE_FIND_MAXDEPTH, FEATURE_FIND_PRINT0, FEATURE_FIND_LINKS, FLOCK, TIMEOUT, SHA256SUM, FEATURE_MD5_SHA1_SUM_CHECK, WHOAMI, SETSID, NSLOOKUP (all with CONFIG_ prefix, value y).
4. Run make -j2. Fail the build on nonzero exit and retain the build/config logs.
5. Verify file and readelf: ARM EABI5, **statically linked**, no ELF INTERP segment. Run with qemu-arm-static and verify selected applets, FIND -type/-perm/-maxdepth, SHA-256 parity and bounded TIMEOUT behavior.
6. Before installation, run the binary from a private /tmp staging directory on the target router: compare SHA-256 and size, test execution and clean up. A successful QEMU build alone is not target-runtime acceptance.

The current binary was reported to pass the Fedora/QEMU tests and isolated live /tmp tests on 2026-10-09. Source checksum, artifact checksum, architecture and enabled configuration options remain part of every future rebuild review.

## Safe deployment boundary

The 2026-10-09 installation used a root-owned private /tmp staging directory, checked received bytes and SHA-256, then verified the staged candidate copied onto JFFS. A same-filesystem directory rename published the **versioned** directory; the previous firmware BusyBox was not touched. New files were created under umask 077, with executable mode 0700. The published artifact was rehashed and tested, then the temporary copy was removed.

For a repeat deployment **do not run an unreviewed blind installer**. First prove backup/recovery readiness, sufficient JFFS reserve, no symlink/path conflicts and the expected artifact hash. Do not replace an existing versioned directory. Keep at least 10 MiB free after deployment. Capture pre/post hash of /bin/busybox and project healthcheck. If a step fails, stop and inspect before any cleanup of unexpected objects.

### Read-only verification

Run in an authenticated administrator shell on the router:

~~~sh
BB=/jffs/addons/asus-edge/tools/busybox/1.36.1/busybox
EXPECTED=08929e6cf52e8ed49ea46f1945ac51193613550099a2bbec24f90b0c1c58763a

test -f "$BB" && test ! -L "$BB" || exit 1
ACTUAL=$(/opt/bin/sha256sum "$BB" | awk '{print $1}')
test "$ACTUAL" = "$EXPECTED" || exit 1
"$BB" --help | sed -n '1p'
"$BB" find /jffs/addons/asus-edge/backup -type l >/dev/null
"$BB" find /jffs/addons/asus-edge/backup -perm -0002 >/dev/null
"$BB" timeout 3 /bin/sleep 1
/jffs/addons/asus-edge/bin/healthcheck.sh
~~~

These commands are diagnostic only; FIND matches are intentionally not printed. A healthcheck PASS is not a substitute for service recovery after a wiped router.

## Rollback (documented, **not live-exercised**)

1. Confirm that no installed hooks, cron entries, running scripts or manually configured callers depend on the versioned binary. Existing reference operation does **not** point system PATH, shell or startup hooks to it.
2. Independently verify the path has no symlinks, the exact artifact hash matches, and a usable off-router copy remains available.
3. In a separately authorized maintenance step, remove **only** the exact known version file; remove its version directory only if empty. Leave /bin/busybox, /bin/sh, all other versions and any unrelated tools untouched. Never apply recursive deletion to the parent tools tree.
4. Re-run project healthcheck and, if needed, check callers. A failed hash/path test must **STOP**, not delete unknown content.

Example of pre-removal inspection (**read-only**):

~~~sh
BB=/jffs/addons/asus-edge/tools/busybox/1.36.1/busybox
test -f "$BB" && test ! -L "$BB" || exit 1
ls -ldn /jffs/addons/asus-edge/tools /jffs/addons/asus-edge/tools/busybox /jffs/addons/asus-edge/tools/busybox/1.36.1 "$BB"
 /opt/bin/sha256sum "$BB"
~~~

Rollback is straightforward in design because the binary has no automatic consumers, but **removal/restore was not executed** in this acceptance. Do not mark rollback PASS until an isolated exercise is recorded.

## Disaster recovery and persistence

The existing project CORE scripts/backup.sh copies the addon bin/ and legacy/ trees, **not** tools/. Therefore the versioned BusyBox executable is **not** included in the existing CORE backup or its SHA256SUMS manifest. No source-level change to the production backup script was made by this documentation.

During a clean-device rebuild:
1. Restore the stock GNUton/Merlin firmware and preserve its original BusyBox.
2. Rebuild CORE DNS/Entware/swap and access using the current [router recovery contract](router-disaster-recovery.md) and [Pi-hole runbook](pihole-dr-rebuild-runbook.md); the optional BusyBox is **not** a prerequisite.
3. Obtain the validated ARM binary from the **separately retained trusted off-router artifact** (or rebuild from reviewed source and toolchain), verify the exact ELF/size/SHA-256 and use an isolated staging/install flow to publish the versioned location.
4. Run the read-only verification above and record JFFS capacity, healthcheck, and any actual reboot persistence result.

A complete empty-router/empty-SSD rebuild and optional-tool removal/rollback remain **NOT TESTED**. A separate [2026-10-10 operator-reported read-only check](../evidence/2026-10-10/issue-129-custom-busybox-reboot-persistence.md) established the versioned binary's **latest-reboot persistence PASS** on the existing reference router, not on a cleanly rebuilt target. Keep #129 open.

## Tested scope and open boundaries

**Operator-reported PASS (2026-10-09):** source SHA-256; ARM static build and QEMU tests; /tmp binary transfer and live hash/selected applets; versioned JFFS install and exact hash; original /bin/busybox unchanged; four issue #200 protected trees reporting zero symlinks/world-writable objects when audited using the custom FIND; full project healthcheck 0 failures and 0 warnings.

**Not proven:** all 402 applets under ASUS firmware; applet-semantic equivalence with vendor BusyBox; production rollout/rollback of new PATH links; optional-tool **removal/rollback**; exact clean-device reconstruction; or bit-for-bit reproducibility across new toolchain images. The separate 2026-10-10 latest-reboot persistence check is PASS on this existing device only.

**2026-10-09 follow-up:** issue #200 was **closed** for the scoped 698-object JFFS permissions audit and PR #209 isolated regressions; see [final #200 evidence](../evidence/2026-10-09/issue-200-final-permissions-acceptance.md). **2026-10-10 follow-up:** latest-reboot persistence of this optional binary passed a separate read-only gate; **removal/rollback is still untested**. See [dated evidence](../evidence/2026-10-10/issue-129-custom-busybox-reboot-persistence.md).

Related: [#200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200) and [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129). Issue #200 is **CLOSED** within its original permissions scope; issue #129 remains **OPEN** pending full Pi-hole-aware disaster recovery.
