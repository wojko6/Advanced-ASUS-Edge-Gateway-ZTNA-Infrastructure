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
| reference `post-mount` swap-order fix | project archive | **added by #100 branch** | restore as a critical integration hook; review AMTM-generated content before apply |
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

The hook is partly addon-managed, so restore must not silently assume that an old post-mount file is compatible with a newly installed AMTM version. Restore procedure:

1. dry-run and inspect the archived hook;
2. establish the intended AMTM baseline;
3. merge/preserve the validated pre-Entware swap ordering;
4. run `sh -n`;
5. reboot only in a controlled maintenance window;
6. verify swap-before-Entware evidence and project health.

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

## Validation gates

Before #100 can close:

- [ ] backup includes the validated post-mount integration hook;
- [ ] package/runtime rebuild manifest is captured;
- [ ] NVRAM export procedure is documented and a private export is stored off-router;
- [ ] Unbound runtime ownership recovery is proven or explicitly reconstructed;
- [ ] backup archive and sidecar checksum are copied off-router and verified;
- [ ] `restore.sh --dry-run` passes on the produced archive;
- [ ] a safe restore test is completed without jeopardizing the known-good router;
- [ ] post-restore validation covers storage, swap, Tailscale, DNS/Unbound, firewall and project healthcheck;
- [ ] published evidence is sanitized.

## Out of scope

This project DR flow is not a full backup of personal/user data stored on router-attached media, does not publish or archive Tailscale authentication state, and does not claim cross-model or cross-firmware restoration.
