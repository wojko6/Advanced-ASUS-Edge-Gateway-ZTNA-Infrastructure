# Entware feed and SSD root-permission live checkpoint — 2026-10-14

> **Follow-up recorded 2026-10-15 (historical acceptance scope):** The October 14 `0777 -> 0755` ENTWARE mount-root change passed immediate bounded checks, **not boot persistence**. On October 15 both ENTWARE and ROUTER_DATA ext4 mount roots were again observed root:root `0777`, consistent with GNUton firmware's mount-success mode reset. [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) remains open and Draft [PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) is not deployed. See [October 15 worklog](../../docs/worklog/2026-10-15.md). The historical October 14 PASS below remains valid **only for that immediate test window**.

**Status:** COMPLETED / BOUNDED LIVE ACCEPTANCE  
**Source:** operator-supplied ASUS TUF-AX5400 SSH outputs; no independent remote execution by the repository.  
**Production change:** yes, limited to Entware metadata/configuration permissions and the ext4 `ENTWARE` volume root mode. No package installation, router reboot or service restart was reported.

## Scope and environment

- Asuswrt-Merlin GNUton `3004.388.11_1-gnuton1_tuf`; Entware architecture `armv7-3.2`, with `all` packages.
- `/opt -> tmp/opt -> /tmp/mnt/ENTWARE/entware`.
- `/tmp/mnt/ENTWARE` is a mounted ext4 filesystem with observed options `rw,nodev,relatime,stripe=8191,data=ordered`.
- `/tmp/mnt` is a separate firmware-managed parent, observed mode `0777`; it was **not** modified.
- The Entware volume root initially had mode `0777`, while its `entware` directory had `0755`, `lost+found` `0700`, and `myswap.swp` `0600`.

## Package-index review and limited file hardening

The operator observed two HTTPS feeds, `entware` and `entware-pi-hole`. HTTPS is transport protection, **not proof of authenticated package-index signatures**. Initial `/opt/etc/opkg.conf` and both feed-index files were mode `0666`. A root SSH session initially reported `umask 0000`; this association does not prove that every package-management service or startup hook inherited the same setting.

After making and comparing private JFFS backup copies, a bounded procedure changed:

| Object | Before | After |
| --- | --- | --- |
| `/opt/etc/opkg.conf` | `0666` | `0600` |
| `/opt/var/opkg-lists/entware` | `0666` | `0644` |
| `/opt/var/opkg-lists/entware-pi-hole` | `0666` | `0644` |

A scoped `umask 022` was used for `opkg update`, while private backup handling used `umask 077`. The command returned `OPKG_UPDATE_RC=0` and `opkg list-upgradable` printed no entries.

A **keyword-only** tally of the saved private `update.log` showed:

```text
DOWNLOAD_ATTEMPTS=2
UPDATED_LISTS=2
SIGNATURE_PASS_MESSAGES=0
NOT_MODIFIED_MESSAGES=0
ERROR_MESSAGES=0
```

`SIGNATURE_PASS_MESSAGES=0` means the log tally contained no explicit signature-success messages. It does **not** establish whether signature validation occurred. The `entware` index retained an August 31 modification timestamp after refresh; the Pi-hole index showed October 13. These timestamps alone do not establish package freshness or upstream release parity. **No `opkg upgrade`, `opkg install`, or live package replacement took place.** Do not infer Tailscale runtime binary parity from Entware package metadata.

## Ext4 volume-root hardening

Pre-change checks found exactly one reference among the inspected startup files: `/jffs/scripts/post-mount`. Operator-supplied excerpts showed:

- `SWAPFILE="${1}/myswap.swp"` at line 4;
- `/sbin/swapon "$SWAPFILE" 2>/dev/null || true` at line 8;
- `. /jffs/addons/amtm/mount-entware.mod` at line 18.

`sh -n /jffs/scripts/post-mount` passed, and `/tmp/mnt/ENTWARE/myswap.swp` was active before the change. This is a bounded dependency review, **not** an exhaustive proof that no uninspected process writes to the mount root.

The operator created a root-private JFFS rollback record and changed **only**:

```text
/tmp/mnt/ENTWARE: 0777 -> 0755
```

The procedure verified the new mode, `/opt/etc/opkg.conf` availability, Entware directory presence and continued active `ENTWARE` swap. Its `chmod 0777 /tmp/mnt/ENTWARE` rollback procedure was documented but **not executed or tested**. There was no recursive chmod; `/tmp/mnt`, the `entware` tree and both swap files were not changed.

## Post-change acceptance

Operator-reported result:

```text
DIRECTORY_HARDENING=PASS
ENTWARE_PATH=PASS
SWAP_PRESERVED=PASS
unbound=RUNNING
pihole-FTL=RUNNING
tailscaled=RUNNING
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

The deployed project healthcheck also reported PASS for Unbound control reachability and DNSSEC `AD` validation on port `53535`, syslog-ng and the monitored firewall/DNS enforcement chains. `/proc/swaps` showed both files active:

| Mount | Size (KiB) | Used (KiB) |
| --- | ---: | ---: |
| `ROUTER_DATA/myswap.swp` | 2097148 | 4932 |
| `ENTWARE/myswap.swp` | 524284 | 0 |

Process presence plus this healthcheck is **not** a substitute for browser-level RouterCloud, end-to-end Pi-hole client filtering, external Tailscale path, or post-reboot validation. No dedicated RouterCloud functional smoke test was recorded in this checkpoint.

## Open follow-ups / safety boundary

1. Determine the origin of root-session `umask 0000`; a temporary `umask 022` applied to one SSH session is **not** persistent system-wide hardening.
2. Validate the `0755` ENTWARE root mode after the **next separately authorized** remount/reboot, including swap-before-Entware startup ordering. No reboot was performed solely for this check.
3. Review the `0777` firmware-managed `/tmp/mnt` parent and mount trust boundary without changing it blindly.
4. Audit actual package signature-verification mechanism and configured feed trust before future package installs. A successful update and zero upgrade candidates do not prove upstream-current versions.
5. Keep RouterCloud [issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) independent; Entware mode hardening does **not** resolve its runtime identity, file-origin and TOCTOU security gates.

**Evidence handling:** only sanitized observed output and conclusions are published. Local backup data, original `opkg.conf`, feed URLs, raw update log and secrets remain out of Git. See [2026-10-14 public worklog](../../docs/worklog/2026-10-14.md).
