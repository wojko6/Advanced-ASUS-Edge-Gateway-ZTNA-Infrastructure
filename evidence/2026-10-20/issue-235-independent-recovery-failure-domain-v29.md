# Issue #235 — V2.9 independent recovery failure-domain review (2026-10-20)

> **Status:** documentation/design + nonroot Fedora metadata-only inventory, **not an installation or actual recovery**. Operator V2.9 replay: **9/9 operator self-tests PASS + metadata-only inventory PASS**, both primary candidates **SAME_ST_DEV**. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Accepted baseline and missing guarantee

- [V2.8](issue-235-recovery-copy-separation-v28.md) independently confirmed the actual private Fedora **full** `services-start` and DNS Guard copies with `BYTES_OWNER_MODE_PASS_AT_READ_TIME`, `RECOVERY_COPY_READONLY_CHECK=PASS_PRIMARY_SNAPSHOTS_ONLY`, exit 0. These are two **primary** backup files, not evidence of a second off-host copy. File bytes and private paths remain unpublished.
- No independent recovery after total loss of Fedora was demonstrated; optional secondary paths were **NOT_PROVIDED** and V2.8 filesystem pair topology `NOT_ASSESSED`. A separate physical disk still inside the Fedora machine would not alone prove survival of total host loss.
- [RouterCloud backup design](../../docs/routercloud-versioned-backup.md) and its [actual wrapper](../../scripts/routercloud-backup.sh) show encrypted Restic snapshots of the **RouterCloud staging directory** by default, not a demonstrated inclusion of the two private Issue #235 backup directories. Do not assert inclusion without inspecting an actual read-only snapshot. The separately managed Fedora Recovery workflow also has no **verified #235 file-level coverage** in this checkpoint, and must not be changed.
- The [V2.7 independent approval design](../../docs/operations/issue235-two-script-offline-approval-authority-v27-2026-10-20.md) requires a separately protected **operator-approved authority**, distinct from the source files and any same-UID-writable manifest or candidate. Recovering copies does not confer execution permission.

## V2.9 local metadata-only inventory (candidate, Fedora)

Tool: `issue235_failure_domain_inventory_v29.py`; exact source SHA-256: `9eabaf8481d1dd4f5477a9641906ca781c8002dd66006d81f896483355ec8bad`.

- Local deterministic **9/9 self-tests PASS**. A separate disposable-file fixture correctly located both roles with `SEARCH_ERRORS=0`, reported their `SAME_ST_DEV` relation, and skipped symlink directory decoys. No production paths, router or backup source bytes were involved.
- Only scans **direct child directories** of `$HOME`, `$HOME/Pobrane`, `$HOME/Projekty` with preapproved prefixes `issue235-hook-backup-*` and `issue235-dns-guard-backup-*`; direct regular child names `services-start` and `dns-guard`. It will **not** search broadly or decide among multiple candidates. In case of none/multiple, returns HOLD, not an arbitrary selection.
- `PRIMARY_COPY_DEVICE_RELATION=SAME_ST_DEV` shows one local `stat` filesystem device ID at read time. `DIFFERENT_ST_DEV_NOT_PHYSICAL_INDEPENDENCE` **never** proves different hardware/host/offline media. Btrfs subvolumes, bind mounts and layered storage make simple filesystem IDs insufficient.
- Does not read file bytes (V2.8 already covers integrity), extract paths, expose device names/UUIDs, inspect Restic keys or repository, run `sudo`, `subprocess`, SSH, modify files, mount media or touch ASUS.
- Operator **Fedora PASS_METADATA_ONLY_INDEPENDENCE_NOT_PROVEN**; this verifies only local device-ID classification and candidate discovery, never independent storage acceptance.

Fedora only (nonroot), after source checksum verification:

```bash
cd ~/Pobrane
printf '%s  %s\n' \
  '9eabaf8481d1dd4f5477a9641906ca781c8002dd66006d81f896483355ec8bad' \
  'issue235_failure_domain_inventory_v29.py' | sha256sum -c - &&
python3 -B issue235_failure_domain_inventory_v29.py --self-test &&
python3 -B issue235_failure_domain_inventory_v29.py --audit
echo "V29_EXIT_CODE=$?"
```

## Independent operator Fedora replay — V2.9 accepted as metadata-only (2026-10-20)

The operator checked the source SHA-256 (`sha256sum -c` yielded `DOBRZE`) and independently ran the fixed-path source in the ordinary Fedora user session. Sanitized results:

```text
SELFTESTS=9/9
SELFTEST_RESULT=PASS_BOUNDED_METADATA_MODEL_ONLY
SEARCH_SCOPE=HOME_POBRANE_PROJEKTY_FIXED_PATTERNS_ONLY
SEARCH_ERRORS_PRESENT=NO
HOOK_LOCATED=ONE_REGULAR_NONSYMLINK_CANDIDATE
GUARD_LOCATED=ONE_REGULAR_NONSYMLINK_CANDIDATE
PRIMARY_COPY_DEVICE_RELATION=SAME_ST_DEV
FILES_CONTENT_READ=NO
FILE_PATHS_OR_VOLUME_IDENTIFIERS_PRINTED=NO
RESTIC_REPOSITORY_OPENED=NO
RESTIC_ISSUE235_SNAPSHOT_INCLUSION=NOT_VERIFIED
FEDORA_RECOVERY_ISSUE235_SNAPSHOT_INCLUSION=NOT_VERIFIED
EXTERNAL_OFF_HOST_COPY=NOT_VERIFIED
INDEPENDENT_RECOVERY_ACCESS_AFTER_FEDORA_LOSS=NOT_PROVEN
APPROVAL_STORE_INDEPENDENCE=NOT_PROVEN
PHYSICAL_FAILURE_DOMAIN=NOT_PROVEN_FROM_ST_DEV
ASUS_CONTACTED=NO
FILES_MODIFIED=NO
CRON_MODIFIED=NO
PRIVILEGED_EXECUTION_TRUST_GATE=HOLD
DEPLOYMENT_GATE=HOLD
V29_INVENTORY_RESULT=PASS_METADATA_ONLY_INDEPENDENCE_NOT_PROVEN
V29_EXIT_CODE=0
```

**Interpretation:** the two uniquely located local backup candidates share the same kernel `st_dev` filesystem ID at inspection. This does **not** imply same inode, and the tool did not assess physical drives or backup redundancy. The hash/DAC proof from V2.8 remains a **separate** at-read-time acceptance; V2.9 did not read or rehash either file. No production scripts or existing backups were changed.

**Completed:** `V29_LOCAL_DISCOVERY=PASS`, `V29_PRIMARY_FILESYSTEM_RELATION=SAME_ST_DEV`. **Outstanding:** external/off-host backup evidence, independent access to decryption material and restore tooling after Fedora loss, and disposable restore of both scripts. In particular, a second NVMe in the *same computer* can be a valuable disk-failure tier but is **not an off-host disaster-recovery tier**.

## Recovery dependency and acceptance table

| Requirement after total Fedora loss | Status | Evidence needed (future, separately approved) |
| --- | --- | --- |
| Exact source bytes of both scripts | **V2.8 primary copies PASS at read time** | Confirm separate independent offline copy version and integrity |
| Off-host/offline storage | **NOT PROVEN** | Physically separate host or disconnected encrypted medium with known custody and update cadence |
| Restic snapshot inclusion of these exact files | **NOT PROVEN** | Read-only, scope-specific listing of an existing snapshot; RouterCloud staging alone does not show coverage |
| Recovery without local Fedora | **NOT PROVEN** | Independent device, compatible software, available recovery instructions and credentials held separately |
| Safe restore proof | **NOT PROVEN** | Restore both scripts to disposable storage, verify exact SHA and metadata; never into live JFFS in the test |
| Operator-approved change authorization | **NOT ISSUED** | Separate approval/root-of-trust and launcher protected from same-UID candidate writes; no PR #245 approval reuse |
| Publication on GNUton JFFS2 | **NOT IMPLEMENTED** | Separate root publisher, old FD/process writer exclusion, crash recovery, DNS/boot continuity and explicit apply GO |

## Decision and next action

**Next linked design gate:** [V2.10 full-host-loss recovery options](../../docs/operations/issue235-independent-script-recovery-options-v210-2026-10-20.md) compares a normally disconnected encrypted medium with independently administered off-host storage; existing local same-host backups are supporting tiers only. No copy, Restic change, restore or production action has been performed.



**Do not create a new Restic profile, change retention/passwords, enable a timer, move private backup copies, alter Fedora Recovery, or install/change any ASUS/SSD/RouterCloud service.** The next decision is *where* an independent off-host or disconnected recoverable copy and recovery credentials can be kept, and how to test a disposable restore without depending on the lost Fedora. Do not count distinct `st_dev` or a synthetic V2.9 PASS as proof of this. Separate operator authorization required for any copy or restore execution.

```text
V28_PRIMARY_BACKUPS=PASS_AT_READ_TIME
V29_OPERATOR_INVENTORY=PASS_METADATA_ONLY_INDEPENDENCE_NOT_PROVEN
V29_PHYSICAL_FAILURE_DOMAIN=NOT_PROVEN
V29_RESTIC_ISSUE235_INCLUSION=NOT_VERIFIED
V29_OFF_HOST_RECOVERY=NOT_TESTED
V27_APPROVAL_AUTHORITY=NOT_ISSUED
PRIVILEGED_EXECUTION_TRUST_GATE=HOLD
DEPLOYMENT_GATE=HOLD
```
