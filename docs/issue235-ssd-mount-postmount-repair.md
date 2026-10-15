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
- Requires a real, uniquely matching `/proc/mounts` ext4 entry with a `/dev/` source, a directory that is not a symlink, root:root ownership, a canonical-shaped UUID, and UUID parity after normalization of the `blkid -s UUID -o value` response for that device (either canonical value-only or GNUton BusyBox tagged/quoted `UUID="..."` form).
- Will only accept `0777` for transition to `0755` or preserve already-hardened `0755`. Unexpected modes, missing `blkid`, UUID mismatch, wrong device, missing mount, and all command errors cause an explicit `REVIEW` (no intentional chmod).
- Makes only one nonrecursive `chmod 0755` on the validated mount root, then verifies `0755`. Neither `RouterCloud`, `.routercloud-system`, `entware`, firmware-generated metadata, nor swap files are edited.
- This is ordinary path-based shell logic and **does not eliminate theoretical TOCTOU races** between checking and changing the mount; the broader trust model assumes the root-owned JFFS hook and firmware boot path are trusted.

**Dependency boundary:** the live reference `/jffs/scripts/post-mount` is operator-managed alongside AMTM. Existing `swapon` must occur *before* sourcing `/jffs/addons/amtm/mount-entware.mod`, as documented in [boot-service dependency flow](architecture/boot-service-dependency-flow.md). Never overwrite the entire live hook from a repository template or shift swap initialization past Entware startup.

## 2026-10-15 — GNUton BusyBox blkid compatibility verified (read-only)

The real ASUS operator ran UUID probes for both ext4 SSD mounts. Both were genuine block devices with a working `blkid` command (`RC=0`). The GNUton BusyBox command `blkid -s UUID -o value` produced **not** a raw 36-character UUID but a tagged quoted record with an accompanying volume label: output lengths were 74 for `ROUTER_DATA` and 70 for `ENTWARE`. Safe structural parsing found `UUID="` in both, extracted a 36-character canonical UUID from each, and confirmed that the two UUIDs differ; no UUID values or device identifiers were printed or committed. The result was `ISSUE235_BLKID_FORMAT=PASS`, production changes NO.

The isolated candidate was updated to accept **exactly** canonical value-only UUID output and a single quoted tagged GNUton UUID. It rejects malformed, unquoted, duplicated or mismatched UUID fields without proceeding to chmod. The UUID is still compared to the privately preverified expected UUID; parsing a label by itself is not sufficient identity validation. The CI mock suite now explicitly models GNUton tagged/quoted output for both volumes, confirms value-only compatibility, and covers malformed/duplicate-tag rejection. **This is not proof of production integration or reboot persistence.**

## 2026-10-15 — restricted-PATH live-router gate accepted

Operator ran the read-only on-ASUS `ISSUE235 / EARLY PATH UUID GATE`, deliberately invoking `blkid` with `PATH=/usr/sbin:/usr/bin:/sbin:/bin` to approximate the draft helper's command lookup. Both `ROUTER_DATA` and `ENTWARE` reported `RESTRICTED_PATH_BLKID_RC=0`, `UUID_FORMAT=PASS`, and the pair reported `UUIDS_DISTINCT=PASS` with `ISSUE235_EARLY_PATH_GATE=PASS`. No identifiers were printed and the operator reported `PRODUCTION_CHANGES=NO`.

**Acceptance boundary:** the check ran on the *already-booted router*, not from a newly invoked early `post-mount` hook. It establishes executable availability and UUID parser-compatible output under the intended restricted PATH in the current environment, **not** timing, device readiness, actual hook integration or post-reboot persistence. The hook must not depend on Entware or `/opt`-only utilities; its integration is still blocked pending read-only live-hook control-flow inspection, private expected-UUID binding and verified rollback.

## Local isolated test (Fedora/CI, unprivileged)

```sh
sh -n router/scripts/issue235-ssd-mount-mode
python3 tests/test-issue235-ssd-postmount-mode.py
python3 tests/test-issue235-postmount-composed.py
sh tests/test-static.sh
```

The isolated test creates fake directories under a randomized `/tmp` tree, rewrites **only an ephemeral test copy** of the candidate's mount-table and mount-root constants, and uses mocked `blkid`/failure-case `chmod` binaries. It must never read or change real `/proc/mounts`, ASUS device mounts, JFFS, RouterCloud data or secrets. Tests cover both labeled partitions, GNUton tagged/quoted output, raw canonical output, duplicated/unclosed/unquoted UUID tags, idempotence, malformed/mismatched UUID, missing/non-ext4/fake-device mount records, unexpected modes, symlink, wrong owner, failed `blkid`, failed `chmod` and skipped other media. `tests/test-static.sh` includes the isolated runner in this branch. A mock PASS is **not** live ASUS validation.

## Production go/no-go prerequisites — NOT COMPLETED

1. Confirm the exact actual live `post-mount` control flow without printing private values; preserve original JFFS hook byte-for-byte in verified **private and off-router** backups. Establish unambiguous insertion point **after swap activation yet before AMTM startup** as appropriate to each mounted volume, and ensure the hook returns safely for unrelated media or a failed helper without blocking swap.
2. **Partially accepted:** on-router read-only tests confirmed both devices return a tagged/quoted UUID with `blkid -s UUID -o value`, with independently extractable 36-character, distinct IDs (`ISSUE235_BLKID_FORMAT=PASS`). Still required: confirm the installed early-boot BusyBox binary/PATH exhibits the same output and verify private mount-label-to-UUID mapping with root-only access, before modifying the hook. Reject unexpected collisions, missing UUIDs, symlinks, mount aliases or parser drift. Binding mountpoint labels alone is not sufficient.
3. Audit existing root-level writers on both partitions and all relevant consumers, including RouterCloud, Fedora restricted rsync backup/sync, Entware/AMTM, swap, Tailscale, Unbound, DNS Guard and firmware-created metadata. Explicitly decide what cannot be restricted and why. Do not assume mode `0755` is compatible with unknown daemons merely because earlier spot-tests passed.
4. Test a composed live-hook **copy** on a disposable fixture, prove swap-before-AMTM textual and functional ordering, and confirm `sh -n`, code review and CI PASS. Have an idempotent rollback to the **original hook** with preservation of its ownership and executable mode.
5. Request separate, explicit operator approval for limited live deployment. Capture pre- and post-deploy checks with zero additional router/daemon restarts; test both real mounts, swap, services, HTTP UI, rsync and backup.
6. Schedule a **separate explicitly approved controlled reboot** to prove that two SSD roots are `0755`, private state remains `0700`, partitions and swap mount correctly, startup sequence is healthy, no DNS/Tailscale regressions occur, and backups run. Also test later physical remount/hotplug if operationally applicable.

**GO = all gates pass + operator approval.** Until then: do not install the helper, change live JFFS hooks, run production chmod, trigger mounts/reboots or merge this draft as an implicit deployment authorization.

## Tracking

- [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235)
- [Root-cause source finding](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6185981597)
- [Oct 14 public engineering worklog](worklog/2026-10-14.md)

## 2026-10-15 — candidate insertion boundary and composed-hook fixture

After the earlier structural baseline, the operator ran a second **read-only** boundary audit against the same live JFFS `/jffs/scripts/post-mount`:

```text
SOURCE_INTEGRITY=PASS
SYNTAX=PASS
LINE_17_SLOT=BLANK_OR_COMMENT
CONDITIONAL_DEPTH_AFTER_LINE_16=0
EARLY_EXIT_REFERENCES=0
ERREXIT_REFERENCES=0
SWAP_BEFORE_AMTM=PASS
INSERTION_BOUNDARY_STATIC=PASS
SCRIPT_CONTENT_PRINTED=NO
FILES_MODIFIED=NO
SWAP_MODIFIED=NO
SERVICES_RESTARTED=NO
```

The audited SHA-256 was `8625bee2558d046e789e9ea871ed5d7758be42c39548ca7f6a63757704a02b66`. The results confirm only the static placement class of the blank/comment slot at line 17, after the source file's swap operation (line 8) and before sourcing AMTM (line 18). **The actual JFFS hook bytes are not included in the public repository**; static keyword/depth checks are not a full control-flow proof.

A proposal for that placement is recorded in [`issue235-postmount-integration.snippet`](../router/scripts/issue235-postmount-integration.snippet). It is **not installed** and has no installer registration. The proposal:

- Uses exactly the `$1` mounted volume path to select one of two privately stored expected UUID files under a root-owned JFFS subtree. No actual UUID values are in Git.
- Invokes the separately validated candidate helper for an allowlisted mount only when its executable and the non-symlink private UUID file are available.
- On missing private UUID, helper verification failure or unrelated USB volume, performs **no intentional root-mode change**, reports a status without revealing identifiers, and continues to the existing AMTM line (does **not** `exit`/`return` or use `set -e`).
- Must not be activated before the private mapping's integrity/ownership, real early-boot readiness, existing hook preservation, rollback, and root-level consumers have been reviewed.

The synthetic [composed-hook test](../tests/test-issue235-postmount-composed.py) uses only disposable `/tmp` directories, a synthetic nested-IF + swap-before-AMTM script, fake `swapon` and fake AMTM sourced after a substituted version of the proposed snippet, plus mocked `blkid` and mount table. The fixture tests both target volumes, idempotent second run, invalid UUID, missing/symlink UUID file, and unrelated media. In failure cases it requires **swap and AMTM to continue** while leaving the synthetic root at `0777`; success cases require `0755` before AMTM. It is included in `tests/test-static.sh` on this draft branch.

**Limitations:** the test does not execute the exact real JFFS source, cannot prove real boot ordering/races, cannot validate firmware-managed `0777` rewrite after hook, and does not give live production approval. A reversible composed **copy of the real hook** can only be validated by the operator in an isolated offline fixture under controlled conditions; never upload unsanitized JFFS contents/UUID material to the public repo.

**Recovery/deployment gate still blocked:** obtain private byte-for-byte copies of `post-mount` on independent storage, verify SHA and mode, confirm the rollback restores the original hook while maintaining swap-before-AMTM, test root-level consumers and backups, ask explicit operator approval for scoped live activation, and perform a separate later approved reboot. Do not rely on rollback to `0777` as the default security response; reversion of the hook does not retroactively protect an ext4 root already set to `0777` by firmware.

## 2026-10-15 — structural JFFS post-mount snapshot

On the production router, the operator performed another read-only JFFS hook structural check:

```text
POST_MOUNT_SYNTAX=PASS
POST_MOUNT_SHA256=8625bee2558d046e789e9ea871ed5d7758be42c39548ca7f6a63757704a02b66
LINE_4=MOUNT_ARGUMENT
LINE_6=IF
LINE_7=IF
LINE_8=SWAP
LINE_9=FI
LINE_11=IF
LINE_13=ELSE
LINE_15=FI
LINE_16=FI
LINE_18=AMTM
LINE_23=IF
LINE_29=IF
LINE_36=ELSE
LINE_39=FI
LINE_40=FI
SCRIPT_CONTENT_PRINTED=NO
FILES_MODIFIED=NO
PERMISSIONS_MODIFIED=NO
SWAP_MODIFIED=NO
SERVICES_RESTARTED=NO
```

**Interpretation:** `post-mount` remains syntactically valid, with an observed swap operation on line 8 before the AMTM sourcing on line 18, consistent with the critical #66 startup ordering. The first compound IF region appears to end at line 16; the proposed insertion region near line 17 is a **candidate only**, because a keyword-level sanitized output cannot prove that the top-level control path reaches the slot or that no additional side effects exist. The immutable-reference SHA-256 is a baseline for subsequent **on-device, read-only** source and staged-copy checks, not a substitute for a byte-for-byte off-router rollback copy.

**Current gate:** do not insert a helper or overwrite `/jffs/scripts/post-mount` yet. A narrowly scoped, read-only check should confirm the exact line 17 class, lack of early `exit/return/exec` before the AMTM call, and balanced `if/fi` at the candidate boundary without exposing hook content. Keep any composed-hook testing in an isolated fixture before operator review. Do not conflate shell syntax PASS with boot persistence or recovery acceptance.
