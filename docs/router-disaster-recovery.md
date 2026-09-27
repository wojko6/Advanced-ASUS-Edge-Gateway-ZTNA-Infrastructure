# Router disaster-recovery baseline

**Tracking:** #100  
**Status:** design / validation in progress

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

Read-only inventory on 2026-09-27 established:

- reference router: ASUS TUF-AX5400;
- reference firmware: GNUton / Asuswrt-Merlin 3004.388.11_1-gnuton1_tuf;
- JFFS is read/write;
- separate ENTWARE and ROUTER_DATA ext4 filesystems are active;
- two swap files are active;
- Tailscale, Unbound and syslog-ng are running;
- Unbound listens on 127.0.0.1:53535 over TCP and UDP;
- the live post-mount hook contains the validated #66 pre-Entware swap-order correction;
- AMTM, Unbound Manager, uiDivStats and Diversion-related state exist outside the project-owned tree.

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
| Unbound standard config | project archive | covered where present | do not overwrite manager-generated runtime config blindly |
| Unbound Manager runtime config | project archive | file covered | runtime directory ownership still requires explicit validation |
| Unbound Manager hook | project archive | `unbound.postconf` covered | manager scripts themselves are addon-owned and should be reinstalled/revalidated |
| syslog-ng main config | project archive | covered | credentials/certificates remain separately controlled |
| NVRAM | native ASUS/Merlin settings export | **separate required artifact** | keep an encrypted/off-router export for the same model/firmware baseline; do not publish raw values |
| Tailscale state/auth | intentionally excluded | recreate | re-enroll/re-authenticate after recovery; do not restore stale node secrets from the project archive |
| Tailscale package/runtime provenance | rebuild manifest | gap | package metadata alone is insufficient on the current reference state |
| Entware package inventory | rebuild manifest | gap | capture versions for reconstruction; packages are reinstalled rather than copied blindly |
| AMTM modules | reinstall/revalidate | addon-owned | restore integration points, then reinstall/validate AMTM-managed components |
| Diversion | reinstall/rebuild | partial / open | preserve only verified user-specific state once exact ownership is classified |
| uiDivStats | reinstall/rebuild | optional addon | not required for core gateway recovery |
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
4. **DNS / Unbound**
   - confirm the runtime directory owner/mode contract;
   - validate the active Unbound configuration;
   - confirm TCP/UDP listener on `127.0.0.1:53535`;
   - run a direct DNSSEC-validating query;
   - confirm dnsmasq forwards to the local Unbound listener.
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
- [x] post-restore validation covers storage, swap, Tailscale, DNS/Unbound, firewall and project healthcheck;
- [x] published evidence is sanitized.

## Out of scope

This project DR flow is not a full backup of personal/user data stored on router-attached media, does not publish or archive Tailscale authentication state, and does not claim cross-model or cross-firmware restoration.
