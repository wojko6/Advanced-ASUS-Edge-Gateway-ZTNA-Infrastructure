# Issue #235 / PR #245 — Stage B payload provenance and recovery contract (DRAFT)

> **DESIGN ONLY — NOT AN INSTALLER, RUNBOOK EXECUTION OR PRODUCTION APPROVAL.**
> Date: 2026-10-17. `DEPLOYMENT_GATE=HOLD`. Neither production ASUS nor its JFFS, SSD mount modes, hooks, services, swap, or private UUID files have been altered under this proposal.

## 1. Scope and evidence

This design applies **only** to delivering three future payload files for the GNUton ASUS TUF-AX5400 mount-root mode repair tracked by Draft PR #245. It does not implement or approve the helper's eventual run, the installation or activation of `post-mount` V3, a reboot/remount, DUFS/RouterCloud PrivDrop, DAC migration or the separately developed Native SSD Trust Helper.

Fedora-only synthetic Stage B lab: versions v0 (22/22), v1 (37/37), v1.1 (49/49), v1.2 (60/60), v1.3 (unchanged v1.2 **60/60** + separate importer **26/26**, per native/QEMU/sanitizer run). On 2026-10-17 operator output confirms `ARMV7_SOFT_FLOAT_ELF=PASS`, `ARMV7_STATIC_LINK=PASS`, `ARMV7_V13_QEMU=PASS` and `V13_CLANG_SANITIZERS=PASS` using QEMU user-mode on **Fedora's kernel**. These checks cover synthetic rejection logic, **not** ASUS kernel/JFFS2 behavior, real UUID import, trusted root-owned installation, hardlink/fsync durability or power-loss recovery.

The original live `/jffs/scripts/post-mount` and private Fedora V3 candidate have separate exact-byte integrity records. Stage B **must not inspect/overwrite/execute** either as part of staging. The existing live hook must continue to match its authorized pinned original; drift stops all future stage work. Keep swap-before-AMTM startup order, and never use the generic project installer that might modify the independent `services-start`.

## 2. Trust model and non-negotiable assumptions

The lab's compiled synthetic SHA-256 manifest pin is **not** a production trust anchor. SHA-256 detects divergence from a *trusted* expectation; it cannot establish who supplied that expectation. For production design the trusted manifest needs an independently reviewed and protected origin, linked to a reviewed helper revision and to separately verified private device/partition UUID mapping. A signed manifest with an independently pinned verification key, or an offline independently verified manifest digest kept outside attacker-writable paths, are candidate models to review; **neither is implemented or authorized**. Avoid a circular check in which an attacker can replace both the file and its expected digest.

Boundary:
- Adversary: non-root writes or renames of world-writable SSD objects, symlink/path swaps, untrusted or partial transfers, source modifications during a copy, malicious existing target, crash/interruption and stale candidate revisions.
- Defended by design: descriptor-anchored type/mode/owner and size checks; no symlinks or hardlinks for source/target; verified manifests and exact allowlist; per-file postwrite integrity; no-clobber publishing; explicit HOLD and manual reconciliation.
- **Not solved** by the design: competing UID 0 writers, continuously mutable ancestors, kernel/JFFS2 semantic drift, power cuts between filesystem operations, credential or signing-key compromise, compromised router firmware, absence of a reliable wired recovery path.
- The JFFS `/jffs` ancestry is not assumed safe because the last check passed. Independently recheck freshness, actual numeric `0:0` ownership, modes, device/mount identity and no symlinks under an authorized maintenance window.
- Production UUID plaintext and its secret-specific hashes/pins remain **outside public GitHub, issue comments, worklogs, stdout/stderr, telemetry and build artifacts**. Keep them only in approved private protected/offline media. Public docs may list exact target *names*, not bytes or sensitive digests.

## 3. Fixed allowlist and immutable import contract

Only the following production targets are in scope:

| Target relative to `/jffs/addons/asus-edge` | Type | Final mode | Owner | Provenance |
| --- | --- | --- | --- | --- |
| `bin/issue235-ssd-mount-mode` | regular executable, not symlink | `0755` | `0:0` | reviewed exact PR #245 helper revision + public vetted SHA-256 |
| `private/router-data.uuid` | regular, not symlink | `0600` | `0:0` | independently verified **private** ROUTER_DATA UUID mapping |
| `private/entware.uuid` | regular, not symlink | `0600` | `0:0` | independently verified **private** ENTWARE UUID mapping |

The container `private/` must be a real `0700 0:0` directory. The existing `/jffs`, `/jffs/addons`, `/jffs/addons/asus-edge` and `bin` ancestors must be real non-symlink `0755 0:0` directories and their mount/namespace identity must be justified; do not chmod pre-existing directories to make them pass without a separate authorization.

Future importer accepts exactly **three** manifest entries with fixed logical roles and paths; rejects duplicates, unrecognized keys or paths, ambiguous separators, extra entries, unexpected file types, inconsistent lengths, unsafe size, missing independent provenance and any policy drift. Specify a canonical byte serialization and an explicit version number **before** computing an authoritative manifest pin. No `../`, absolute source paths supplied by untrusted records, symlink traversals, wildcard expansion or user-selectable production destination. Read of private files, even for diagnostic tests, requires a separately reviewed procedure; laboratory tests continue to use disposable fake data.

The source transfer/import may eventually use authenticated transport with a pinned endpoint identity, but **transport does not replace independent content integrity and provenance**. Source regular files must be opened with trusted anchored descriptors and `O_NOFOLLOW`/`O_CLOEXEC`, rejecting hardlinks when required; capture size, mode, UID/GID, device/inode and trust of parents. Use bounded streaming reads, compare manifest digest, and reject source metadata/content changes before, during or after preparation. A postcopy SHA-256 check of *both* original descriptor and prepared descriptor is necessary but **insufficient** against a privileged concurrent writer. Production importer and a kernel-enforced immutable snapshot guarantee remain **unimplemented**.

## 4. Planned publication protocol: no-clobber, not bundle-atomic

**Precondition:** fresh Stage A **GO** and *separate explicit Stage B approval*, no old/post-mount patch active, accepted writer-compatibility risk and a trusted local/offline recovery route. Anything unknown = STOP.

1. **READ-ONLY PREFLIGHT:** confirm physical model/firmware, `/jffs` type/space, original hook SHA/owner/mode, exact ext4 mounts and both active swaps, exact JFFS ancestor trust, reviewed artifacts, manifest provenance and private-input integrity. Do not print UUIDs or read live hooks into the log.
2. **INPUT ACQUISITION:** verify each source's independent trust anchor; use identity-pinned descriptor-relative access rather than untrusted mutable path reopening. Reject symlink/hardlink, wrong size/mode/owner, unexpected inode replacement and altered content. No publication while any source remains unchecked.
3. **PREPARE ALL THREE:** under the future, approved **root-owned** JFFS location, create three unique private temporary regular files with `O_CREAT|O_EXCL|O_NOFOLLOW` or justified equivalent, scoped to their exact destination directories. Treat the creation of a missing `private/` directory as a *separate specifically allowed Stage B operation*. Write by checked bounded loops, establish exact numeric owner/mode, verify bytes/digest on held FDs, `fsync` each file, and verify parent identity. A temporary secret UUID must never be world-readable even briefly. Preparing everything in advance does **not** itself guarantee an atomic three-file transaction.
4. **PUBLISH ONLY AFTER PREPARATION PASS:** require a **proven on-target JFFS2** no-replace primitive (e.g. `linkat` *only if its semantics and durability are independently demonstrated*). Do **not** substitute normal `rename`/`mv` that may clobber an existing target. Keep the namespace pinned and recheck as narrowly as possible. Publish private UUID A and B **before the helper**, so the helper is the last visible target. This is an ordering convention, **not** a commit marker, activation flag or synchronization barrier. It does not make the three writes atomic. No fourth marker/state file may be created without a separate scope review.
5. **AFTER EACH PUBLISH:** verify target identity/type, `0:0` owner, intended mode, exact digest, source/target relation, and supported file+directory sync semantics. Treat every failure after the no-clobber link as **published-but-unverified / manual REVIEW**; it is unsafe to infer the destination is absent from an error return. Never automatically retry or remove the newly visible target on a failed sync/unlink/verification.
6. **FINAL READ-ONLY ATTESTATION:** all three exact targets must be independently verified and all three parents remain trusted. Confirm original `post-mount`, SSD modes, swaps, and services were not touched. Store a **nonsecret** operator acceptance record outside JFFS containing only gate statuses, reviewed revision ID and aggregate state; **no private UUID hashes/values**. Only then may `STAGE_B_VERIFIED` be recorded. **Stage C still needs its own authorization.**

**Hard blocker:** JFFS2 `linkat` semantics, same-filesystem no-clobber behavior, fsync-of-directory support, crash ordering, older ASUS kernel syscall support and concurrent namespace safety are not established. If any is unsupported or unknown, Stage B is **NO-GO**. No synthetic Fedora/QEMU test substitutes for an approved bounded JFFS2 fixture test and independent recovery review.

## 5. State machine and diagnostic classes

States are *logical conclusions from independently verified on-disk evidence*, **not** a fourth file under JFFS:

| State | Meaning | Allowed next action |
| --- | --- | --- |
| `S0_EMPTY_VERIFIED` | No target/candidate/collision; all parents verified | May begin only after Stage B approval |
| `S1_PREPARED_3` | Three private temp candidates verified; no final target yet | May publish only under stable reviewed conditions |
| `S2_UUID_A_VISIBLE` | One UUID target linked; others uncommitted | STOP if interrupted; manual review |
| `S3_UUIDS_VISIBLE` | Both UUID targets linked; helper not published | STOP if interrupted; manual review |
| `S4_HELPER_VISIBLE` | Three target names visible, final audit pending | Not success; read-only final audit |
| `S5_STAGED_VERIFIED` | All three independently verified; original hook intact | End Stage B, no invocation; request new Stage C approval |
| `HOLD_UNKNOWN` | Unexpected objects, metadata drift, source conflict or unproven JFFS operation | No write/retry/cleanup; operator investigates |
| `PARTIAL_STATE_REVIEW` | Post-link error, non-atomic interrupted bundle or uncertain durability | No write/retry/cleanup; operator reconstructs state |

Diagnostic failures before publish distinguish `MANIFEST_UNTRUSTED`, `SOURCE_INVALID`, `PREFLIGHT_DRIFT`, `TEMP_CREATE_FAILED`, `TEMP_WRITE_FAILED`, `PREPARED_VERIFY_FAILED`, `TARGET_COLLISION` and `JFFS_PRIMITIVE_UNPROVEN`. A post-publication failure distinguishes `LINK_RESULT_UNCERTAIN`, `POST_LINK_FSYNC_FAILED`, `TEMP_UNLINK_FAILED`, `POST_UNLINK_SYNC_FAILED` and `FINAL_TARGET_VERIFY_FAILED`, all collapsing operationally into `PARTIAL_STATE_REVIEW`. A successful command exit or a single target's hash does **not** prove durability or bundle completion.

The exact future implementation's exit codes and logging map must be reviewed, tested under fault injection and fixed **before** it is eligible for production. The present v1.3 test binary and these state names are **not** an installed state machine.

## 6. Incident decision and rollback (design, not instructions to execute now)

| Observation | Immediate decision | Recovery requirement |
| --- | --- | --- |
| Manifest trust failure, parent drift, existing target or unsafe mode **before any publish** | `HOLD_UNKNOWN`; do not start or adjust permissions | Re-establish provenance and root ownership with independent evidence; reapprove if needed |
| All temps prepared but no final names; interruption | `HOLD_UNKNOWN`; no blind cleanup | Inspect temp/target identities, ownership and digests off the critical path; remove *only* exact audited items if separately approved |
| One or two UUID targets visible | `PARTIAL_STATE_REVIEW`; **no automatic resume** | Record which exact destinations exist and their hashes/modes; operator decides scoped cleanup vs leave inert |
| All three visible; any fsync/unlink/hash verification failed | `PARTIAL_STATE_REVIEW`; presence does not mean durable success | Read-only inspection, JFFS evidence and documented fresh approval; never overwrite existing target automatically |
| All three final files verified, original hook unchanged | Stage B accepted only | Stop; do not execute helper or edit hook until separately authorized Stage C |
| Stage C later fails | **Different authorization and recovery scope** | Restore exact original hook under its separate atomic same-JFFS plan; never use a blind full-project reinstall |
| Router loses remote access | No assumption that Tailscale/DNS is available | Use independently attested local wired access and protected offline original; actual full recovery not yet demonstrated |

A Stage B-only rollback is not automatically defined as deleting all three files: the directory may contain pre-existing or subsequently used data, and deletion after Stage C could damage an active dependency. Any removal requires a *separate explicitly bounded* operator decision after verifying each exact inode, provenance, use and ownership. No recursive deletion, untrusted wildcard cleanup or permissive emergency chmod. Existing private original-hook recovery archive and Fedora restoration rehearsal do not establish live JFFS restore under power loss.

## 7. Production GO/NO-GO matrix and independent approval boundaries

| Gate | Current evidence | Decision |
| --- | --- | --- |
| Fedora synthetic source import, SHA-256 and negative tests | v1.3 native, soft-float ARMv7 QEMU, sanitizer tests PASS | **LAB PASS only** |
| Authenticated and independent production manifest provenance | Not designed/implemented/independently audited | **HOLD** |
| Device-side staging transport, root:root and exact private modes | Not implemented/tested | **HOLD** |
| Physical ASUS JFFS2 no-replace, directory fsync, crash recovery | No authorized fixture test | **HOLD** |
| Continuous parent/namespace trust and root-writer conflicts | Snapshots/static search only | **HOLD** |
| First-level SSD writers' compatibility with root 0755 | Residual unknown; separately track permissive children in issue #263 | **HOLD** |
| Fresh original `post-mount` SHA, recoverable backup and local management | Historical evidence and operator attestation; fresh check required | **PENDING** |
| Permission to stage files (B) | No explicit approval | **NOT AUTHORIZED** |
| Permission to activate hook (C) | Separate explicit approval required | **NOT AUTHORIZED** |
| Permission for boot/remount verification (E) | Separate explicit approval required | **NOT AUTHORIZED** |

**Next development action:** review the **manifest authority and transport contract** in a nonsecret design; select a justified strategy for keeping expected digests independent from uploaded payloads, and define safe bounded on-target JFFS2 capability validation requiring separate advance authorization. Do not start the actual on-router test or use real private payloads as synthetic inputs.

Related documents: [scoped staging/activation/rollback runbook](issue235-jffs-staging-activation-rollback-runbook-draft.md), [production GO/NO-GO](issue235-production-go-no-go-2026-10-15.md), [SSD mount-mode repair analysis](issue235-ssd-mount-postmount-repair.md). **Issue #235 OPEN / PR #245 DRAFT / `DEPLOYMENT_GATE=HOLD`.**
