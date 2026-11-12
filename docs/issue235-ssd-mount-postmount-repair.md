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

## 2026-10-15 — RouterCloud directory dependency sampling (read-only)

Operator checked first-level *subdirectories* within the three root-owned, nonsticky world-writable directories on ROUTER_DATA. Favorites ARMv7 smoke has one world-writable subdir; favorites feature check has two world-writable subdirs; rollback has one root-standard, non-world-writable subdir. All three report zero active process file-descriptor/current-working-directory path references at the instant of sampling. No directory names below the previously known three locations, file contents, process arguments or secrets were disclosed; no production changes.

Zero references are **not** evidence of an obsolete workspace or safe deletion. Parent directory mode 0777 still permits unprivileged manipulation of child *names*, including replacement of the protected rollback subdirectory's entry. Narrow Draft PR #245 only repairs the SSD mount-root inodes; independent RouterCloud subtree hardening requires a separate consumer, deployment, rollback and backup review. No recursive chmod or cleanup is authorized.

[Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6187630758).

## 2026-10-15 — SSD writer classification (read-only)

Reported router classification:

| Area | Writer candidates | Absolute mount paths | Write command + mount path on same line | Privilege-change hints | Oversized unknown files |
|---|---:|---:|---:|---:|---:|
| JFFS hooks | 1 | 0 | 0 | 0 | 0 |
| Entware init | 1 | 1 | 0 | 0 | 0 |
| ASUS Edge bin | 5 | 2 | 1 | 0 | 1 |

The earlier scan identified 45 inspected files, 9 files referring to SSD, and 7 candidates matching a broad write-command heuristic. The two swap files are mode 0600 and root-owned. This classification found one syntactic same-line match, **not one proven SSD mount-root write**. Dynamic paths, source-vs-destination ambiguity, non-shebang text, systemd service users, privileged versus unprivileged commands and scheduled jobs remain outside this heuristic. The oversized unknown file needs metadata/type inspection; do not execute it to classify it. No content, filename, file, permission, swap or service change was reported.

The remaining compatibility gate is REVIEW, with production changes blocked. Next inspect the one same-line candidate's destination classification without exposing source text and determine the type of oversized file. Do not merge or deploy until consumers and rollback are accepted explicitly.

[Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6187804095).

## 2026-10-15 — specific writer inventory and source cross-check

Operator-provided, read-only inventory of the seven candidate scripts: JFFS `services-start` (0755 uid/gid 1000:1000); Entware `S67routercloud` (0755 root:root); ASUS Edge bin `personal-cloud-rsync`, `personal-cloud-rsync-backup`, `services-start`, `services-start.bak-20260910`, `services-start.pre-dns-watchdog-20261006-213719` (all 0755 root:root). The large unclassified `edge-dns-supervisor` is 603664 bytes; a native ARMv7 binary of that name is a documented project component, but its on-router magic/identity still needs confirmation. The dated scripts are historical-looking copies, **not yet proof they are inactive**.

Public `router/scripts/personal-cloud-rsync` strictly allows rsync server commands targeting `/tmp/mnt/ROUTER_DATA/RouterCloud/`, **not the mount root itself**; `docs/personal-cloud-sync.md` provisions that child with `0700`. The live destination mode and live wrapper compatibility are pending. This explains why the one same-line grep match must not be classified as a confirmed direct mount-root write.

**Separate privileged-hook integrity concern:** operator observed JFFS `/jffs/scripts/services-start` mode 0755 owned by UID:GID 1000:1000, unlike the root-owned managed copy. Public `scripts/install.sh` generates its live managed hook using redirection to an existing path and applies `chmod 0755`, but no explicit `chown 0:0` in the `install_hook` path. That may preserve a pre-existing non-root owner; provenance is unproven. Firmware hook execution as root makes owner-write a possible integrity boundary, requiring separate remediation planning, **not an unreviewed live chown**. Verify marker/content equivalence, parent directory and account privileges first.

Next gate: safely inspect only directory mode/owner, wrapper marker, hook mode/owner, and ELF header classification without printing source, credentials or script contents. The root-mode `0755` compatibility gate remains REVIEW, production approval withheld.

[Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6187927310).

## 2026-10-15 — final on-router writer preflight

Reported RouterCloud rsync target exists in the expected child directory under ROUTER_DATA, owner root, mode 0700. Live JFFS forced-command wrapper is root-owned 0755 and the destination-reference and shell-syntax checks passed. This is favorable for root-mode 0755 compatibility but does not replace a run-as-identity check.

Active JFFS services-start hook parses but is owned by UID/GID 1000 and mode 0755; the managed-hook marker is absent. This is a distinct potential privileged-script integrity risk, requiring separate origin/account/contents and service-execution review before changes. The deployed DNS supervisor type-check returned REVIEW for an ambiguous file-or-tool availability gate, not proof of binary corruption. Do not run/chown/rewrite either artifact. No production changes.

Next read-only tests should compare the active hook with the managed bin without printing contents or hashes, check UID 1000 account mapping and parent ownership, and distinguish the DNS supervisor format-check failure causes. Remain in draft and hold production activation.

## 2026-10-15 — hook owner and missing inspection tools

Final router diagnostic isolated the unresolved conditions: live `/jffs/scripts/services-start` is a regular 0755 file owned by numeric UID:GID 1000:1000, while parent `/jffs/scripts` is 0755 root:root. UID 1000 has no matching `/etc/passwd` entry, but numeric-UID processes can still have permission to write their own files. Shell syntax PASS; expected managed-hook marker absent, so assume a custom/unmanaged hook unless provenance establishes otherwise. Direct comparison to managed `bin/services-start` was unavailable in the previous combined gate because `cmp` was missing or the peer was absent. No live ownership change is justified without further tests and a separate recovery plan.

The DNS supervisor is a regular 603664-byte, root-owned mode 0755 file. ELF header was not inspected because `head`, `od`, `dd`, and `hexdump` were unavailable in this restricted shell; that does NOT establish binary corruption. Public `scripts/install.sh` pins the packaged supervisor SHA-256 to `26f3615a99448469718f682bde6960e27e30b9466ecfc427c7e392c317103740` and supports the standalone `/bin/busybox sha256sum` applet for portable verification. Next read-only gate should verify the pinned hash without dumping file bytes, check the managed hook's existence, compare script hashes only (difference may be expected because the managed firmware hook is a wrapper), and count running UID 1000 process identities without printing process arguments. No production changes.

[Issue evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6188077727).

## 2026-10-15 — hash tool unavailable / uid 1000 runtime snapshot

Read-only router result: `HASH_PROVIDER=UNAVAILABLE` in the current shell, therefore `SUPERVISOR_SHA256=UNAVAILABLE` and `SCRIPT_HASH_COMPARISON=UNAVAILABLE`; this is a tooling limitation, not a hash mismatch. Managed `/jffs/addons/asus-edge/bin/services-start` exists with mode `0755` and owner `root:root`. The active `/jffs/scripts/services-start` remains mode `0755` and UID:GID `1000:1000`, and the managed marker was previously absent. Of 148 running processes successfully sampled, zero matched numeric real/effective UID 1000. An unmapped UID and zero observed processes do **not** eliminate the potential root-executed-hook ownership risk.

**Next diagnostic only:** inspect configured PATH presence and fixed absolute locations for preexisting hash utilities, then verify expected supervisor SHA and compare files without emitting digests if an available utility is found. Never install packages, execute hooks, change ownership or restart services merely to recover this diagnostic. The case remains **REVIEW**, with production HOLD.

[Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6188148121).

## 2026-10-15 — off-router supervisor SHA pin verified

The operator reported `SUPERVISOR_SHA256=PASS` from a read-only SSH byte stream of the live `edge-dns-supervisor` to Fedora, hashed locally against the installer-pinned SHA-256. This resolves the prior hash-tool-availability ambiguity and confirms binary identity against the repository artifact. The operator supplied **only** this result; `HOOK_VS_MANAGED` is **not yet reported** and remains UNKNOWN. No router or local file changes were made as part of this verification. Draft PR #245 remains uninstalled and on hold.

[Issue #235 result](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6188229976).

## 2026-10-15 — confirmed live services-start hash divergence

Operator completed a corrected read-only Fedora/off-router SHA-256 comparison with SSH stdin disabled. `HOOK_VS_MANAGED=DIFFERENT` and `ISSUE235_HASH_COMPARISON_V2_COMPLETE` were reported. The live JFFS `services-start` is **not** byte-identical to the root-owned managed script in ASUS Edge bin. This is not evidence of compromise or a deployment regression by itself: the JFFS hook may contain independent custom/legacy startup logic. The live JFFS hook still belongs to UID:GID 1000:1000 (mode 0755) and lacked the generated managed-hook marker in the previous inspection, so do **not** overwrite it with the managed bin or change ownership without a separate dependency/rollback review. The earlier `SUPERVISOR_SHA256=PASS` independently confirmed the installed native DNS supervisor matches the pinned repository binary.

**Next read-only gate:** classify structural invocation markers in the live JFFS hook without printing its contents or modifying it, and determine whether the hook invokes the managed file, Entware/AMTM or other recovery logic. Preserve all existing live startup behavior and the post-mount swap-before-AMTM ordering. No live operations or production authorization; Draft PR #245 remains open.

[Issue #235 result](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6188289185).

## 2026-10-15 — private services-start backup and static references

Operator made a private read-only SSH export of the existing live JFFS `services-start` to the Fedora workstation. The archive directory (0700), original-script copy (0600), manifest (0600), original source and metadata matches, SHA-256 parity and `sh -n` all passed. No private shell source or digest was uploaded or printed, no live files were changed.

A local, non-executing structural audit of that verified copy counted matches in non-comment lines: ASUS Edge bin 3, managed services-start absolute path 0, Entware startup 1, Tailscale 32, DNS 15, post-mount 1, swapon 0, direct literal SSD path 0, explicit privilege-change keywords 0. Counts indicate potential independent network startup/recovery behavior but do not establish actual execution paths, dynamically generated paths, or whether services are launched directly. Combined with missing managed marker and hash divergence, this confirms the two scripts cannot be assumed interchangeable.

**Gate:** retain the live custom hook unmodified and protect its off-router original; root-owned managed script cannot be substituted. The distinct UID 1000 hook ownership concern needs a separate safety and rollback decision. Absence of literal direct SSD paths favors the narrow SSD mount-root repair but does not constitute proof of complete write compatibility; inspect active configured writers and private UUID storage before any deployment. PR #245 remains DRAFT and uninstalled. Post-mount swap-before-AMTM order is not to be disturbed.

[Issue #235 audit](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6188501055).

## 2026-10-15 — early-boot tool resolution compatibility BLOCKER

Operator's native read-only Asuswrt shell inventory after the earlier UUID staging preflight stopped: `stat` is executable at `/opt/bin/stat` only (Entware), whereas `awk` exists at `/usr/bin/awk`, `blkid` at `/sbin/blkid`, and `chmod` at `/bin/chmod`. Available `/bin/busybox` implements `awk`, `blkid`, `chmod`, but **not** the `stat` applet. The restricted early boot PATH embedded by the draft helper excludes /opt, and a direct `stat` execution under that PATH returned REVIEW. In this observed firmware shell, `command -v` returned MISSING for all four commands even though direct tools may work; therefore the helper's `command -v blkid` guard is not reliable without a separate actual-execution test. Do not patch these gates by adding Entware to the early-boot PATH.

The separate read-only UUID diagnostics confirmed exactly one ext4 block device for each managed mount, mode `0777` owner root for both, `blkid` return code zero, a single valid tagged UUID for each, and distinct identifiers; no UUID values were shown. **No private UUID staging files were created.** Before editing the draft helper, investigate a firmware-native ownership/mode representation, e.g. explicit BusyBox `ls -ldn` in a read-only probe, and validate its exact output parsing. Preserve root-only ownership and reject every unexpected format. No live changes, no package installs, no helper activation or reboots.

[Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6188825461).

## 2026-10-15 — firmware-native metadata parser staged (draft only)

A direct read-only test on the live ASUS under its constrained firmware PATH returned `SYSTEM_AWK_EXEC=PASS`, `BUSYBOX_NUMERIC_LS=PASS`, `SYSTEM_BLKID_EXECUTABLE=PASS`, `SYSTEM_CHMOD_EXECUTABLE=PASS`, and on **both** ext4 SSD mount roots `LS_OWNER_MODE=PASS`, `LS_VS_STAT=PASS`, `NATIVE_BLKID_EXEC=PASS`. The cross-check used Entware `stat` only to compare existing metadata on an already-booted router; no production mutations occurred. An earlier inventory found no `stat` applet in firmware BusyBox and the previous helper's PATH excluded `/opt/bin`.

To remove this premature-boot dependency in **Draft PR #245 only**, the candidate now uses `/bin/busybox ls -ldn` with a fail-closed parser accepting only `drwxrwxrwx` (0777) or `drwxr-xr-x` (0755) and the expected numeric owner/group. It invokes `/usr/bin/awk`, `/sbin/blkid` and `/bin/chmod` at absolute firmware paths and no longer trusts shell `command -v` to discover blkid. Mode and ownership are checked again immediately before a permitted 0777-to-0755 change and verified afterward. Negative and composed swap-before-AMTM fixture tests were updated to mock the firmware-shaped ls output and native absolute executables. No Entware PATH is added. The helper is still not installed or activated; the live JFFS hooks, UUID paths and both SSD root modes are unmodified.

**Acceptance limitation:** existing read-only on-router validation does not prove earliest-boot timing, post-mount reentry, race safety or actual production behavior. The parser recognizes only the observed mode shapes and fails closed on unexpected formats. CI for the new branch commits and operator-run isolated tests must pass before considering private UUID staging and separate live approval. The separate UID1000-owned `services-start` concern remains unresolved and must not be modified as part of this helper change.

## 2026-10-15 — independent private UUID staging audit PASS

Operator completed both local Fedora UUID stages with no router writes. Initial V2 staging confirmed independent ext4 block-device mount identities and stable canonical UUID values by repeated live read-only ASUS queries, then privately wrote two per-volume UUID files and a local SHA-256 manifest. A separate offline follow-up audit reported `STAGING_DIRECTORY=PASS`, `EXPECTED_FILES_ONLY=PASS`, both file privacy/format checks PASS, `UUIDS_DISTINCT=PASS`, manifest privacy and `MANIFEST_INTEGRITY=PASS`, and `ISSUE235_PRIVATE_UUID_AUDIT_COMPLETE`. The stage directory has local mode 0700; both UUID files and manifest mode 0600. No contents, device IDs or digests were printed or put in Git; no router connection occurred during the second audit. **Local private UUID preparation is complete.**

This is not a live JFFS install or production acceptance. Router private directory root:root 0700, file owner root:root 0600, helper delivery/integrity, existing post-mount exact byte provenance and insertion order, consumer compatibility, and restoration gating still need formal signoff. Planned integration must always keep swap activation before AMTM and never abort unrelated mounts. The separate UID1000-owned custom `services-start` hook must remain untouched. PR #245 remains DRAFT, deployment/reboot withheld pending explicit operator approval.

[Issue #235 private staging result](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6189124550).

## 2026-10-15 — saved post-mount candidate offline structural preflight PASS

Operator reported a Fedora-only offline audit of the privately saved live `post-mount` original and candidate: both private regular files (0600) and `sh -n` PASS; the original still matches SHA-256 `8625bee2558d046e789e9ea871ed5d7758be42c39548ca7f6a63757704a02b66`; saved candidate passes prefix/suffix byte equality against the original with a single nonempty insertion after line 16. The insertion contains expected issue #235 helper and private UUID file identifiers; original swap logic was found before insertion and AMTM logic after. `OFFLINE_POSTMOUNT_COMPOSITION=PASS`; no live router access or file mutations occurred.

**Important scope:** this structural test does not prove the inserted bytes match the **current** PR #245 snippet exactly, nor that current live JFFS source remains at the saved baseline, nor that early-boot integration functions. Next independent gate: compare the inserted slice with the publicly version-pinned snippet without printing original JFFS text or private UUIDs; confirm current live hook baseline read-only and verify the rollback/consumer contract. The private UUID staging V2 and independent manifest audit have passed separately. Production deployment and reboot remain on HOLD pending explicit operator approval; `services-start` is unchanged and its UID1000 owner concern separate.

[Issue #235 result](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6189190119).

## 2026-10-15 — pinned snippet parity boundary newline only (HOLD)

Operator's Fedora-only, commit-pinned check of the existing private candidate versus `router/scripts/issue235-postmount-integration.snippet` found `ORIGINAL_SHA256=PASS`, `ORIGINAL_LAYOUT=PASS`, `ONLY_INSERTION=PASS`, `PINNED_SNIPPET_FETCH=PASS`, but `INSERTION_EXACT=REVIEW` with `BOUNDARY_NEWLINE_ONLY=YES`. The insertion's inner bytes equal the pinned public snippet after stripping CR/LF only at both ends; **the existing saved candidate is not byte-for-byte identical** and remains blocked. No private hook contents, UUIDs, or hashes were printed, and no files were changed during the check.

Next offline-only gate: preserve both existing private original and old candidate, then create a distinct 0700 staging directory and new 0600 candidate using exactly `original_prefix_after_line_16 + fetched_pinned_snippet + original_suffix`; require fixed original SHA, old candidate normalized-body parity, new exact inserted-byte parity, shell syntax PASS, and preserved swap-before-AMTM order. Never normalize the original hook or source snippet in place. Afterward separately revalidate current live post-mount SHA using read-only SSH and formal startup/rollback conditions before requesting explicit authorization. `DEPLOYMENT_GATE=HOLD`; Draft PR #245 uninstalled.

[Issue #235 result](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6189258199).

## 2026-10-15 — exact pinned insertion rebuilt as a separate private candidate

Operator's Fedora-only V2 run resolved the earlier CR/LF boundary discrepancy by creating a **separate** private candidate from the byte-preserved baseline `post-mount` plus the exact integration snippet pinned to commit `7e1c23ac061bd7bd7845013432dbe71300154784`. Reports: baseline SHA-256, original layout, prior candidate insertion-only, expected old boundary-newline difference, pinned snippet fetch, **exact inserted bytes**, original swap/AMTM section preservation, private stage/candidate permissions (0700/0600), candidate on-disk integrity, and `sh -n` all **PASS**. Both the saved original and previous candidate remained unchanged, no router connection occurred, and no private source/UUID/hash values were revealed. The new private candidate is saved locally on Fedora, not in Git.

The exact-byte **offline composition gate is closed PASS**, replacing the previous candidate's parity REVIEW; the *production* gate remains HOLD. Next revalidate the current live `/jffs/scripts/post-mount` owner/mode and baseline SHA via read-only SSH (no local source output), recheck service/SSD writer and recovery prerequisites, and seek explicit authorization separately for production staging, activation and later controlled reboot. Do not deploy helper or UUID files, edit JFFS hooks, chmod mount roots or alter the unrelated UID1000-owned `services-start` during this stage.

[Issue #235 result](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6189333869).

## 2026-10-15 — live JFFS post-mount baseline reconfirmed PASS

Operator completed a live-router read-only revalidation through pinned SSH after creating the separate exact offline Fedora candidate. The actual `/jffs/scripts/post-mount` is a regular non-symlink file, `0755` owner `root:root` (`LIVE_HOOK_MODE_OWNER=PASS`). Streaming the live file to Fedora confirmed the original SHA-256 `8625bee2558d046e789e9ea871ed5d7758be42c39548ca7f6a63757704a02b66` (`LIVE_HOOK_BASELINE_SHA256=PASS`), `/bin/sh -n` PASS and second stream hash unchanged (`LIVE_HOOK_STABLE=PASS`). Aggregate `LIVE_POSTMOUNT_BASELINE=PASS`; no contents/hashes disclosed, no live script execution, files modified or services restarted.

The **offline candidate and live original now refer to the same baseline**, and the privately rebuilt candidate's inserted bytes match the pinned public snippet. This closes the offline source freshness gate, **not production acceptance**. Open gates: formal SSD-mount consumer/writer 0755 compatibility and exception decision, predeployment recovery and UID/root ownership plan for two JFFS UUID files and helper, explicit operator consent for limited live staging/activation, then independent approval for reboot persistence tests. Preserve swap-before-AMTM and the unrelated UID1000-owned custom `services-start`. Draft PR #245 unmerged and helper not installed.

[Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6189380307).

## 2026-10-15 — predeployment SSD runtime baseline confirmed

Operator's **read-only** runtime preflight confirmed single valid live ext4 mount mapping for both ROUTER_DATA and ENTWARE and both root-owned mount roots still at `0777`. Their protected children have the expected owner/mode: `ROUTER_DATA/RouterCloud` is `0700 root:root` and `ENTWARE/entware` is `0755 root:root`. `/proc/swaps` contains **one active swap entry for each managed SSD volume**, with no swap alteration, chmod, restart, or device/UUID disclosure. `ISSUE235_RUNTIME_COMPATIBILITY_COMPLETE` completed with PASS for mount and directory predicates. This is **baseline health**, not a simulated or live test after root-mode hardening.

Predeployment gates already PASS: locally staged UUID identity and independent manifest validation; byte-exact offline post-mount integration with pinned snippet; verified live original `post-mount` baseline owner/sha/syntax; firmware-native helper CI. Still OPEN: acceptance for non-root and root-level writers when both mount roots become `0755`, repeatable production-JFFS deployment and restoration instructions with protected owner/modes, service/backup health, explicit operator activation approval and separate reboot permission. The three previously identified world-writable RouterCloud test/rollback subtrees are separate and not covered by the mount-root-only change. Do not modify custom `services-start` with UID 1000 ownership; keep swap-before-AMTM. **GO/NO-GO = HOLD.**

[Issue #235 runtime evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6189446891).

## 2026-10-15 — live service process UID snapshot

Operator ran an ASUS **read-only** `/proc` identity inventory with `ISSUE235_SERVICE_IDENTITY_COMPLETE`. Root/nonroot process counts: tailscaled 1/0; dnsmasq 1/1; unbound 0/1; syslog-ng 2/0; Dufs/RouterCloud 1/0. All unknown-UID counts zero. No arguments, private paths, files, permissions or services were modified or disclosed.

**Scope:** this proves only the process identity snapshot, not that all processes or periodic jobs can tolerate mount-root `0755`. In particular, verify the unprivileged dnsmasq and Unbound consumers have writable **descendant** directories and do not need to create entries directly beneath `ROUTER_DATA` or `ENTWARE` mount roots. A read-only FD inventory is supporting evidence at most, not proof of all possible future writes. Production mount-root mode remains `0777` and both SSD swap entries remain active. Production helper activation, custom JFFS hook edits and reboot continue to be blocked pending consumer and rollback acceptance plus explicit operator approval. Custom UID1000-owned `services-start` is out of scope.

[Issue #235 service identity evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6189514912).

## 2026-10-15 — nonroot descriptor snapshot for SSD resolvers

A read-only ASUS FD inventory (no file paths printed) found one nonroot dnsmasq and one nonroot Unbound process. Both processes had 0 FDs on either SSD mount root, 0 FDs at the first directory level of either SSD and 0 root-CWD matches. dnsmasq had 0 nested SSD FDs; Unbound had 1 nested FD; both had 0 unreadable FDs. No writes or service changes occurred. This narrows direct mount-root compatibility concerns but does not establish future write/create/rename usage; it also does not establish the access mode of Unbound's nested descriptor.

This snapshot does not satisfy the formal writer/rollback GO gate. Retain Draft PR #245, leave the existing live mount modes and helper untouched, and require separately authorized production staging and later reboot.

## 2026-10-15 — consolidated production GO/NO-GO checklist

A consolidated, audited [production GO/NO-GO and recovery decision](issue235-production-go-no-go-2026-10-15.md) now records the accepted read-only evidence and material open blockers. Key additional review point: the drafted post-mount snippet validates that a private expected-UUID file exists and is readable, but **does not itself check root:root/0600 ownership and permissions**. These private JFFS metadata requirements must be explicitly verified and enforced as a STOP gate before separate activation approval; do not assume local Fedora staging permissions imply correct later router ownership. The source-level review of `scripts/install.sh` also shows `install_hook` rewrites live `services-start` wrappers and only chmods, which would affect a separate custom UID1000-owned hook: **do not run the general installer for #235**. The narrow future deployment must be independently scoped and reversible. The current candidate, original backup, helper and UUID stage remain entirely offline; no new production router operation is authorized. Status: **NO-GO / HOLD**.

## 2026-10-15 — private JFFS metadata guard added to Draft snippet

The initial integration snippet checked UUID file existence, non-symlink and readability, but did **not** verify private owner/mode. The Draft PR #245 insertion is now fail-closed for the complete JFFS directory chain (`/jffs`, `/jffs/addons`, `/jffs/addons/asus-edge`, `bin` must be real, non-symlink, numeric owner/group `0:0`, mode `0755`), the private UUID directory (`0700 root:root`), the selected UUID file (`0600 root:root`, regular non-symlink), and helper (`0755 root:root`, regular non-symlink). It reads firmware-native metadata using `/bin/busybox ls -ldn` in a subshell so field splitting never overwrites the real hook's positional mount argument. This gate runs **before** reading the UUID or invoking the helper; absent/insecure metadata prints `ISSUE235_POSTMOUNT_REPAIR=NOT_READY`, does not run chmod, and returns to the existing startup flow. This does not replace separate trusted JFFS file delivery and integrity verification, nor eliminate time-of-check/time-of-use races.

The composed isolated test now models protected JFFS ancestors and adds invalid file/directory/helper permission and symlink cases. **IMPORTANT:** the earlier new private Fedora `post-mount-exact` candidate was byte-exact against the **previous** snippet. It is now **STALE** relative to this updated Draft PR revision. It must not be deployed. After CI and review, rebuild a new copy off-router from the unchanged verified original plus the newly pinned snippet, preserving swap-before-AMTM; do not modify any old candidate, original, encrypted backup or the live ASUS hook. The private UUID contents remain offline. Deployment is still **NO-GO/HOLD**.

See [the consolidated GO/NO-GO runbook](issue235-production-go-no-go-2026-10-15.md).

## 2026-10-15 — exact post-mount V3 built privately from guarded snippet

Operator created a **new, independent, Fedora-only private candidate V3** from the previously hash-verified original `post-mount` and the snippet pinned at Draft PR #245 commit `be191e1098a5145d58e38baceebf061190ce11a9`. The local staging script reported all PASS: original baseline SHA-256, private original and prior V2, pinned Git blob identity and metadata guard markers, exact inserted snippet bytes, original swap-before-AMTM sections, new candidate/manifest local 0700/0600 privacy and byte integrity, `/bin/sh -n`, and original/V2 left unchanged. `ISSUE235_CANDIDATE_V3=PASS`, no SSH/router connection, no UUID values disclosed, no ASUS modification. The previous V2 is obsolete and must not be deployed. Current CI run `38719831711` on the pinned source commit completed SUCCESS.

**Not yet accepted:** a separate independent integrity/manifest audit of V3 and an isolated atomic-update/rollback simulation; real JFFS restoration and boot/hotplug remain untested, with independent approvals required. Stage V3 stays private to Fedora and **NO-GO/HOLD** still applies.

## 2026-10-15 — independent V3 integrity and isolated atomic rollback PASS

Operator completed the separate, Fedora-only `ISSUE235 / V3 INTEGRITY AND ATOMIC ROLLBACK LAB` with every reported gate PASS: the private source, new stage and expected files; original baseline hash; candidate shell syntax; immutable pinned snippet Git blob identity; byte-exact full V3 composition; independent manifest bytes; isolated same-directory replacement of an original fixture by the candidate and replacement by the original; restored original hash/0755/syntax; no stale temporary files; and source original/V3 unchanged. Aggregate `V3_INDEPENDENT_INTEGRITY=PASS`, `ATOMIC_REPLACE_ROLLBACK_LAB=PASS`, `ROUTER_CONNECTION=NO`, `ASUS_PRODUCTION_MODIFIED=NO`. These results supersede the previous 'independent V3 audit pending' note above. The signed-off fixture simulates an atomic rename on Fedora, **not a JFFS transaction on ASUS**; no live root:root file delivery, helper deployment, in-boot operation or rollback was attempted.

A controlled, explicitly non-authorizing [JFFS stage/activation/rollback runbook](issue235-jffs-staging-activation-rollback-runbook-draft.md) now separates nonmutating preflight, root-owned private payload staging, separately approved hook activation, recovery and later independently approved reboot. The operator's exact V3 source remains a private Fedora artifact. **Production GO/NO-GO remains HOLD**, notably pending direct-mount-root writer risk acceptance and scoped JFFS recovery approval.

[Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6190043448).

## 2026-10-15 — final read-only ASUS JFFS/SSD preflight PASS

Operator ran `ISSUE235 / PRODUCTION READ-ONLY PREFLIGHT` against the already-booted production ASUS after V3 offline integrity and isolated rollback had passed. Exact numeric metadata checks PASS for `/jffs`, `/jffs/scripts`, `/jffs/addons`, `/jffs/addons/asus-edge` and `bin`: all required 0755 root:root, no symlink directories. Available JFFS capacity exceeded the selected **8 MiB** acceptance threshold. Proposed private JFFS UUID directory and mode helper each reported **NOT_INSTALLED**. Active original `post-mount` shell syntax PASS. The two expected ext4 mounts each had root:root 0777 baseline and exactly one active swap entry. No private content/UUIDs printed, files, permissions, swap or services changed, and no reboot.

This establishes a **current read-only predeployment baseline**, not that JFFS staging is safe or currently authorized. The test did **not** rehash the live hook or demonstrate independent wired recovery access, backup decryption availability, direct first-level writer compatibility with 0755, live JFFS atomic replacement or an actual reboot. Continue `DEPLOYMENT_GATE=HOLD`; next confirm local wired/WebUI recovery and complete the risk acceptance and separately authorized staging decision. [Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6190162812).

## 2026-10-15 — read-only ASUS cron and startup script SSD writer inventory

Operator ran a strictly read-only `ISSUE235 / PERIODIC SSD WRITER AUDIT` after documenting independent wired recovery and available encrypted Verbatim backup credentials. Live ASUS `cru l` returned `CRON_ACCESS=PASS`, **3 scheduled entries**, **0 literal references** to `ROUTER_DATA` or `ENTWARE` mount paths, **1 DNS Guard** entry and **0 literal logrotate** entries. The sampled /jffs/scripts and /opt/etc/init.d S* sources yielded **18 readable regular scripts**, **2 files containing literal SSD mount paths**, **0 write-command-on-same-line heuristic matches**, no symlink skips or read errors. No script sources, arguments, UUIDs or private paths were printed, and no files, services, swap, cron or mount modes changed.

**Interpretation:** the sampled tasks show no *obvious literal same-line SSD-root writer*, not proof against transient tasks, built-up paths, indirect writers, external scripts or firmware-created root entries. The two referring scripts are yet to be safely classified, and absence of an ASUS-cron logrotate entry does not establish a log rotation problem. Writer gate remains REVIEW, Draft PR #245 uninstalled and production `DEPLOYMENT_GATE=HOLD`. Next evidence should classify the two scripts using only aggregate path/reference semantics, with no live execution or disclosure. [Issue #235 evidence](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235#issuecomment-6190403085).
