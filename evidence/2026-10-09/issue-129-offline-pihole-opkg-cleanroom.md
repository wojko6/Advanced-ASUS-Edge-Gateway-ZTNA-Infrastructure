# Issue #129 — Offline Pi-hole / Entware reconstruction on Fedora (clean-room evidence)

**Date:** 2026-10-09  
**Target baseline:** ASUS TUF-AX5400, GNUton Asuswrt-Merlin `3004.388.11_1-gnuton1_tuf`; Entware `armv7-3.2`.  
**Scope:** operator-reported Fedora / rootless Podman / ARMv7 QEMU tests; the production router was queried read-only and **not** used as a restore target.  
**Result:** **PASS** for package provenance, recursive declared dependency closure, offline `opkg` installation and database validation in an isolated disposable target. **NOT a blank-router rebuild acceptance.**

## Private archive and service prerequisites

Three **separately encrypted, off-router** recovery items were checksum-verified: project CORE, dedicated Pi-hole DR and native ASUS settings CFG. No encrypted archives, plaintext configurations, tokens, password/API values, IPKs or raw operator logs are committed here.

- A disposable Fedora `tmpfs` CORE rehearsal passed decryption, dry-run, allowlisted restore and syntax checks: **39 restored files**, AMTM-owned `post-mount` protected. An earlier 41-entry CORE stream/manifest inspection was a different test; **41 is not the count of restored files**.
- A private Pi-hole DR archive passed integrity/manifest inspection and Gravity SQLite integrity checks. A separate clean-room Pi-hole state restore validated **19 staged files**, **18 file hashes**, modes and hook syntax; UID/GID and xattrs were **not** re-applied in that test.
- One controlled reference-router restart passed with Entware available, DNS Guard convergence and healthcheck **0 failures / 0 warnings**; that boot is documented [separately](issue-129-pihole-dr-reboot-persistence.md) and does not prove disaster recovery on blank storage.

## Live read-only package provenance

The router reported `pi-hole 2026.09.20-1` (`armv7-3.2`), while the active `/opt/bin/pihole-FTL` had SHA-256:

```text
63e64dccdd74f82d5be048f4beef41200cf10a647cc097af77a624835954060b
```

The Pi-hole package source was `https://jacklul.github.io/entware-pi-hole/armv7sf-k3.2/`; the general Entware feed was `https://bin.entware.net/armv7sf-k3.2/`. A locally installed Pi-hole package does **not** imply its installer is cached in `opkg` storage. The index-record check on the router did not find the package, but the **fresh remote** feed index subsequently supplied an exact record with SHA-256 and size.

A Fedora copy of `pi-hole_2026.09.20-1_armv7-3.2.ipk` was independently checked against the downloaded feed index: **15,265,919 bytes**, correct SHA-256 and valid `control.tar`/`data.tar` structure. The package payload contained **211 ordinary files** and its FTL binary hash matched the running router binary. `control` declared **37 direct dependencies** and three maintainer scripts: `preinst`, `postinst`, `prerm`.

The independent custom **Unbound 1.26.1** IPK set (five verified installed packages) and **Tailscale 1.103.375** runtime artifact were also located off-router. These are **separate recovery artifacts**; they are not counted among the 65 Pi-hole closure packages. Router `opkg` metadata for Tailscale reported an older version than the active binary; runtime identity must be checked separately.

## Recursive offline dependency construction

The operator downloaded and verified exact router-matching package versions using SHA-256 published in the HTTPS feed indexes:

| Phase | Verified IPKs | Reported verdict |
|---|---:|---|
| Pi-hole itself | 1 | SHA-256, package structure and FTL hash PASS |
| Declared direct Pi-hole dependencies | 37 | 37/37 downloaded, SHA-256 PASS |
| First transitive level | 20 | 20/20 SHA-256 PASS |
| Second transitive level | 7 | 7/7 SHA-256 PASS |
| **Total** | **65** | **65/65 SHA-256 PASS** |

A first transitive download attempt stopped after ten packages because the operator script's filename allowlist omitted the valid Entware version character `~` (notably `libnl-tiny`). The corrected script reused the ten verified files and downloaded the remaining ten; no router changes were made.

Four private SHA-256 manifests covered exactly **1 + 37 + 20 + 7 = 65** distinct `.ipk` files. The final metadata inspection reported:

```text
LOCAL_PACKAGES=65
SHA256_VERIFIED=65/65
DEPENDENCY_GROUPS_CHECKED=340
ADDITIONAL_PACKAGES_NEEDED=0
UNRESOLVED_GROUPS=0
VIRTUAL_GROUPS_TO_REVIEW=0
VERSION_CONSTRAINTS_TO_VALIDATE=0
ROUTER_VERSION_MISMATCHES=0
OFFLINE_METADATA_CLOSURE=PASS
```

**Interpretation:** all **declared package-name dependencies** encountered in this selected package set were resolvable locally, with matching versions and no discovered version constraints/virtual ambiguity. This is not a proof that package scripts will avoid additional dynamic downloads or that every required addon for the full router is covered.

## Package archive and maintainer-script review

A no-execution archive inspection of all 65 IPKs reported:

```text
PAYLOAD_REGULAR_FILES=450
PAYLOAD_SYMLINKS=227
PAYLOAD_HARDLINKS=0
FILESYSTEM_COLLISIONS=0
UNSAFE_ARCHIVE_PATHS=0
ABSOLUTE_SYMLINKS_TO_REVIEW=1
ESCAPING_SYMLINKS_TO_REVIEW=0
MAINTAINER_SCRIPTS=4
```

The sole absolute link was `/opt/etc/ssl/cert.pem -> /opt/etc/ssl/certs/ca-certificates.crt`, inside the normal target Entware layout. An absolute symlink inside an offline target must be treated carefully: dereferencing it from a **host** can resolve against the host's `/opt`, not the staged `/stage/opt`. Avoid accessing staged absolute links from the Fedora host.

The four scripts were Pi-hole `preinst`, `postinst`, `prerm` and `terminfo postinst`. Static review found:
- Pi-hole `preinst` can invoke `opkg install` for missing runtime utilities.
- Pi-hole `postinst` can create / modify `/opt/etc` configuration, cron and logrotate state, call Gravity scripts, configure FTL interface and API password, manage FTL service start/restart, run a custom `postinstall.sh` and spawn an update check. Execution is conditional; **static pattern matches are not evidence those operations ran**.
- Pi-hole `prerm` can stop FTL and record a restart marker.
- `terminfo postinst` appends `export TERMINFO=/opt/share/terminfo` to `/opt/etc/profile` if absent.

**Recovery control:** do not directly execute these maintainer scripts on the Fedora host or healthy router. On a real rebuilt router, review their actions, preserve backed-up Pi-hole policy/configuration, restrict outbound network access as appropriate and enforce DNS/startup gates before deciding how to apply required install-time actions.

## Clean-room payload and actual `opkg` tests

1. **Payload-only test:** 65 verified IPKs were streamed into a disposable Fedora `$XDG_RUNTIME_DIR` `tmpfs` tree. The test staged **450 regular files** (70,843,977 bytes), verified their hashes and the FTL binary, recorded **227 symlinks without creating them**, then destroyed the workspace. `ISSUE129_IPK_TMPFS_RESTORE=PASS`. No maintainer scripts, UID/GID, capabilities, `opkg` or service startup were exercised here.
2. **ARMv7 runtime:** the existing local `localhost/issue129-unbound-lab:1` image started through rootless Podman and reported `ARCH=armv7l`; the Fedora host remained x86_64. Podman `ROOTLESS=true`; QEMU ARM support available.
3. **`opkg` provenance:** the Entware `armv7sf-k3.2/installer/opkg` client is a statically linked ARM ELF (SHA-256 `82d693e3c928def1cbf584a1130f37fd51bcb3338e57d4af327e342a5f19ee3a`). It ran in the ARMv7 container as `opkg version d038e5b6d155784575f62a66a8bb7e874173e92e (2022-02-24)`. This binary rejects `--help` with exit code 1 but its usage output confirms `--offline-root`, `--noaction` and `--force-postinstall`.
4. **Planning check:** rootless ARMv7 Podman, `--network=none`, read-only base image, separate `tmpfs` mounts and read-only IPK mount; `opkg -f /lab/opkg.conf --offline-root /stage --noaction install /packages/*.ipk` returned `OPKG_OFFLINE_DRYRUN=PASS`.
5. **Actual installation:** a fresh disposable ARMv7 container used `--network=none`, a read-only base image, `tmpfs` for `/stage`, `/opt`, `/tmp`, read-only bind mounts for the verified `opkg` binary/config and 65 IPKs, and `--offline-root /stage` **without** `--force-postinstall` or `--noaction`. `opkg` exited **0**, staged `/stage/opt/bin/pihole-FTL` with the expected SHA-256, and created `/stage/opt/lib/opkg/status` containing **65 `Package:` records**, all reporting `Status: install user installed`.

Operator-reported final checkpoint:

```text
EXIT_CODE=0
OPKG_INSTALL_COMMAND=PASS
FTL_STAGED=PASS
FTL_SHA256=PASS
STATUS_DATABASE=/stage/opt/lib/opkg/status
PACKAGE_RECORDS=65
65 Status: install user installed
CERT_SYMLINK_STAGED=YES
CERT_SYMLINK_TARGET=/opt/etc/ssl/certs/ca-certificates.crt
ISSUE129_OPKG_CLEANROOM_INSTALL=PASS
CONTAINER_NETWORK=DISABLED
TEMPORARY_FILESYSTEM=DESTROYED_ON_EXIT
PRODUCTION_ROUTER_UNCHANGED=YES
```

`Configuring ...` lines in the `opkg` log and package status **do not on their own prove maintainer scripts executed**. `--force-postinstall` was not specified; no side-effect audit of deferred maintainer scripts was performed. **No DNS, FTL runtime, or real-router service acceptance was exercised in this container.** This exercise verifies package registration and installed payload in the isolated target, not the whole ASUS/Entware startup stack.

## Remaining gates — issue #129 remains OPEN

- On a **disposable rebuilt target**, confirm account/group `pihole` **999:999**, exact file ownership and permissions, and required `pihole-FTL` capabilities (seven-capability set documented in the private manifest) after recovery; the `tar` backup does not carry `security.capability`.
- Reconcile `preinst`, `postinst` and `terminfo postinst` side effects without running router-specific operations on Fedora or overwriting recovered private Pi-hole configuration / API credentials.
- Recreate the actual firmware, JFFS, disk labels/mounts, two swap files and verified **swap-before-Entware** startup order; preserve AMTM ownership of `post-mount` and independent WAN DNS for NTP bootstrap.
- Integrate custom Unbound, `S61unbound`, the `S64pihole-ip` alias before `S65pihole-FTL`, DNS Guard, dnsmasq DHCP/local PTR policy, Tailscale fresh enrollment, syslog-ng and firewall.
- Exercise actual restored-target Gravity integrity/filtering, DNSSEC positive/negative, UDP/TCP forwarding, DHCP DNS, reverse DNS, watchdog, API/collector and healthcheck; separately test post-recovery reboot.
- Full factory/blank-storage router restore and native CFG import are **NOT TESTED**. Do **not** close #129 or claim measured RTO/RPO from these package-only tests.

Private operator logs (not committed) included `issue129-opkg-dryrun.log` and `issue129-opkg-install.log`. Public evidence is intentionally limited to sanitized outputs and validation boundaries.

## References

- [Issue #129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)
- [Pi-hole-aware reconstruction runbook](../../docs/pihole-dr-rebuild-runbook.md)
- [Blank-router field guide (Polish)](../../docs/router-bare-metal-recovery-pl.md)
- [Router DR baseline](../../docs/router-disaster-recovery.md)
- [Controlled reboot persistence evidence](issue-129-pihole-dr-reboot-persistence.md)
