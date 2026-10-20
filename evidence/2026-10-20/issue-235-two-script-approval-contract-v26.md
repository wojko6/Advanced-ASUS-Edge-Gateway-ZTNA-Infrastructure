# Issue #235 — new two-script approval-scope contract V2.6 (2026-10-20)

> **Status:** Fedora-compatible, *entirely synthetic/in-memory* approval-contract model. **29/29 local self-tests PASS**; independent operator Fedora replay PENDING. No real root authority, no target file reads, no router connection and no JFFS publication. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Trigger and achieved dependency

The operator independently ran V2.5 against the original historical Canonical Manifest C/ZIP on Fedora:

- `SELFTESTS=10/10`, `ORIGINAL_C_SHA256=EXACT_MATCH`.
- `ZIP_C_SOURCE_BYTES=EXACT_MATCH`, `ZIP_UNIQUE_SYNTHETIC_BASELINE=PASS`.
- `ARCHIVE_MEMBER_COUNT_WITHIN_LIMIT=YES`, `SOURCE_AND_ZIP=VERIFIED_AT_READ_TIME`, `ATTESTATION_EXIT_CODE=0`.
- `ASUS_CONTACTED=NO`, `TWO_TARGET_SCRIPT_APPROVAL=NOT_GRANTED`, `DEPLOYMENT_GATE=HOLD`.

This closes the historical SSD PR #245 **source/ZIP identity** gap, not an independent approval for root-executed scripts. Do not move/copy SSD repair sources, manifests or existing policy files into Issue #235's *new* publisher.

## New two-role namespace (DESIGN ONLY)

The new allowlisted roles are **precisely**:

| Field | Role 1 | Role 2 |
| --- | --- | --- |
| Meaning | Existing full firmware `services-start` hook | Existing DNS Guard program |
| Target path | `/jffs/scripts/services-start` | `/jffs/addons/asus-edge/bin/dns-guard` |
| Expected owner after hypothetical repair | `root:root` | `root:root` |
| Expected mode | `0755` | `0755` |
| Required file identity | Regular, single hard link, no symlink | Regular, single hard link, no symlink |
| Real source size/sha256 | Must be separately reauthenticated and pinned in a future private approval; **no real source bytes read in V2.6** | Same |

Versioned prototype manifest header: `ISSUE235-TWO-SCRIPT-APPROVAL/1`. Exact scope: `issue235-privileged-scripts-owner-repair`, initial **synthetic** generation 1. Two roles and their paths are ordered and fixed. Duplicate/extra/renamed role, foreign target, foreign scope, incorrectly declared mode/owner, extra fields, noncanonical newlines, unexpected approval generation, revoked/consumed approval, changed source bytes or broken digest must **DENY**.

**Cross-project isolation is enforced in the test contract:** `pr245-ssd-mount-roots` is explicitly rejected. No PR #245 Stage B approval may be interpreted or re-signed automatically as approval for this two-target change. Approval scopes are distinct and the new schema does not contain real private UUID values.

## Local artifact and test result

- `issue235_two_target_contract_model_v26.py` — SHA-256 `a847e2f6ae0715704645a010178add68bd7d3874a48be19abeb547715d03a339`.
- Contains only fixed artificial source bytes prefixed `SYNTHETIC-ONLY-`; the SHA-256 approval `fc0cda2e6ee7b6cc3c3e9acb45de6df7d5ccad6ab1d60064522d52afa8d174ad` is **hardcoded for the test fixture**, not derived from an untrusted runtime candidate or an operator's protected signer.
- Local `--self-test` **29/29 PASS**; `--matrix` five explicit states (synthetic exact pair accepts in model; SSD scope, bad root owner, source drift and revoked authority deny).
- No CLI to select external paths or files; no `sudo`, imports for network, `subprocess`, source reads, compilation, chmod/chown, writing targets, importing real keys or JFFS mutation.
- No production root credentials, secure signed approval, independently protected trust store, policy anti-rollback durability, process/FD confinement, live JFFS behavior or executable publisher.

**Important interpretation:** a model that uses synthetic source bytes and an in-script expected SHA-256 **proves a rigid grammar and fail-closed comparisons only**. It does *not* prove that an attacker cannot change the checker/source/authority at the same UID, that a real target matches a recorded manifest, or that approval came from a separate reviewer.

## Required independent acceptance gates (not met)

1. Authenticate the real existing full `services-start` and DNS Guard bytes **independently of mutable old-owner paths**, and protect immutable review input plus separate recovery copies in a second failure domain.
2. Define a *separate* operator approval mechanism and launcher identity for `issue235-privileged-scripts-owner-repair`; distinguish a trusted authority from the candidate and prevent same-UID policy substitution. The two-role schema has not been approved for production.
3. Test on representative ARMv7/GNUton/JFFS2 the trusted publisher's root-owned stage isolation, inode/content identity binding, safe single-file rename, old-owner writable FD exclusion, and crash interruption/persistence.
4. Coordinate every boot/manual `services-start`, named Cron, WAN-connected DNS Guard and break-glass entrypoint while retaining independently proven DNS recovery; do not claim a generated hook or normal `init-start` is a trusted boot barrier.
5. Require separate operator approval for any router staging, apply, reboot or recovery; do not turn synthetic `ACCEPT_SYNTHETIC_ONLY` into production GO.

Run on operator Fedora, no sudo:

```bash
cd ~/Pobrane
printf '%s  %s\n' 'a847e2f6ae0715704645a010178add68bd7d3874a48be19abeb547715d03a339' 'issue235_two_target_contract_model_v26.py' | sha256sum -c - &&
python3 -B issue235_two_target_contract_model_v26.py --self-test &&
python3 -B issue235_two_target_contract_model_v26.py --matrix
```

**Verdict:** `V26_CANONICAL_CONTRACT=PASS_SYNTHETIC_ONLY`, `REAL_INDEPENDENT_APPROVAL=NOT_IMPLEMENTED`, `REAL_ROOT_PUBLISHER=NOT_IMPLEMENTED`, `PRODUCTION_APPLY=NEVER_AVAILABLE_IN_TOOL`, `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.
