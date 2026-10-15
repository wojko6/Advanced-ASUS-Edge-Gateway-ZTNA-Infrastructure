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

## Controlled off-router backup and rollback preflight

**2026-10-15 operator evidence: single private Fedora off-router baseline copy verified PASS; redundant protected backup remains pending.** Before writing any SSD-mode helper into the live JFFS hook, use the Fedora workstation to **read-only fetch** the router's complete original `/jffs/scripts/post-mount` via the already trusted SSH connection (OpenSSH remote `cat`, not SFTP-dependent `scp`). Keep the downloaded original *locally*, never in a public or private GitHub repository.

Preconditions and acceptance:

1. Perform the operation **from Fedora**, not from the router. Prefer the existing SSH host configuration and known pinned host key. A temporary local directory must be mode `0700` and the original file mode `0600` on Fedora, with `umask 077`. No SSH agent keys, UUID values or file contents should be printed.
2. Before retrieving bytes, verify the remote JFFS file is still mode `0755`, UID:GID `0:0`, and its SHA-256 equals the operator-observed baseline `8625bee2558d046e789e9ea871ed5d7758be42c39548ca7f6a63757704a02b66`. A mismatch is a **STOP** rather than something to "repair".
3. Fetch by `ssh ... 'cat /jffs/scripts/post-mount'` into a new local temporary file. Validate that local SHA-256 matches baseline, and re-query remote SHA-256 *after* transfer to detect a concurrent hook rewrite. Run `sh -n` on the saved file; only then mark the private original as valid and write a local-only metadata manifest including router path, original owner/mode, verified hash and time.
4. Do **not** modify `/jffs/scripts/post-mount`, remount any device, activate/deactivate swap, change permissions on router, disclose original hook, or run the candidate live during this backup stage. Do not copy the original into CI public test fixtures.
5. Preserve at least one additional **encrypted off-router** copy or established protected backup before any future production maintenance; a single file on the same Fedora disk is not sufficient disaster recovery. Independently confirm recovery access to the router.
6. **Future rollback procedure, NOT executed by the backup phase:** in a separately authorized maintenance window, stop touching the hook on any concurrent installer/AMTM updater; compare the saved original's SHA-256; restore it atomically via a private staged file to JFFS, preserving root:root and mode `0755`; check `sh -n`, the original hash, swap-before-AMTM ordering and service health. Do not execute the original hook manually: it is an event-driven router hook. If the original is restored, the firmware will still revert the SSD roots to `0777` at subsequent mount; that is a documented security regression to manage rather than a guarantee of remediation.

**2026-10-15 operator evidence: privately composed actual saved-hook copy and disposable byte-for-byte local rollback both PASS.** Original hash verification, restrictive local file/directory permissions, exact single-snippet delta, insertion after line 16, saved and composed `sh -n`, disposable test deployment/rollback to baseline, and preservation of original/candidate were reported PASS. `ROUTER_MODIFIED=NO`. This is an exact-diff and local restore proof; it does not demonstrate actual router hook behavior during boot, real JFFS restore, or independence of copies.

### 2026-10-15 — independent Verbatim SSD GPG backup verified

Operator executed the Fedora read-only source preflight: original post-mount SHA-256 parity PASS. Independently identified the external USB Verbatim SSD as a 953.9 GB exFAT partition, mounted it as an existing filesystem (without repartitioning or formatting), and saved a **new GPG symmetric AES-256 encrypted tar archive** of the original script and manifest into a separate directory. GPG encryption succeeded. The archive was immediately decrypted in a streaming verification and the recovered original script matched baseline SHA-256 `8625bee2558d046e789e9ea871ed5d7758be42c39548ca7f6a63757704a02b66`. Operator-provided evidence:

```text
SOURCE_SHA256=PASS
USB_DEVICE=PASS
FILESYSTEM=exFAT
SSD_MOUNT=PASS
GPG_ENCRYPTION=COMPLETE
ENCRYPTED_RECOVERY=PASS
SOURCE_INTEGRITY=PASS
USB_STORAGE=PASS
AES256_BACKUP=PASS
ENCRYPTED_RECOVERY_SHA256=PASS
SOURCE_FILES_UNCHANGED=YES
ROUTER_MODIFIED=NO
ISSUE235_ENCRYPTED_BACKUP_COMPLETE
```

The separately stored encrypted copy is on the **external Verbatim SSD**, not the laptop's internal NVMe. The secret GPG passphrase and full original hook bytes were never provided to the public repository. Test includes a successful decrypt-and-verify, but does not yet establish readability following a physical disconnect/reconnect, passphrase-manager recovery, or full JFFS restore. The SSD should be unmounted/powered down cleanly before disconnection. This backup is protection against local filesystem loss, not a production deployment approval.

**Next gate:** confirm Verbatim can be cleanly flushed/unmounted and retained independently from the Fedora laptop. Then audit private UUID mapping file security, root-level mount consumers, and installer ownership before seeking explicit production authorization. Remain in DRAFT until that review and a separately approved reboot.

## 2026-10-15 — safe external backup disconnect accepted

Following the independently encrypted Verbatim SSD backup and successful streamed recovery SHA verification, the operator reported `MOUNT_IDENTITY=PASS`, `USB_IDENTITY=PASS`, `ENCRYPTED_ARCHIVE=PASS`, `DATA_FLUSH=COMPLETE`, `SAFE_UNMOUNT=PASS`, `USB_POWER_OFF=PASS`, `ROUTER_MODIFIED=NO`, and `ISSUE235_SAFE_DISCONNECT_COMPLETE`. The OS confirmed that the external exFAT partition unmounted. It is safe to physically disconnect the drive. Reconnect/decrypt verification after an extended offline period remains a separate optional durability gate; no production ASUS files were changed.

**Next gate (read-only):** verify actual current JFFS path/permission ownership and whether the candidate helper and private expected-UUID files are even installed. No candidate file or private UUID has been deployed by this draft; absent helper/UUID files must be reported as `NOT_CONFIGURED`, not guessed or silently created. Then audit actual mount-root writers/consumers for mode `0755` compatibility and prepare an explicit go/no-go; no live chmod/hook edits/reboot.

## 2026-10-15 — live-router JFFS baseline inventory

Operator's **read-only** pre-install audit returned:

```text
JFFS_MODE_OWNER=755:0:0
ADDONS_MODE_OWNER=755:0:0
ASUS_EDGE_MODE_OWNER=755:0:0
BIN_MODE_OWNER=755:0:0
PRIVATE=NOT_CONFIGURED
ROUTER_DATA_UUID=NOT_CONFIGURED
ENTWARE_UUID=NOT_CONFIGURED
SSD_MODE_HELPER=NOT_CONFIGURED
ORIGINAL_POST_MOUNT=PASS
POST_MOUNT_SYNTAX=PASS
UUID_VALUES_PRINTED=NO
PRIVATE_FILE_CONTENT_PRINTED=NO
JFFS_MODIFIED=NO
ROUTER_PERMISSIONS_MODIFIED=NO
SERVICES_RESTARTED=NO
```

Current ancestor and bin directories are `0755 root:root`. The proposed private UUID mapping directory and UUID files and mode helper do **not yet exist**, consistent with the Draft PR being **not installed**. No writes or production service operations occurred. Their target permissions (`private` root:root `0700`, UUID files root:root `0600`, executable helper root-owned with reviewed access) remain **design requirements**, not production PASS findings. The baseline live `post-mount` SHA/parse remained unchanged.

**Upcoming read-only gate:** enumerate only sanitized aggregate first-level filesystem owner/mode classes and running service identities (without printing directory contents or credentials); confirm current SSD roots' mount identity/mode and swap active state; review any legitimate non-root root-level writers. Root-mode `0755` changes must remain gated pending that assessment, protected private UUID storage design, installer ownership, staged integration review, and explicit authorization.

## 2026-10-15 — three identified RouterCloud writable directories

Read-only live ASUS inspection identified the three `0777`, root:root, non-sticky directories at the ROUTER_DATA mount root:

- `.routercloud-favorites-armv7-smoke`
- `.routercloud-favorites-feature-check`
- `.routercloud-rollback`

Names suggest test and rollback uses, but the first two have not been proven obsolete, and the rollback directory must be treated as recovery-critical until inspected. Existing permission exposure persists inside these directories even if the mount-root inode changes from `0777` to `0755`. Do not automatically delete or chmod anything. Main-branch source search did not find exact references to the two favorites names; a search result for `routercloud-home-rollback.sh` uses a different temporary filename pattern and does not validate ownership or use of `.routercloud-rollback`.

Next review is read-only collection of directory metadata and child type/mode counts, without printing contents or private credentials; review service/backup reliance before any separate child hardening. Operator reported file contents untouched, permission changes NO and services restarted NO. This remains out of the narrow mount-root mode patch deployment authorization.
