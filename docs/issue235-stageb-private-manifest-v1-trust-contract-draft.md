# Issue #235 / Draft PR #245 — private Stage B manifest v1 and independent trust anchor

**Status: DESIGN SPECIFICATION ONLY. No source code, release artifact, signature system or production stager is approved. `DEPLOYMENT_GATE=HOLD`.**

Date: 2026-10-17. Applies only to the mount-root mode repair's three Stage B payloads. The current synthetic v1.3 import tests (60/60 regression + 26/26 new, native/ARMv7 soft-float QEMU/Clang ASan-UBSan PASS) are *input-validation laboratory evidence*, **not** an implementation or acceptance of the private format below. No real UUIDs or private original/V3 hooks were read or copied in this design work.

## 1. Trust decision

**Provisional model for review: independent OFFLINE SHA-256 pin of the exact private manifest bytes.**

A trusted operator must create/review a candidate private manifest from separately verified local helper and UUID inputs, then approve its exact SHA-256 digest and store that digest **on a separately controlled offline medium / encrypted operator checkpoint, independently of the upload directory and destination router**. Before any later authorized import, the operator must obtain the pin from that independent trusted checkpoint and a separately reviewed verifier must compare the hash of the *entire* candidate manifest against it **before parsing or consuming any entries for publication**. A manifest obtained from the same mutable directory as its self-reported hash is **not authenticated**. Checking the SHA-256 fields inside an untrusted manifest alone provides no provenance.

**Important security distinction:** the offline digest pin establishes integrity *relative to an independently trusted approval*. It is **not a digital signature**, does not authenticate its author without a secure approval channel and is not safe if both candidate inputs and the approval checkpoint are compromised. A future signature-based Ed25519 design with a genuinely pinned public key is an alternative requiring a separate implementation and key-lifecycle review. Do not silently treat `sha256sum manifest && compare to manifest-side hash` as a trust check.

The **private** entire-manifest pin and **private UUID file hashes** may identify low-entropy device identifiers. They must not be committed, printed to logs, added to PR comments, included in public build artifacts, or stored in monitoring telemetry. The reviewed helper's public hash and commit ID may be public.

**Never manufacture the root of trust on the ASUS from untrusted on-device files.** If the independent checkpoint cannot be accessed and reviewed during a future authorized maintenance, status is `MANIFEST_TRUST_UNAVAILABLE / HOLD`.

## 2. Manifest v1 canonical bytes: exact positional ASCII

File encoding: **7-bit ASCII only**, with **LF (`0A`) line ending on every line including the last**. No UTF-8 BOM, CR (`0D`), NUL, blank lines, comments, trailing whitespace, tabs, duplicate keys, extra fields or optional sections. No leading/trailing bytes. Total manifest size hard limit: **2,048 bytes**. All field names and ordering are fixed; the version tag is exactly `ISSUE235-STAGEB-MANIFEST/1` (case-sensitive).

This specimen contains intentionally **invalid placeholders**, **not** production bytes or live UUID-derived hashes:

```text
ISSUE235-STAGEB-MANIFEST/1
scope=pr245-ssd-mount-roots
helper-git-commit=<40_lowercase_hex>
helper-size=<decimal>
helper-sha256=<64_lowercase_hex>
router-data-size=<decimal>
router-data-sha256=<64_lowercase_hex>
entware-size=<decimal>
entware-sha256=<64_lowercase_hex>
```

The real v1 document is *exactly nine LF-terminated lines*, with these exact fields and no others. Decimal sizes use ASCII `0-9`, are strictly positive, have **no leading zeros**, signs, whitespace, decimal separators or exponent notation. All three file sizes must remain within per-role limits, verified **both before read and before publication**:

| Field role | Hard bound | Fixed destination (not read from manifest) | Fixed trusted mode/owner |
| --- | --- | --- | --- |
| Helper | `1..262144` bytes | `/jffs/addons/asus-edge/bin/issue235-ssd-mount-mode` | regular, non-symlink, `0755 0:0` |
| ROUTER_DATA UUID | `1..128` bytes | `/jffs/addons/asus-edge/private/router-data.uuid` | regular, non-symlink, `0600 0:0` |
| ENTWARE UUID | `1..128` bytes | `/jffs/addons/asus-edge/private/entware.uuid` | regular, non-symlink, `0600 0:0` |

`helper-git-commit` is exactly 40 lowercase hex characters of a **separately reviewed** Git commit that contains the helper. It is an audit identifier, not an authorization to fetch/execute arbitrary repository content. The helper's SHA-256 is calculated on the exact intended source bytes and independently reconciled with that reviewed revision. Neither Git history alone nor this metadata replaces byte-level verification.

All SHA-256 fields contain exactly 64 ASCII **lowercase** hex characters. The two private UUID hashes remain **in the private manifest only**. The manifest never contains the UUID plaintext and never determines device UUID interpretation by itself. The current helper expects a privately verified UUID format; when file bytes and shell newline handling are specified at implementation review, the parser must ensure the source is the intended canonical representation (including whether there is one final newline) rather than guessing based on hash alone.

The fixed path, expected UID/GID, mode, file type and ordered roles are **policy constants of the independently audited verifier**, not attacker-controlled manifest fields. Any manifest with a path, target alias, arbitrary UID/mode, extra object, second signature/pin, platform fallback or unrecognized version must be rejected. Different canonical manifest versions require new review and a new independently approved offline pin; never auto-upgrade from `/1` to unknown `/2`.

## 3. Creation and independent approval (future design; not a terminal procedure)

1. Establish a reviewable helper revision and its exact bytes; independently verify **private** UUID-to-partition mapping using an approved local process without ever displaying or exporting values.
2. Construct the nine-line canonical manifest in a private controlled Fedora-only location using stable byte-level generation; reject unexpected source inode/mode/owner, content drift and noncanonical UUID input. Do not place it in a source tree, public Git object, CI artifact, log or shared workspace.
3. Independently compare the generated bytes with independently reviewed input identity/length/hash evidence. Only after accepting the review, compute its SHA-256 **over all nine LF-terminated lines**, and place that pin in the **separately controlled offline encrypted checkpoint**. Merely copying the digest next to the candidate manifest does not separate trust.
4. Define a traceable operator approval record identifying the reviewed helper revision, policy version, and approval epoch while holding **no sensitive value, UUID hash or entire-manifest digest in public records**.
5. At a future separately authorized import, retrieve the digest from the offline checkpoint and compare it with a **fresh descriptor-based read of the manifest**, before using the candidate contents. A verifier must keep its trust anchor independent of the candidate payload and maintain source identity through subsequent import/preparation. If the approval checkpoint, candidate or source identity has drifted, **STOP** and require a new explicit review/approval; no automatic pin regeneration.

This model still needs an implementation-level threat review of **how** the offline pin enters the verifier, how it is protected in memory, how concurrent file changes are excluded during the handoff, and how the final JFFS copy is independently checked. No production verification path has yet been implemented.

## 4. Manifest parser/verifier obligations: fail closed

Verification is order-sensitive:
1. Trusted checkpoint availability and operator approval **must precede any publication**.
2. Open the candidate manifest under a validated private source directory using descriptor-relative `O_NOFOLLOW|O_CLOEXEC` and required regular-file, single-link, owner/mode and size checks; read the entire bounded file and revalidate its identity/metadata. Rejected short reads must never be treated as accepted hashes; an implementation may retry `EINTR` only within bounded controlled conditions.
3. Hash **the exact bytes including final LF** and compare against the independently obtained pin using an appropriate fixed-length comparison. Only then parse the nine-line schema with exact field order, boundaries and canonical formatting.
4. Open exactly three source files by previously verified, pinned directory FDs; verify source file regularity, link count, owner, mode, bounded size and independently approved digests from the now-authenticated manifest. Revalidate hashes and source identities at least after copy; if source immutability under a privileged competing writer cannot be guaranteed, label that risk `OPEN`, do not call the snapshot trusted.
5. Prepare all three temporary candidate destinations with restrictive permissions, verify after copy and again after target creation; **never log UUID bytes or private hashes**. The manifest, source files and approved pin must not be delivered via a single mutable untrusted authority.
6. Absent a separately proven real-JFFS2 no-clobber/fsync/crash-recovery protocol, return `JFFS_PRIMITIVE_UNPROVEN / HOLD`. The manifest contract alone does not authorize delivery or activation.

A rejected candidate must not trigger automatic clobber, chmod, trusted-state creation, retry, cleanup, mount action, hook modification or reboot. Future implementations must be reviewed for race windows and secret leaks independently.

## 5. Contract-level negative cases (future Fedora synthetic suite)

These are **required test designs, not previously executed PASS claims**:

- One-byte flip of canonical header, any case change, CRLF conversion, BOM, trailing space, extra LF, unknown key, duplicate field, out-of-order field, inserted comment.
- Missing final LF, embedded NUL/non-ASCII, alternate hex case, malformed/short/long digest, non-decimal size, zero/leading-zero/oversized size, duplicate roles or changed scope.
- Candidate manifest modified but its hash updated **only in the same untrusted directory**: still rejected because the independent approval pin did not change.
- Candidate and source both replaced together; independent pin must reject; pinned directory/inode identity checks must also reject a symlink/rename/UID-mode drift.
- Validly pinned manifest with helper bytes not matching the reviewed helper revision; approved manifest with one UUID payload truncated/modified; no publication.
- Wrong trusted checkpoint, missing pin, stale or ambiguous approval revision, simultaneous writer mutation during source snapshot; `HOLD`, not a fallback acceptance.
- Fault after successful first or second no-clobber publish, including sync/unlink error: `PARTIAL_STATE_REVIEW`, no automatic re-run or cleanup. **Real JFFS2 durability is not a synthetic-test fact.**

## 6. Decisions, dependencies and approvals

| Topic | Status |
| --- | --- |
| Exact v1 canonical field/order/encoding policy | **DRAFT SPECIFIED**; review required before code |
| Independent offline pin authority | **PROPOSED, NOT OPERATIONAL OR AUDITED** |
| Private manifest generation and verifier | **NOT IMPLEMENTED** |
| Real UUID handling or helper data import | **NOT EXECUTED** |
| On-target root-owned JFFS3-file publication | **NOT IMPLEMENTED OR AUTHORIZED** |
| Real JFFS2 no-clobber and fsync semantics, power-loss recovery | **OPEN; cannot be inferred from QEMU** |
| Current `post-mount` / `services-start` / SSD mount roots | **UNCHANGED** |
| Stage B installation, Stage C activation, Stage E reboot/remount | **SEPARATE EXPLICIT AUTHORIZATIONS, NONE GRANTED** |

**Next step:** independently review the canonical format, trust checkpoint threat model and verifier's status/logging design, then create a **synthetic offline-only parser test** if the contract is accepted. Any on-router write experiment or production import requires a separate future approval with preflight/rollback conditions; do not do it based on this document.

References: [Stage B three-file/recovery contract](issue235-stageb-payload-provenance-recovery-design-draft.md), [Stage B/C/E runbook](issue235-jffs-staging-activation-rollback-runbook-draft.md), [GO/NO-GO matrix](issue235-production-go-no-go-2026-10-15.md).

**Issue #235 OPEN / Draft PR #245 / `DEPLOYMENT_GATE=HOLD`.**
