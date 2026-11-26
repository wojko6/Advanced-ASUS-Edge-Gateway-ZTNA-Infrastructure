# Issue #276 — legacy post-mount rollback regression (2026-10-22)

> **Scope:** Fedora/off-router only. This is a **review-only code fix and regression test**, not a router restore or production installation. Related Issue #235 / Draft PR #245 stay separate and at `DEPLOYMENT_GATE=HOLD`.

## Finding and source

The original `scripts/restore.sh` (Git blob `91fee3c8482127ef54f1e767e0256fe2fa193105`; pinned commit `505ab768cf9d0bcf8fd34222c4df4ce3d8bac676`) deliberately treated legacy `jffs/scripts/post-mount` as review-only. It stripped the archived hook from the extraction payload and skipped the hook during pre-restore snapshot, **but did not skip it during rollback**. After a later copy failure the rollback could delete the existing live hook and attempt to copy its nonexistent snapshot.

This is a control-flow defect confirmed in synthetic Fedora alternate-root tests. It is **not** evidence of a live outage on ASUS or of compromise by another actor.

## Operator-supplied Fedora evidence

| Lab | Result | Interpretation |
| --- | --- | --- |
| V0.1 RED | 15/15 model self-tests; 20/20 kernel fixture controls; `RED_DEMONSTRATED=YES` | The actual pinned `restore.sh` lost an existing synthetic hook after deterministic failure at the second `opt` copy |
| V0.2 GREEN | 21/21 model self-tests; 30/30 RED/GREEN checks; `PASS_BOUNDED_GREEN_FEDORA_ONLY` | The same fault with a shared applicable path list preserved the original hook, restored other files, and reported successful rollback |
| V0.3 regression | 16/16 model self-tests; 2/2 exact pinned upstream test suites; 56/56 extra checks; `PASS_FEDORA_PINNED_RESTORE_FULL_REGRESSION` | Existing archive validation and clean-room restore, legacy/current archive variants, absent hooks, success and fault paths passed |

All three results are transcribed from operator-provided terminal output. Tests used synthetic archives and temporary `EDGE_RESTORE_ROOT`; no real backup was read. V0.3's `56/56` excludes the two upstream suites' internal PASS assertions; it is not a repo-wide coverage claim.

## Minimal patch

`scripts/restore.sh` now derives `applicable-manifest-paths` **after archive/path/hash verification**. It selects only normal `jffs/` and `opt/` entries while excluding `jffs/scripts/post-mount`; both snapshot creation and rollback iterate over that identical list. The archived legacy hook remains review-only. A failure constructing the list exits without attempting restoration.

The archive verifier, original root/alternate-root gate, normal copy loop, review-only source stripping, and existing rollback diagnostics are otherwise unchanged.

## CI regression

`tests/test-restore-postmount-rollback.py` runs in a temporary rootless `/tmp` fixture. It creates a disposable archive and alternate target, forces failure **only before the second (`opt`) directory copy**, then verifies the restoration of other state and preservation of the protected hook.

The negative mutation-control intentionally reinstates the **old defective rollback input only in a temporary script copy** and requires the RED hook-deletion symptom, ensuring the test would detect a regression of this exact behavior. Other cases cover an archived legacy hook, review-only `recovery-reference` hook, and absence of an existing hook; each test uses artificial bytes.

`.github/workflows/shellcheck.yml` executes this test after the existing `test-restore-validation.sh` and `test-cleanroom-restore.sh` suites.

## Open gates

- **No approval for real restore:** no live JFFS/AMTM hook/Entware rollback, no exact firmware BusyBox/JFFS2 persistence, no power-loss injection.
- Full GitHub Actions outcome is **PENDING** until completed on this Draft PR; the local V0.3 PASS does not prove the new CI runner passes in GitHub Actions.
- This scope fixes precisely the *legacy hook rollback list mismatch*. It does not certify all archive handling, recovery correctness during arbitrary filesystem races, independent backup reliability or unrelated installer #278.
- **No direct changes to Issue #235, Draft PR #245, DUFS 0.47, ASUS SSD permissions or production deployments.**

**Decision:** Draft PR for review only; `ISSUE_276=OPEN`, `DEPLOYMENT_GATE=HOLD`. Separate operator approval would be required for any deployment/recovery change.
