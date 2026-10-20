# Issue #235 — FD-to-name publication race V2.3 (2026-10-20)

> **Status:** Synthetic, disposable Linux filesystem experiment, executed as **nonroot user**, **20/20 local self-tests PASS including expected-red adversarial name swaps**. No ASUS contact or production mutation. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.

## Operator baseline and scope

The operator independently reproduced the [V2.2 real-file rename/inode fixture](issue-235-rootless-file-inode-publish-v22.md): **19/19 PASS**; a previously open writable FD persisted on an old inode after `os.replace`, without modifying the newly published pathname in the single-user model. This is not a claim of writer isolation.

V2.3 advances from ordinary rename to an **intentionally adversarial synthetic name-swap** located precisely after an FD-bound source digest verification but before the name-based rename:

1. Open `stage` relative to a pinned directory FD with `O_NOFOLLOW`, verify `fstat`, single link, mode 0755 and SHA-256 of the **synthetic expected bytes** through that FD.
2. Simulate a same-UID attacker replacing the `stage` **directory entry**, without mutating the checked FD's original inode.
3. Rename `stage` to `live` relative to a pinned `dirfd`. The observed `live` path now names the attacker's synthetic alternate bytes **despite the correct FD digest**.
4. A post-rename SHA-256 check detects the wrong inode/contents, but **cannot undo the fact that it was briefly accessible by pathname**. Therefore, treating that postcheck as pre-execution protection is unsafe.

**V2.3 is not exploiting an actual router** and does not run the synthetic scripts. It proves a weakness in the **name-based protocol under a writer with directory modification rights**. Trusted parent directories and per-UID restrictions can change the threat model, but were **not** provided by the actual test; there is no tested root:root authority. This is precisely why earlier read-only parent DAC snapshots and separate trusted publisher authorization matter.

## Artifact, harness and results

- Python script: `issue235_fd_name_race_lab_v23.py`.
- SHA-256: `12d29c6424af08326a561d6376de8de223f3fe36b3d1b120c9d90c93a0498b31`.
- Executed as a nonroot Linux user in the assistant's isolated container: `python3 -B ... --self-test` → **20/20 PASS**, and `--matrix` → all expected red signals.
- New private `$HOME` directory with mode 0700 is created for each test and removed afterward; user-owned synthetic files only; no `sudo`, SSH, network connection, shell-script execution, Cron operations, `chown`, router paths, or required real sources.

Selected outcome lines:

```text
SOURCE_NAME_SWAPPED_AFTER_CHECK=YES
PRECHECKED_FD_STILL_ORIGINAL_INODE=YES
STAGE_NAME_CHANGED_INODE=YES
NAME_BASED_RENAME_PUBLISHED_SWAPPED_INODE=YES
POST_PUBLISH_HASH_MISMATCH_DETECTED=YES
POSTCHECK_PREVENTS_PREEXPOSURE=NO
DIRFD_ANCHOR_PREVENTS_SOURCE_BASENAME_SWAP=NO
TRUSTED_ROOT_OWNER_OR_SEPARATE_UID=NOT_TESTED
JFFS2_POWER_LOSS_AND_DURABILITY=NOT_TESTED
FD_BASED_ATOMIC_PUBLISH_OF_CHECKED_INODE=NOT_PROVEN
ASUS_CONTACTED=NO
ROUTER_FILES_MODIFIED=NO
CRON_MODIFIED=NO
PRIVILEGED_EXECUTION_TRUST_GATE=HOLD
DEPLOYMENT_GATE=HOLD
```

The full self-test matrix includes no-follow symlink rejection, FD identity persistence, late name swap after a final pre-check, expected-red wrong publication, postcheck detection, clean ordinary rename behavior, surviving old destination FD, pinned directory FD surviving a parent pathname rebind, same-UID changes despite mode 0755, and mixed two-target state.

**Important:** `O_NOFOLLOW`, `dirfd`, `fstat`, checksums and `renameat`/Python `os.replace` are valuable primitives, but the FD checked for content is not the file named by the later rename **if an attacker can rewrite its source basename between operations**. A post-publish mismatch is only detection and may be too late. The suite does not prove that a genuinely trusted no-writer staging area or an FD-to-inode kernel publish API is available on GNUton.

## Independent operator replay on Fedora (2026-10-20)

The operator verified the previously pinned V2.3 artifact with `sha256sum -c` reporting `DOBRZE`, then executed `--self-test` and `--matrix` on Fedora:

- `SELFTESTS=20/20`, `SELFTEST_RESULT=PASS_SYNTHETIC_LINUX_INODE_RACE_LAB_ONLY`.
- Expected adversarial behavior reproduced: `SOURCE_NAME_SWAPPED_AFTER_CHECK=YES`, `PRECHECKED_FD_STILL_ORIGINAL_INODE=YES`, `STAGE_NAME_CHANGED_INODE=YES`, `NAME_BASED_RENAME_PUBLISHED_SWAPPED_INODE=YES`.
- `POST_PUBLISH_HASH_MISMATCH_DETECTED=YES`, `POSTCHECK_PREVENTS_PREEXPOSURE=NO`, `DIRFD_ANCHOR_PREVENTS_SOURCE_BASENAME_SWAP=NO`.
- `TRUSTED_ROOT_OWNER_OR_SEPARATE_UID=NOT_TESTED`, `JFFS2_POWER_LOSS_AND_DURABILITY=NOT_TESTED`, `FD_BASED_ATOMIC_PUBLISH_OF_CHECKED_INODE=NOT_PROVEN`.
- `ASUS_CONTACTED=NO`, `ROUTER_FILES_MODIFIED=NO`, `CRON_MODIFIED=NO`; `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.

This confirms **reproducibility of a deliberately insecure source-name handoff** on the operator's Fedora under a same-UID attacker model. It does **not** establish that an actual firmware publisher is vulnerable to that race or that any real trusted publisher or JFFS2 recovery mechanism has been built.

### Design refinement — do not repeat same-UID demonstrations

Prior Issue #235 isolated labs have independently explored role separation, same-FD handoff, source pinning and signed receipts. Before proposing another rootless primitive test, **cross-reference those existing results** and identify only the unproven production boundary: a genuinely separate trusted root authority, root-controlled staging directory and inode content, writer/FD exclusion, firmware/JFFS2 interruption handling and independent DNS restoration.

The race is avoidable in principle when the stage directory and its contents are controlled exclusively by trusted authority, but V2.3 **does not test that condition**. Conversely, adding a final postcheck without excluding hostile name swaps remains an invalid prevention claim.

## Operational implications and remaining gate

1. **No production name-only helper should be approved** based on the V2.2 success criterion alone. Require a demonstrably trusted source and staging directory inaccessible to adversarial UIDs, and a publisher with protected process authority, stage and parent FDs.
2. **Reject mixed states** and unexpected publication inode/content identity, but do not claim post-facto rollback makes transient exposure impossible. Block all relevant root-execution entrypoints or eliminate the writer/name-swap ability *before* publishing.
3. A secure root-owned stage and independent root-owned rollback must be feasible on the reference GNUton / JFFS2 environment. Ext4/Btrfs/tmpfs/overlayfs fixture results do not prove durable JFFS2 semantics.
4. Reconcile outstanding V2.0/V2.1 failure boundaries: open FDs and in-flight processes, independently protected recoverable backups for both original scripts, safe root-Cron/WAN/bootstrap DNS and break-glass coordination, physical reset/power interruption, and explicit new apply approval.
5. **Operator Fedora replay of V2.3: COMPLETE — 20/20 PASS (operator-reported).** Local 20/20 fixture assertions are an off-router developer result, not acceptance by the operator.

**Status:** V2.2 independently replayed **19/19 PASS**; V2.3 isolated nonroot **20/20 PASS with expected-red source name swap**, independently replayed on Fedora **20/20 PASS**, **production deployment remains HOLD**. No ASUS/SSD/RouterCloud/DUFS worktree changed.
