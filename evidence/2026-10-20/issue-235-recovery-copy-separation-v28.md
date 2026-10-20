# Issue #235 — V2.8 off-router recovery copy and failure-domain audit (2026-10-20)

> **Status:** Fedora operator READ-ONLY PREFLIGHT / isolated local synthetic suite **18/18 PASS**; operator primary-backup audit **PASS_PRIMARY_SNAPSHOTS_ONLY** in the second replay; independent recovery and failure-domain still unproven. Not a trusted publisher, restore test or independent-media certificate. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.

## Why this is the next gate

Existing read-only evidence proves a privately retained Fedora byte copy of the current **full** `/jffs/scripts/services-start` and of `/jffs/addons/asus-edge/bin/dns-guard` (each at a point in time; the hook backup and DNS Guard backup passed their own source integrity tests). It **does not** prove an independently protected second copy, a separate storage failure domain, actual recoverability without Fedora, or independent storage of the proposed V2.7 operator approval.

The [V2.7 design](../../docs/operations/issue235-two-script-offline-approval-authority-v27-2026-10-20.md) explicitly forbids treating a manifest and its matching checksum stored in the same user-writable location as independent authority. Therefore recovery-copy evidence must be **separate from approval authority evidence**. A matching backup hash is data integrity only; not proof of operator authorization or mount/boot continuity.

## Actual source byte identities and fixed targets

| Role | Fixed existing script | Historical reviewed SHA-256 of exact script bytes |
| --- | --- | --- |
| `HOOK` | **Full**, existing firmware `/jffs/scripts/services-start` | `026b3c18a950abd70ec86046b04c0015832289ec3ec886bcf4d25298aebf5616` |
| `GUARD` | Existing `/jffs/addons/asus-edge/bin/dns-guard` | `ecd44c59532073d33290b8eb500144e12ecfb4537542bc58a4c75be8753ab0db` |

The audited inputs are **copies stored on Fedora**, selected locally by the operator. No router-side source path is opened and no production secrets or private backup paths are part of this report. Historical pins are **not** a current live attestation; a future publication requires separately authenticated fresh source bytes.

## V2.8 tool and local evidence

- `issue235_recovery_separation_audit_v28.py`
- SHA-256 of isolated source: `7541de5439a39d332d10da1b701b6cb14676d4e76b12d5b7f881883b73c440d5`
- Run in disposable nonroot assistant environment: `--self-test` **18/18 PASS**. Synthetic private-copy tests include known matching bytes, mismatched SHA, file writable permissions, symlink and hardlink denial, writable ancestor denial, ambiguous path denial, and distinct inode / filesystem classification. The suite's `PASS` establishes only the behavior of this rootless fixture; a later **independent Fedora audit of the two actual primary copies PASSED**; see the replay evidence below.
- `--audit` works **only** in the local operator's nonroot terminal. It reads **two required** local primary backups, with **two optional** secondary-copy paths, entered via hidden interactive prompts (no path-valued command-line arguments or network). A missing or inaccessible required primary copy ends in `HOLD`. Secondary copies may be absent; the checker honestly reports `NOT_ASSESSED`.
- Fixed scoped file checks: open directory/file by descriptor with `O_NOFOLLOW`; reject ambiguous paths and group/world writable ancestors, symlinks, nonregular files, hardlinks, unexpected owner and group/other-readable modes; compare stable `fstat` identity before and after bounded checksum and fresh name lookup; exact historical hash, size <= 1 MiB.
- The tool **does not run commands**, use `sudo`, perform SSH/network access, query the router, inspect any private approval/key store, modify copies or mount disks, perform file restore, change Cron/services/JFFS, or publish any new script.
- Output is **role-based**, without input paths, user names, mount device identifiers, source code bytes or hashes of any private records. Running interactively with private backup paths also reduces shell-history/process-argument disclosure.

## Reading the resulting labels

| Output | Meaning | **Not** implied |
| --- | --- | --- |
| `PRIMARY_HOOK/PRIMARY_GUARD=BYTES_OWNER_MODE_PASS_AT_READ_TIME` | Each named existing Fedora file matched the reviewed source SHA and passed basic metadata checks at one instant | It is immutable, independently protected from same-UID tampering, or recoverable after loss of Fedora |
| `SECONDARY_*=NOT_PROVIDED` | No secondary loose-file copy was audited | No other backup exists (could be in Restic/other format) |
| `FS_TOPOLOGY_*=SAME_INODE` | Same opened filesystem object at the two user-selected paths | Any separate copy |
| `FS_TOPOLOGY_*=SAME_FILESYSTEM` | Distinct inodes reside in the same filesystem | Separate filesystem failure domain |
| `FS_TOPOLOGY_*=DIFFERENT_FILESYSTEM_ONLY` | Different device IDs observed through local `stat` | Separate physical disks, controllers, host, network, off-site custody, or actual independent failure domain |
| `ENCRYPTED_RESTIC_RESTORE_AND_OFFLINE_MEDIA=NOT_TESTED` | Restic archives / removable media / offline restore outside this loose-file checker | Failure or success of those independent recovery mechanisms |

`INDEPENDENT_FAILURE_DOMAIN=NOT_PROVEN_BY_LOCAL_PATH_CHECKS` remains **permanently honest**, even when two files are on different filesystems. An actual independent recovery acceptance would require further evidence: storage topology, independent power/controller/host or offline custody, external-access credentials held separately from failed Fedora, protected and versioned backup/approval copies, and a separately authorized restore rehearsal on disposable storage.

## Operator Fedora command (no sudo)

```bash
cd ~/Pobrane
printf '%s  %s\n' \
  '7541de5439a39d332d10da1b701b6cb14676d4e76b12d5b7f881883b73c440d5' \
  'issue235_recovery_separation_audit_v28.py' | sha256sum -c - && \
python3 -B issue235_recovery_separation_audit_v28.py --self-test && \
python3 -B issue235_recovery_separation_audit_v28.py --audit
echo "V28_EXIT_CODE=$?"
```

On `--audit`, enter the primary full-hook backup location, primary DNS Guard backup location, and optionally one further separately held *loose-file* backup per role. **Do not paste private paths into the chat/repository.** Hidden prompts are optional for secondary copies. Do not use `sudo` or offer mounted encrypted sources to a script that cannot independently validate the archive/restore process.

## Independent operator Fedora replay — first attempt, expected HOLD (2026-10-20)

The operator hash-verified the pinned V2.8 Python file (`sha256sum -c`: `DOBRZE`) and independently replayed **18/18 synthetic self-tests PASS**. The subsequent actual-copy `--audit` received **blank input for all four interactive paths**; therefore it did **not read either existing private backup**:

```text
SELFTESTS=18/18
SELFTEST_RESULT=PASS_ROOTLESS_SYNTHETIC_COPY_GATE_ONLY
PRIMARY_HOOK=NOT_PROVIDED
PRIMARY_GUARD=NOT_PROVIDED
SECONDARY_HOOK=NOT_PROVIDED
SECONDARY_GUARD=NOT_PROVIDED
FS_TOPOLOGY_HOOK=NOT_ASSESSED
FS_TOPOLOGY_GUARD=NOT_ASSESSED
INDEPENDENT_FAILURE_DOMAIN=NOT_PROVEN_BY_LOCAL_PATH_CHECKS
RECOVERY_COPY_READONLY_CHECK=HOLD
V28_EXIT_CODE=2
ASUS_CONTACTED=NO
FILES_MODIFIED=NO
CRON_MODIFIED=NO
DEPLOYMENT_GATE=HOLD
```

**Classification:** `INPUT_MISSING / AUDIT_NOT_PERFORMED`, **not** `HASH_MISMATCH`, missing or corrupt backup, failed filesystem separation, or actual restore failure. No backup paths or contents have been shared.

Earlier operator session notes documented **private Fedora backup directory naming patterns**, not exact shareable paths: `$HOME/issue235-hook-backup-*/services-start` and `$HOME/issue235-dns-guard-backup-*/dns-guard`. A local, nonprivileged, metadata-only path discovery is sufficient to find candidates for the next **read-only** run; the operator must select the correct verified copies, and no paths should be pasted into the public report.

```bash
find "$HOME" -mindepth 2 -maxdepth 2 -type f \
  \( -path "$HOME/issue235-hook-backup-*/services-start" -o \
     -path "$HOME/issue235-dns-guard-backup-*/dns-guard" \) -print
```

If the files are found, rerun `python3 -B issue235_recovery_separation_audit_v28.py --audit` and paste each complete local path at its appropriate hidden prompt. The secondary inputs are optional. No copy, archive or permission is to be altered merely to make the audit pass. A failing mandatory integrity check remains `HOLD`.

## Independent operator Fedora replay — second attempt, primary backups PASS (2026-10-20)

The operator supplied two private input paths locally to the already hash-verified, rootless V2.8 `--audit`. Neither path nor any script bytes were published. The output was:

```text
PRIMARY_HOOK=BYTES_OWNER_MODE_PASS_AT_READ_TIME
PRIMARY_GUARD=BYTES_OWNER_MODE_PASS_AT_READ_TIME
SECONDARY_HOOK=NOT_PROVIDED
SECONDARY_GUARD=NOT_PROVIDED
FS_TOPOLOGY_HOOK=NOT_ASSESSED
FS_TOPOLOGY_GUARD=NOT_ASSESSED
ROOTLESS_PROTECTED_APPROVAL_STORE=NOT_ASSESSED
INDEPENDENT_FAILURE_DOMAIN=NOT_PROVEN_BY_LOCAL_PATH_CHECKS
ENCRYPTED_RESTIC_RESTORE_AND_OFFLINE_MEDIA=NOT_TESTED
ACTUAL_RESTORE_ON_INDEPENDENT_DEVICE=NOT_TESTED
TWO_SCRIPT_ROOT_OWNED_PUBLICATION=NOT_AUTHORIZED
ASUS_CONTACTED=NO
FILES_MODIFIED=NO
CRON_MODIFIED=NO
PRIVILEGED_EXECUTION_TRUST_GATE=HOLD
DEPLOYMENT_GATE=HOLD
RECOVERY_COPY_READONLY_CHECK=PASS_PRIMARY_SNAPSHOTS_ONLY
V28_EXIT_CODE=0
```

**Acceptance:** `PRIMARY_BACKUP_SOURCE_BYTES_AND_BASIC_DAC_AT_READ_TIME=PASS_FOR_BOTH`. This supersedes the earlier *empty-input* run's `HOLD` for the **two actual primary loose files only**. It does not show immutable copies against a process with the same UID, backup inclusion in any other archive, independent physical failure domain, independent operator-approved manifest, genuine router recovery or root-owned publication. The optional second copies were **not supplied**, so `FS_TOPOLOGY_*=NOT_ASSESSED` is the only supported statement; **do not infer primary files are on the same filesystem or on different disks**.

### Existing Restic infrastructure is a different evidence scope

The existing repository's [RouterCloud versioned backup design](../../docs/routercloud-versioned-backup.md) describes an encrypted Restic repository on a separate local SSD, **for RouterCloud data**. This is not evidence that the two Issue #235 private hook/DNS Guard files appear in any Restic snapshot. Likewise, the separate Fedora Recovery workflow must not be changed or its archive coverage assumed. Before claiming an independent Issue #235 recovery copy, perform a separately scoped **read-only inclusion inventory** of an already existing verified backup profile, followed eventually by a restore into disposable storage and a check of failure-domain / credentials custody. Do not run a new backup, alter retention or policy, or reuse backup credentials as the V2.7 approval authority.

## Stage gate and next work

- If both primary backup bytes pass: `RECOVERY_COPY_READONLY_CHECK=PASS_PRIMARY_SNAPSHOTS_ONLY`; the actual **independent** copy/recovery remains `NOT_PROVEN`.
- If either primary missing or mismatched: `RECOVERY_COPY_READONLY_CHECK=HOLD`. Do not repair, generate, overwrite, rescan/router-connect or substitute bytes automatically.
- The proposed **separate operator approval** remains `NOT_ISSUED`, untrusted publisher `NOT_BUILT` and JFFS2 interrupt-safe publication `NOT_PROVEN`.
- **No claimed stage/apply/reboot GO** for either script. No PR #245/DUFS/RouterCloud changes.

Final: `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.
