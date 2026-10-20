# Issue #235 — real local filesystem per-file rename/FD fixture V2.2 (2026-10-20)

> **Status:** OFFLINE/FEDORA-INTENDED ROOTLESS **SYNTHETIC** fixture; executed in isolated assistant Linux environment **19/19 self-tests PASS**, **subsequently independently replayed on operator's Fedora (see below)**. No ASUS contact. All production security/deployment approvals **HOLD**.

## Context

[The abstract V2.1 model](issue-235-monotonic-two-target-model-v21.md) was independently replayed by the operator on Fedora, with **19/19 PASS and seven expected matrix states**. That confirms only the abstract assumptions. V2.2 tests ordinary same-filesystem pathname replacement and inode/FD persistence using actual Linux filesystem operations on **disposable user-owned synthetic files**. It does **not** implement or demonstrate any `root:root` privileged publisher.

## Artifact and environment boundary

- Script: `issue235_per_file_inode_publish_lab_v22.py`.
- SHA-256 of locally executed script: `b3c98521f6d8d59581ebb36f2735381cdaee34c07d225eed13e332d6ef94dc85`.
- Only synthetic content `SYNTHETIC OLD PLACEHOLDER` / `SYNTHETIC PINNED GUARD BYTES` / `SYNTHETIC PINNED HOOK BYTES`.
- Creates **one private, auto-cleaned** temporary directory inside `$HOME`, within which it writes, mode-adjusts, flushes and renames the synthetic fixture files. Does not require `sudo` and cannot be pointed at other filesystem paths from its CLI.
- No SSH/network modules, no subprocess or target script execution, no router secret or production source bytes, no Cron operations. `ASUS_CONTACTED=NO`.
- The Linux filesystem used for local execution is **not necessarily Fedora Btrfs** and is **not the production ASUS JFFS2**. Directory and file `fsync` returning successfully **does not prove power-loss durability or crash semantics**.

## Tests (local 19/19 PASS)

1. Private fixture directory mode 0700, synthetic-data-only scope, expected staged digest and regular single-link file.
2. Reject changed staged bytes, staged/destination symlinks, staged hardlink, world-writable stage, non-executable stage.
3. One-path real `os.replace` changed inode identity, exposing verified candidate bytes and `0755` via new pathname.
4. Crucial FD red test: **an FD opened to the original inode remains readable and writable after replacing the pathname**. A test write through the old FD changed the old inode, not the new pathname's bytes. This is Linux fixture behavior and **must not be generalized as writer exclusion or a same-FD secure publication contract**.
5. Before first replace the old pathname stays intact. In a two-path interruption fixture, either **guard-first** or **hook-first** leaves a mixed old/new state. Both replacements without interruption reach two new name bindings; no claim of two-path atomic transaction.
6. Candidate name is consumed after replacement.

The model performs its digest check on a file FD **before** replacing a pathname. That is **NOT a race-free FD-to-publication handoff**: it cannot exclude an adversarial same-directory replacement between the verification and the name-based `os.replace`. Likewise, its fixture processes retain the **same nonroot UID** throughout: mode 0755 is not proof of root-controlled ownership.

## Independent operator Fedora replay (2026-10-20)

The operator verified the previously pinned `issue235_per_file_inode_publish_lab_v22.py` SHA-256 (`sha256sum -c` returned `DOBRZE`) and ran `python3 -B ... --self-test --matrix` on Fedora. The complete sanitized output independently reproduced **19/19 PASS** and:

- `SAME_FILESYSTEM_RENAME=EXERCISED`, `FILE_AND_DIRECTORY_FSYNC=EXERCISED_NOT_CRASH_PROVEN`;
- `OLD_FD_AFTER_RENAME=STILL_USABLE` and `OLD_W_OK_WRITE_FD=NOT_REVOKED_BY_RENAME`;
- `OLD_FD_WRITES_NEW_PATH=NO_IN_THIS_SINGLE_USER_FIXTURE`, `TWO_PATH_ATOMIC_COMMIT=NO`;
- `RACE_FREE_ADVERSARIAL_PUBLISH=NOT_PROVEN`, `REAL_ROOT_OWNER_BOUNDARY=NOT_TESTED`, `JFFS2_POWERLOSS_PERSISTENCE=NOT_TESTED`;
- `ASUS_CONTACTED=NO`, `ROUTER_FILES_MODIFIED=NO`, `CRON_MODIFIED=NO`, `DEPLOYMENT_GATE=HOLD`.

These are reproducible real Linux inode and rename **primitives**, not trusted privileged publication or real JFFS2 durability evidence. The previously open writer FD is a negative finding: rename does not by itself revoke a writer's access to the old inode.

## Security conclusion and blocking gaps

**V2.2 fixture result:** `19/19 PASS_ROOTLESS_FILESYSTEM_LAB_ONLY`. This is positive *primitive behavior* and negative *old-FD persistence* evidence.

**Still NOT PROVEN:**
- Actual `root:root` candidate authority and protected source/parent/lock/receipt identity;
- exclusion of a concurrent nonroot owner or retained writable FD while old content is root-executed;
- actual atomic same-inode pinning through publication (vs. separate pathname check);
- JFFS2-specific crash, power interruption, `fsync` durability and reboot ordering;
- independent backup/recovery storage; WAN/Unbound/Pi-hole availability and break-glass safety;
- target permission/owner mutation on ASUS or actual publication of either script.

**Next valuable research:** a rootless, physically separate test that specifically challenges checked-FD → rename-by-name races and demonstrates the need for a genuinely trusted publisher/dirfd design. No deployable `chown`, `mv`, `cru`, JFFS or firmware apply commands follow from this fixture.

**Final gates:** `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.
