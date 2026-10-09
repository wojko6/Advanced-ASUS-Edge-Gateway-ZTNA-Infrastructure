# Router disaster-recovery baseline

**Tracking:** #100 (historical), #129 (Pi-hole recovery)

**Status (2026-10-09):** verified private recovery archives and disposable restore components; **production reboot persistence PASS** with Entware present; full end-to-end router rebuild pending

## Goal

Create a practical, testable recovery path for the current ASUS TUF-AX5400 reference deployment without turning the backup into an unauditable full-filesystem image.

A successful archive is not considered proof of recoverability. The recovery claim requires a documented coverage model, integrity checks, a safe restore procedure and at least one non-destructive or disposable-target restore validation.

## Current design direction

Keep the existing project-native backup/restore workflow as the primary mechanism and extend it deliberately. Use BACKUPMON as a coverage/reference comparator rather than installing it on the reference router by default.

Reasons:

- the project already has checksum manifests, archive path/type validation, dry-run restore and rollback-on-copy-failure behavior;
- the live environment contains project-owned and addon-owned state that should not be copied indiscriminately;
- BACKUPMON targets broad JFFS/NVRAM/USB restoration and scheduled operation, which is useful as a reference but expands write/update ownership;
- the current project requires one material router change at a time and review before third-party installation.

This decision can be revisited if a required recovery gap cannot be covered safely by the project-native workflow.

## Reference-state inventory findings

The original clean-room DR inventory was captured on 2026-09-27. The
reference deployment then changed materially on 2026-09-28 when the main LAN
migrated from Diversion/uiDivStats to Pi-hole.

Current reference facts are:

- reference router: ASUS TUF-AX5400;
- reference firmware: GNUton / Asuswrt-Merlin 3004.388.11_1-gnuton1_tuf;
- JFFS is read/write;
- separate ENTWARE and ROUTER_DATA ext4 filesystems are active;
- two swap files are active;
- Tailscale, Pi-hole FTL, Unbound and syslog-ng are part of the active reference stack;
- Unbound listens on 127.0.0.1:53535 over TCP and UDP;
- Pi-hole owns the dedicated main-LAN DNS alias while firmware dnsmasq retains DHCP/local naming and the existing classic-DNS interception endpoint;
- the live post-mount hook contains the validated pre-Entware swap activation required by the current startup path;
- AMTM and Unbound Manager remain addon-owned integration points;
- Diversion and uiDivStats were removed from the active reference stack after the Pi-hole cutover.

The **2026-09-27 DR validation predates Pi-hole adoption**. It remains valid for
the archive/restore mechanics and the components it tested, but it is not by
itself proof of complete recovery of the current Pi-hole layer.

No raw private Tailscale identifiers, authentication state or credential values are published in this document.

## Recovery coverage matrix

| Recovery item | Current method | Status | Recovery rule |
|---|---|---|---|
| `/jffs/configs/asus-edge.conf` | project archive | covered | restore from verified archive |
| `/jffs/configs/dnsmasq.conf.add` | project archive | covered | restore from verified archive, then validate dnsmasq |
| project `firewall-start` | project archive | covered | restore, then validate syntax and firewall health |
| project `services-start` | project archive | covered | restore, then validate startup dependencies |
| project `wan-event` | project archive | covered | restore, then validate WAN/DNS recovery path |
| `dnsmasq.postconf` | project archive | covered | restore only after ownership/conflict review |
| reference `post-mount` swap-order fix | project archive, review-only reference | **added by #100 branch** | never auto-apply; compare with the rebuilt AMTM hook and manually preserve the validated pre-Entware swap ordering |
| project addon binaries / preserved legacy hooks | project archive | covered | restore only as project-owned state |
| optional custom BusyBox 1.36.1 ARMv7 under /jffs/addons/asus-edge/tools/ | **not** in CORE project archive | live optional tool PASS; clean-device reinstallation and post-install reboot untested | separately retain a hash-verified off-router ARM artifact or rebuild from reviewed source; restore only after CORE services work; do not replace /bin/busybox |
| Unbound standard config | project archive | covered where present | do not overwrite manager-generated runtime config blindly |
| Unbound Manager runtime config | project archive | file covered | runtime directory ownership still requires explicit validation |
| Unbound Manager hook | project archive | `unbound.postconf` covered | manager scripts themselves are addon-owned and should be reinstalled/revalidated |
| syslog-ng main config | project archive | covered | credentials/certificates remain separately controlled |
| NVRAM | native ASUS/Merlin settings export | encrypted private CFG integrity verified; import untested | maintain model/firmware compatibility; do not publish raw values or assume that a verified export has been restored |
| Tailscale state/auth | intentionally excluded | recreate | re-enroll/re-authenticate after recovery; do not restore stale node secrets from the project archive |
| Tailscale package/runtime provenance | rebuild manifest | gap | package metadata alone is insufficient on the current reference state |
| Entware package inventory | rebuild manifest | gap | capture versions for reconstruction; packages are reinstalled rather than copied blindly |
| AMTM modules | reinstall/revalidate | addon-owned | restore integration points, then reinstall/validate AMTM-managed components |
| Pi-hole / FTL package and service state | dedicated private Pi-hole DR archive plus package manifest | archive and isolated FTL checks PASS; complete target reinstall untested | reinstall the reviewed Entware Pi-hole stack, reconstruct account/capabilities and revalidate listener/startup ownership |
| Pi-hole filtering configuration / Gravity inputs | allowlisted private archive with Gravity SQLite integrity verification | backup PASS; restored-target filtering acceptance untested | restore only reviewed policy input/data from verified archive; verify Gravity SQLite and validate blocking on the target |
| Pi-hole query-history database | private operational data | intentionally not a public/project backup payload | analytics/history continuity is not required for gateway recovery; keep any private backup under a separate data/privacy policy |
| Pi-hole dedicated LAN alias/startup integration | backed-up integration scripts, manual target reconstruction | current-router reboot PASS; clean rebuild untested | recreate the alias before FTL starts and verify no port-53 conflict with firmware dnsmasq |
| Diversion / uiDivStats | historical only | removed from active reference stack | reinstall only for an intentional rollback to the pre-2026-09-28 historical design, not as part of current recovery |
| storage labels/layout | rebuild manifest | gap | record filesystem labels, mount roles and swap topology; do not depend on a full USB image |
| swap files | recreate | intentionally not backed up | recreate on the intended storage and validate before Tailscale recovery |
| `root.key` | regenerate/manager-owned | intentionally not primary payload | restore writable runtime ownership and let the resolver/manager maintain trust-anchor state |
| router-attached user data | outside project DR | out of scope | use a separate data-backup policy |

## Important live-state risks

### Post-mount ownership boundary

The reference router currently activates the mounted swap file before sourcing AMTM's `mount-entware.mod`. That ordering fixed the boot weakness observed in #66.

The hook is partly addon-managed, so restore must not silently assume that an old post-mount file is compatible with a newly installed AMTM version.

The backup stores the hook below `recovery-reference/`, outside the automatically applied `jffs/` and `opt/` trees. In addition, `restore.sh` explicitly skips `jffs/scripts/post-mount` if an older archive contains it at the live path.

Restore procedure:

1. dry-run and inspect the archived review copy;
2. establish/reinstall the intended AMTM baseline;
3. compare the rebuilt live hook with the archived reference;
4. manually merge/preserve the validated pre-Entware swap ordering;
5. run `sh -n`;
6. reboot only in a controlled maintenance window;
7. verify swap-before-Entware evidence and project health.

### Unbound runtime ownership

The live reference `/opt/var/lib/unbound` directory is owned by the resolver runtime account rather than root. File-content backup alone does not prove that a clean restore recreates this ownership correctly.

The project must not claim full resolver recovery until a safe restore test proves the required owner/mode contract or the restore procedure recreates it explicitly.

### 2026-10-08 issue #200 directory-mode checkpoint

A separate operator-provided manifest comparison for `/jffs/addons/asus-edge`
covered 698 entries, found 76 differences during preflight (59 directories
and 17 files in the planned correction), and later reported zero remaining
differences plus a clean project healthcheck. This is a **local equality and
health checkpoint only**: neither a complete per-path least-privilege review
nor a successful current-state backup/restore drill was supplied. The modes
for `backup/`, `backups/`, `legacy/` and `rollback/` must be reviewed
against actual writers and rollback consumers. Avoid blanket recursive
permission changes; ensure off-router backups, owner/group/mode evidence,
write-path tests and bounded rollback before [#200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200)
is accepted. This does not close [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)
Pi-hole-aware disaster recovery or establish measured RTO/RPO.

### 2026-10-09 — #200 closed permission-hardening acceptance

Later 2026-10-09 evidence supersedes the **open-issue status**, not the historical
2026-10-08 facts above. [Issue #200](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/200)
was **closed as completed** for the original four world-writable addon trees
after a read-only, checksum-pinned 698-entry inventory (72 `backup/`,
544 `backups/`, 3 `legacy/`, 79 `rollback/`). Each top-level
directory is root:root 0700; 697 objects were root:root and a single retained
`backups/pihole-session-before-7d.toml` was UID:GID 999:999, mode 0640,
under root-only 0700 `backups/`. There were **zero** group/world-writable
objects, symlinks or invalid records.

Live managed hook guards were confirmed, with two `EDGE_RUN_LEGACY_HOOKS=0`
assignments and no enabled assignment. The sole filename had zero exact
matches in the bounded active-script and cron search. [PR #209](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/209)
added 0700-preservation regression tests for isolated install, rejected
artifact, failed-install rollback and clean-room restore (8/8 CI PASS).
The earlier encrypted off-router archive was integrity checked and restored
in isolation. The specific actor who had already changed the live modes
before the aborted 2026-10-08 preflight remains unknown.

This is a **permission-hardening closure, not a production emergency rollback
or complete replacement-device restore**. Do not alter the Pi-hole exception
without verifying private consumer/retention requirements. The full
Pi-hole-aware Disaster Recovery gate [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)
remains OPEN. See [sanitized #200 closeout evidence](../evidence/2026-10-09/issue-200-final-permissions-acceptance.md).

### 2026-10-09 — optional ARMv7 BusyBox outside the CORE archive

The operator installed a standalone, statically linked BusyBox 1.36.1 at
/jffs/addons/asus-edge/tools/busybox/1.36.1/busybox. Its recorded SHA-256 is
08929e6cf52e8ed49ea46f1945ac51193613550099a2bbec24f90b0c1c58763a.
The original firmware /bin/busybox (1.25.1), /bin/sh and global PATH are
unchanged. Selected applets and a post-install project healthcheck passed;
firmware-internal NTP/shell behavior was not replaced.

**Recovery coverage gap:** scripts/backup.sh copies the project's bin/ and
legacy/ subtrees, not tools/. Do **not** infer this binary exists in the
existing CORE tarball or add it as an early-boot dependency. Keep a separate,
verified off-router copy (or reproducible build inputs), then reinstall in a
versioned directory **after** basic network/DNS/service recovery. Validate its
architecture and checksum on the rebuilt device. Its own reboot persistence
and a live rollback/removal test are pending.

The 2026-10-09 operator-reported 41-file checksum/manifest validation of a
current CORE backup was a **read-only stream integrity check**, not an isolated
restore of those 41 files and not a bare-metal recovery acceptance. It should
not be conflated with the earlier 39-file clean-room restore evidence.

See [custom BusyBox deployment, rollback and rebuild contract](custom-busybox-armv7.md)
and [sanitized BusyBox live evidence](../evidence/2026-10-09/custom-busybox-armv7-live-validation.md).

### Tailscale package/runtime drift

On the 2026-09-27 reference state, opkg metadata reports an older package version than the actual `/opt/bin/tailscale` and `/opt/bin/tailscaled` binaries report.

Therefore:

- `opkg list-installed` is useful inventory but not authoritative for the live Tailscale binary payload;
- the DR manifest must record both package metadata and live binary version/provenance;
- Tailscale authentication state remains excluded.

## Sanitized rebuild manifest

The repository includes a read-only collector for the reconstruction facts that are safe and useful to retain with DR evidence:

```sh
./scripts/collect-dr-manifest.sh /tmp/asus-edge-dr-manifest
```

The collector records:

- model and firmware identifiers from an explicit NVRAM allowlist;
- storage/mount and swap topology without filesystem UUIDs;
- Entware package inventory;
- Tailscale package metadata plus actual live binary version/hash;
- metadata and hashes for selected recovery-critical integration files;
- addon file-path inventory without reading addon configuration contents;
- Unbound and syslog-ng versions.

It deliberately does **not** call `nvram show`, `tailscale status`, or read configuration contents. Review the output manually before publishing it.

## NVRAM strategy

Do not add raw `nvram show` output to the project archive or public evidence. NVRAM can contain credentials, WAN authentication data, SSH material and private network configuration.

Use a separate native ASUS/Merlin settings export as a private DR artifact. Keep it:

- off-router;
- encrypted at rest;
- associated with the exact router model and firmware baseline;
- excluded from the Git repository.

A future restore test must document whether the native export is applied before or after JFFS/Entware reconstruction.

## BACKUPMON comparison

BACKUPMON is useful as a reference because it targets JFFS, NVRAM and external USB backup/restore and supports off-router network targets. Its documentation also warns against cross-model and cross-firmware restore assumptions.

For this project, direct installation is deferred because the addon introduces its own configuration, scheduling/network-mount behavior and update path. The current script can download a newer BACKUPMON copy into `/jffs/scripts`, so installing it would create another code/update owner on the reference router.

The present decision is therefore:

**project-native recovery first; BACKUPMON as a design/reference comparator.**

## Safe clean-room restore

The production restore script supports an explicit alternate-root validation mode through `EDGE_RESTORE_ROOT`. The default remains the live router paths; the alternate root exists only to exercise the same archive validation, snapshot, copy and rollback logic against a disposable directory.

Example on a workstation:

```sh
mkdir -p /tmp/asus-edge-dr-cleanroom
EDGE_RESTORE_ROOT=/tmp/asus-edge-dr-cleanroom \
  ./scripts/restore.sh BACKUP.tar.gz --apply
```

The alternate root must already exist, be writable, be absolute, must not be `/`, and must not be a symlink. This mode is intended for safe recovery validation; it does not prove router service startup or runtime ownership that depends on firmware/addon installation.

## Unbound runtime ownership reconstruction

The live reference router uses this directory ownership contract for the manager-generated runtime tree:

```text
/opt/var/lib/unbound  uid=65534 gid=0 mode=0755
```

The project backup preserves the runtime configuration file but does not treat the whole runtime directory as an opaque payload. On a clean rebuild, recreate the runtime directory before starting/recovering Unbound:

```sh
mkdir -p /opt/var/lib/unbound
chown 65534:0 /opt/var/lib/unbound
chmod 0755 /opt/var/lib/unbound
```

Do not treat the currently observed world-writable modes on `unbound.conf`, `root.key` or `dnsmasq.conf.add` as a required recovery contract. Those modes require a separate compatibility/hardening review. The trust-anchor file remains manager/runtime-owned and is not a primary project-backup payload.

## Post-restore validation checklist

After an actual router restore/rebuild, validate the recovered state in this order before relying on remote-only access:

1. **Storage**
   - confirm the intended ENTWARE and ROUTER_DATA filesystems are mounted read/write;
   - confirm `/opt` resolves to the intended Entware environment.
2. **Swap**
   - inspect `/proc/swaps`;
   - confirm the required swap is active before Tailscale recovery.
3. **Tailscale**
   - confirm `tailscaled` is running;
   - record the live binary version locally;
   - re-enroll/re-authenticate when node state was intentionally not restored;
   - confirm project `netfilter-mode=off` ownership.
4. **DNS / Pi-hole / Unbound**
   - confirm the Unbound runtime directory owner/mode contract;
   - validate the active Unbound configuration and TCP/UDP listener on `127.0.0.1:53535`;
   - recreate/validate the dedicated Pi-hole LAN alias before FTL binds port 53;
   - confirm Pi-hole FTL is running and the main-LAN DHCP policy advertises only the Pi-hole resolver;
   - confirm Pi-hole forwards allowed external queries to Unbound;
   - run ordinary resolution, a known synthetic block test and the DNSSEC negative test;
   - confirm conditional reverse DNS works for an active DHCP lease;
   - confirm firmware dnsmasq still forwards its own interception/local path to Unbound.
5. **Firewall**
   - confirm project-owned IPv4/IPv6 chains are present in the expected parent-rule positions;
   - confirm the terminal default-deny policy and any enabled LAN DNS/DoT controls.
6. **Project health**
   - run `/jffs/addons/asus-edge/bin/healthcheck.sh`;
   - do not declare recovery complete unless required checks pass or any warning is explicitly understood and documented.

A clean-room filesystem restore validates the archive and copy path only; this checklist is the runtime acceptance procedure for a real router recovery.

## Validation gates

Before #100 can close:

- [x] backup includes the validated post-mount integration hook as a review-only reference;
- [x] package/runtime rebuild manifest is captured;
- [x] NVRAM export procedure is documented and a private export is stored off-router;
- [x] Unbound runtime ownership recovery is proven or explicitly reconstructed;
- [x] backup archive and sidecar checksum are copied off-router and verified;
- [x] `restore.sh --dry-run` passes on the produced archive;
- [x] a safe restore test is completed without jeopardizing the known-good router;
- [x] post-restore validation covers storage, swap, Tailscale, DNS/Unbound, firewall and project healthcheck for the 2026-09-27 baseline;
- [x] published evidence is sanitized.

### Post-Pi-hole DR extension status — 2026-10-09

Issue #100 covered the earlier, pre-Pi-hole DR baseline.
Issue #129 extends recovery validation to the current DNS stack.

Verified private off-router recovery artifacts:

- ASUS Edge CORE: encrypted archive, checksum verification,
  clean-room dry-run/apply, and independent comparison of
  39 restored files.
- Pi-hole: dedicated Fedora-side generator, six offline
  regression tests, read-only production capture, encrypted
  archive and independent archive acceptance.
- Native ASUS settings CFG: encrypted private export,
  checksum verification and decrypted-payload hash match.
  Actual firmware import has not been tested.

The current Pi-hole archive contains 15 source files and
four manifest files. Independent validation confirmed the
complete file set, SHA-256 manifest, SQLite Gravity integrity,
Pi-hole UID/GID and mode contracts, and the FTL capabilities
manifest.

The earlier archive-metadata defect was corrected in the
generator: the Pi-hole directory is archived as 999:999 0755,
and gravity.db as 999:999 0640. The original backup and
separately corrected archival v2 remain private.

The post-mount hook is preserved as a review-only reference.
It must not be automatically deployed over AMTM-managed
startup integration.

The FTL capability set is recorded in the private manifest;
TAR contents do not independently establish the file
security.capability attribute after restoration. A recovery
operator must restore and verify that capability set on the
appropriate FTL binary and target filesystem.

Separate lab tests validated ARMv7 FTL startup, Gravity
filtering, Pi-hole -> Unbound DNS traffic and DNSSEC behavior.
These checks do not constitute a complete firmware and
Entware rebuild.

Remaining #129 acceptance work:

1. Document and validate reconstruction of Entware, package
   versions, service identities, file ownership and capabilities.
2. Restore and review swap-before-Entware startup ordering,
   dedicated Pi-hole LAN alias and Unbound runtime ownership.
3. **Completed 2026-10-09:** controlled reboot on the existing reference router with verified startup ordering, Entware/Pi-hole/Unbound/Tailscale and DNS Guard recovery, correct FTL capabilities and final healthcheck 0 failures/0 warnings. This is not a fresh-device rebuild.
4. Keep plaintext configuration, encrypted recovery archives,
   credentials and native CFG payloads out of the public repo.

Therefore, describe the current state as **verified private DR artifacts, isolated recovery components and successful production reboot persistence** — not a fully validated end-to-end replacement-router rebuild.


## 2026-10-09 — current Pi-hole-aware reboot acceptance and rebuild runbook

A physically supervised restart on the **existing** router succeeded without manual service repair. Production DNS Guard v3.2, its active `services-start` hook and the ARMv7 supervisor matched `main` by SHA-256. Both independent WAN bootstrap DNS candidates responded in fresh bounded probes prior to reboot. The documented reboot established new uptime; the first post-boot acceptance at 205 seconds confirmed two active swaps, correct Entware startup order, Unbound, Pi-hole FTL, exact binary capabilities, Tailscale, syslog-ng, DNS Guard local mode/watchdog and the router-local Pi-hole resolver. The project healthcheck reported **0 failures, 0 warnings**.

Boot logs show watchdog registration before Entware startup, NTP synchronisation, Unbound/FTL service startup and automatic Pi-hole resolver promotion. The early WAN-policy log does not by itself prove a specific resolver address at that instant.

- [Sanitized #129 production reboot evidence](../evidence/2026-10-09/issue-129-pihole-dr-reboot-persistence.md)
- [Pi-hole-aware stepwise reconstruction runbook](pihole-dr-rebuild-runbook.md)
- [Polish bare-router and empty-SSD emergency procedure](router-bare-metal-recovery-pl.md)
- [2026-10-09 engineering worklog](worklog/2026-10-09.md)

The clean-device recovery gate remains **OPEN**: package/account reconstruction, Unbound runtime ownership on the rebuilt target, Pi-hole FTL xattr reapplication on the target storage, restored Gravity/DHCP/DNSSEC/API/collector validation and native CFG import still require isolated execution. Do not repeat production reboots merely to replace this already successful persistence checkpoint.

## Out of scope

This project DR flow is not a full backup of personal/user data stored on router-attached media, does not publish or archive Tailscale authentication state, and does not claim cross-model or cross-firmware restoration.
