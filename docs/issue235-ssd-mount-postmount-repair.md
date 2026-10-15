# Issue #235 — USB mount-root DAC persistence: isolated post-mount candidate

**Status:** Draft design and isolated mock test. **NO production deployment approval.**
**Date:** 2026-10-15.
**Hardware:** ASUS TUF-AX5400 / GNUton Asuswrt-Merlin 3004.388.11_1-gnuton1; two distinct ext4 partitions on the SSD, mounted as `/tmp/mnt/ROUTER_DATA` and `/tmp/mnt/ENTWARE`.

## Root cause established in the matching GNUton release sources

[GNUton `release/src/router/rc/usb.c` at `3004.388.11_1-gnuton1`](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/rc/usb.c#L2143-L2146) contains, in `mount_partition()`, the following mount-success behavior:

```c
if (ret == MOUNT_VAL_RONLY || ret == MOUNT_VAL_RW) {
    chmod(mountpoint, 0777);
}
```

Later in the same function, the firmware invokes `run_custom_script("post-mount", 120, mountpoint, NULL)` ([source](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/rc/usb.c#L2284-L2291)). Thus the JFFS custom hook executes **after** the firmware attempts its `0777` mount-root permission change.

Read-only production snapshots after the Oct 15 boot found root:root `0777` on **both** physical mount roots, while `/tmp/mnt/ENTWARE/entware` remained `0755` and `.routercloud-system` remained `0700`. The direct source-level instruction matches those observations. It is not a kernel audit trace of the running firmware binary. Mount-root inode ctimes in January 2024 are consistent with very early boot before clock correction.

## Why this matters

Mode `0777` on a nonsticky mount root means ordinary local users can create entries, rename existing root-owned child entries, and unlink their names, subject to filesystem policy. Protected mode `0700` on a child does not protect its **entry** from modifications through a writable parent. This is a path integrity issue; it is **not proof of a network exploit**.

Immediate authorized Stage 1 on Oct 14 set both physical SSD partition roots to `0755` and RouterCloud private state to `0700`, passing functional tests, backup and recovery gates. Oct 15 demonstrated that the mount-root protection is **not persistent across boot**. These findings do not invalidate the historical Oct 14 spot-check; they narrow its acceptance scope.

## Design candidate

[Draft helper](../router/scripts/issue235-ssd-mount-mode):

- Not called by the current installer, `services-start` or `post-mount`. It does **not** run in production from this branch.
- Accepts exactly two arguments: a firmware-provided mount path and a **pre-verified expected ext4 filesystem UUID**, which must be retained privately on the router (never hardcoded in a public GitHub source file).
- Applies only when the exact path is `/tmp/mnt/ROUTER_DATA` or `/tmp/mnt/ENTWARE`; other mounts are skipped without modification.
- Requires a real, uniquely matching `/proc/mounts` ext4 entry with a `/dev/` source, a directory that is not a symlink, root:root ownership, a canonical-shaped UUID, and matching `blkid -s UUID -o value` output for that device.
- Will only accept `0777` for transition to `0755` or preserve already-hardened `0755`. Unexpected modes, missing `blkid`, UUID mismatch, wrong device, missing mount, and all command errors cause an explicit `REVIEW` (no intentional chmod).
- Makes only one nonrecursive `chmod 0755` on the validated mount root, then verifies `0755`. Neither `RouterCloud`, `.routercloud-system`, `entware`, firmware-generated metadata, nor swap files are edited.
- This is ordinary path-based shell logic and **does not eliminate theoretical TOCTOU races** between checking and changing the mount; the broader trust model assumes the root-owned JFFS hook and firmware boot path are trusted.

**Dependency boundary:** the live reference `/jffs/scripts/post-mount` is operator-managed alongside AMTM. Existing `swapon` must occur *before* sourcing `/jffs/addons/amtm/mount-entware.mod`, as documented in [boot-service dependency flow](architecture/boot-service-dependency-flow.md). Never overwrite the entire live hook from a repository template or shift swap initialization past Entware startup.

## Local isolated test (Fedora/CI, unprivileged)

```sh
sh -n router/scripts/issue235-ssd-mount-mode
python3 tests/test-issue235-ssd-postmount-mode.py
sh tests/test-static.sh
```

The isolated test creates fake directories under a randomized `/tmp` tree, rewrites **only an ephemeral test copy** of the candidate's mount-table and mount-root constants, and uses mocked `blkid`/failure-case `chmod` binaries. It must never read or change real `/proc/mounts`, ASUS device mounts, JFFS, RouterCloud data or secrets. Tests cover both labeled partitions, idempotence, malformed/mismatched UUID, missing/non-ext4/fake-device mount records, unexpected modes, symlink, wrong owner, failed `blkid`, failed `chmod` and skipped other media. `tests/test-static.sh` includes the isolated runner in this branch. A mock PASS is **not** live ASUS validation.

## Production go/no-go prerequisites — NOT COMPLETED

1. Confirm the exact actual live `post-mount` control flow without printing private values; preserve original JFFS hook byte-for-byte in verified **private and off-router** backups. Establish unambiguous insertion point **after swap activation yet before AMTM startup** as appropriate to each mounted volume, and ensure the hook returns safely for unrelated media or a failed helper without blocking swap.
2. Verify on the router that `blkid -s UUID -o value` works for each **actual mounted ext4 device**. Record UUID mappings **privately** with root-only write protection. Reject unexpected collisions, missing UUIDs, symlinks, mount aliases, or unsupported BusyBox syntax. Binding mountpoint labels alone is not sufficient.
3. Audit existing root-level writers on both partitions and all relevant consumers, including RouterCloud, Fedora restricted rsync backup/sync, Entware/AMTM, swap, Tailscale, Unbound, DNS Guard and firmware-created metadata. Explicitly decide what cannot be restricted and why. Do not assume mode `0755` is compatible with unknown daemons merely because earlier spot-tests passed.
4. Test a composed live-hook **copy** on a disposable fixture, prove swap-before-AMTM textual and functional ordering, and confirm `sh -n`, code review and CI PASS. Have an idempotent rollback to the **original hook** with preservation of its ownership and executable mode.
5. Request separate, explicit operator approval for limited live deployment. Capture pre- and post-deploy checks with zero additional router/daemon restarts; test both real mounts, swap, services, HTTP UI, rsync and backup.
6. Schedule a **separate explicitly approved controlled reboot** to prove that two SSD roots are `0755`, private state remains `0700`, partitions and swap mount correctly, startup sequence is healthy, no DNS/Tailscale regressions occur, and backups run. Also test later physical remount/hotplug if operationally applicable.

**GO = all gates pass + operator approval.** Until then: do not install the helper, change live JFFS hooks, run production chmod, trigger mounts/reboots or merge this draft as an implicit deployment authorization.

## Tracking

- [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235)
- [Root-cause source finding](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6185981597)
- [Oct 14 public engineering worklog](worklog/2026-10-14.md)
