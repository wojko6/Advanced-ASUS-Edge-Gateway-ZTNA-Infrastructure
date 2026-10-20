# Issue #235 — V2.7 distinct offline approval authority for two privileged scripts (2026-10-20)

> **Decision record:** DESIGN ONLY / DRAFT / NOT AN APPROVAL RECORD / NOT A RUNBOOK. `REAL_INDEPENDENT_APPROVAL=NOT_ISSUED`; `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.
> **Bounded targets:** the **full existing** `/jffs/scripts/services-start` and `/jffs/addons/asus-edge/bin/dns-guard`. **Not in scope:** PR #245 SSD, Stage B/C/E, RouterCloud/DUFS applications, changes to JFFS, Cron/NVRAM, DNS services or router reboot.

## Why V2.7 exists

The operator independently replayed [V2.6](../../evidence/2026-10-20/issue-235-two-script-approval-contract-v26.md) on Fedora with **29/29 PASS**. Its fixed two-role parser denies cross-project PR #245 scope and malformed or revoked *synthetic* approvals. V2.6 nevertheless uses a **synthetic in-script precommitted digest**; this is not a separate operator identity, authenticated approval process, protected key store, secured launcher or a real root-owned publisher.

The earlier Stage B artifacts recovered and pinned in [V2.4](../../evidence/2026-10-20/issue-235-trusted-publisher-evidence-gap-review-v24.md) prove valuable laboratory patterns but belong to **three-role PR #245 SSD** with literal `pr245-ssd-mount-roots` authorization. the Stage B V1.4 independently held FD report and V1.5 offline policy review (both retained in the operator's file Library) distinguish *approval bytes transport* from *authority of the approver*. V1.5's expected-red same-UID keyring/policy substitution illustrates the failure of an attacker-writable trust root. **Neither FD handoff, cryptographic signature nor manifest checksum alone proves who authorized a change.**

## Chosen candidate — independently held operator-approved manifest digest (option A)

This is a **proposed decision for review, not production acceptance**. It avoids adding operational signing-key lifecycle complexity before a real benefit is demonstrated; GPG/Ed25519 remains an alternative requiring key custody, rotation and revocation procedures. Any independent approved digest must be created *after* comparing the proposed source inputs with the already reviewed exact live full hook / DNS Guard version, never by the same process that controls candidate bytes or the destination.

| Principal / trust domain | Sole permitted responsibility | Forbidden assumption or action |
| --- | --- | --- |
| Candidate preparer, untrusted | Assemble a **proposal** for precisely two scripts with declared source digests, sizes, target names, new owner/mode and change purpose | Must not choose its own trusted digest, gain approval by copying an adjacent sidecar or run code as privileged publisher |
| Independent approver on controlled Fedora / separate custody | Review exact source provenance and intended effects; **independently select and record approval digest**, scope, generation, explicit validity and target list in separately controlled protected storage | Must not trust an approval digest computed and delivered solely by candidate without checking source; must not treat the approver's own unchecked runtime environment as a cryptographic root of trust |
| Protected policy carrier / verifier | Compare an authenticated approved record with precisely the candidate's canonical bytes and independently pinned code identity. Fail closed for missing, unknown, duplicated, stale, revoked or consumed approval | Must not accept unauthenticated `pin.v1`, an environment or argument containing a self-declared digest, unsigned candidate approval or a mutable sidecar as authority |
| Privileged launcher / publisher (UNBUILT) | Receive separately authenticated verified source and permission to act from protected authority, then apply **only separately approved per-target transitions** | Must not trust a plain FD number to prove provenance, execute candidate shell code in the verifier, allow arbitrary target names, or publish any bytes while writers can rebind stage names |
| Recovery operator, independent channel | Verify protected off-router recovery sources and independent DNS/LAN access, explicitly approve each stage / apply / reboot where proposed | Must not delete Cron, suppress WAN, overwrite source in place or convert success in a Python model to a production GO |

### Exact proposal namespace (logical fields only)

Canonical record `ISSUE235-TWO-SCRIPT-APPROVAL/1`, with the **dedicated scope** `issue235-privileged-scripts-owner-repair`. V2.6 already tests rigid ordered two-role grammar; V2.7 does **not** write or create a real approval record.

The future approval must bind: exact reviewed proposal bytes (whole-record SHA-256), two **fixed ordered** roles, full hook **not generated wrapper**, exact absolute destination identifiers, exact expected source length and SHA-256, owner `root:root`, mode `0755`, no symlink/multiple hardlinks, approved helper executable commit plus executable byte identity, explicit generation and approval ID, issue/scope identity, approval time policy and optional expiry, validity state `APPROVED / REVOKED / CONSUMED`, and separate operator attribution plus custody evidence. No active private paths, keys, live source hashes or approval tokens should be published in this repo or chat.

Any policy state which authorizes old generation or silently clears `REVOKED`/`CONSUMED` after restart is not a valid anti-rollback mechanism. A policy or keyring writable by candidate's UID, or by an untrusted same-UID process, defeats the independence assumption. Root-level adversaries cannot be excluded through Unix DAC alone. The threat model must state explicitly which previously authorized root processes are trusted, rather than claiming an absolute root-compromise resistance.

## Protocol states and fail-closed decisions

| State | May proceed? | Required proof and failure behavior |
| --- | --- | --- |
| `PROPOSED` | **NO** | Candidate has no inherent authority; even correctly formatted manifest is not approval |
| `REVIEWED_OFFLINE` | **NO** | Human/operator source review and signed internal record (not a generated key from candidate); exact code+source provenance; protected storage |
| `APPROVED_UNCONSUMED` | **NO for publication yet** | A verified approval permits a subsequent technical security preflight, but is not authorization to touch production |
| `STAGING_PREFLIGHT_PASS` | **Still NO until distinct GO** | Trusted launcher/candidate isolation, unchanged content/FD and trusted stage directories, verified current root-Cron/WAN/boot writers and independent DNS recovery |
| `APPLY_APPROVED` | **Only by separate explicit operator decision** | Narrow change-window approval after every technical gate (none met) |
| `PARTIAL_PUBLISH_OR_POWER_LOSS` | **HOLD / manual recovery** | No autonomous retry and no restoring owner-writable nonroot privileged scripts; must separately prove JFFS2 crash consistency and reboot recovery |
| `REVOKED / CONSUMED / UNKNOWN` | **DENY** | No fresh record from candidate alone, no fallback to older generations or PR #245 policy |

**Decision invariants:** `operator approval != file publication permission`; `same UID trust store == NOT INDEPENDENT`; `C accepts FD == NOT FD provenance`; `post-publish hash == detection, not transient pre-execution protection`; `per-target rename != two-file atomic transaction`; `root-owned replacement != old FD revocation`. For a safer design see [V2.0–V2.3 evidence](../../evidence/2026-10-20/issue-235-fd-to-name-publication-race-v23.md).

## V2.8 — recovery copies and separate failure domains (read-only only)

The [V2.8 rootless Fedora recovery-copy audit](../../evidence/2026-10-20/issue-235-recovery-copy-separation-v28.md) is limited to independent historical byte integrity and DAC snapshot checks of **operator-selected private Fedora backup copies**. It does not read any approval material, treat the source checksum as a real approval, use Restic or prove physical storage separation. Local synthetic self-tests passed **18/18**; the operator's second read-only Fedora audit independently confirmed **PRIMARY_HOOK/PRIMARY_GUARD=BYTES_OWNER_MODE_PASS_AT_READ_TIME** and **PASS_PRIMARY_SNAPSHOTS_ONLY**; secondaries and independent restore remain **NOT_ASSESSED**. A distinct `st_dev` proves at most a different filesystem reported by the kernel, not independent disk/host failure resilience.

**V2.7 approval authority and V2.8 recovery copies are intentionally separate evidence streams.** Never create operator approval automatically from backup bytes, claim a file owner/mode of `0600` protects it against the same UID, or reuse a PR #245 approval pin. Root-owned publisher and DNS/JFFS2 recovery remain independent unproven GO gates.



## Concrete engineering work still required

**V2.9 scope update:** [independent Fedora-loss recovery review](../../evidence/2026-10-20/issue-235-independent-recovery-failure-domain-v29.md) distinguishes already verified *local* bytes from a physically independent off-host/offline restore and separate custody of authorization. A bounded read-only metadata scanner has local 9/9 model tests PASS, operator Fedora replay pending; it does not validate Restic inclusion or physical independence. Do not assume the RouterCloud Restic staging repository or the distinct Fedora Recovery project covers the two private scripts. No permission, backup schedule, publication or issuer change approved.

1. **Separate the approving authority:** determine how a protected digest/approval is created and held, who can change it, which code verifies it, how generation/revocation survive loss, and how a compromised candidate/same UID cannot rewrite the approval. No real approval yet.
2. **Reauthenticating the exact two sources:** preserve byte-for-byte the current full firmware `services-start` semantic behavior and independently reviewed DNS Guard. Private backup copies have been validated on Fedora; independent recovery *outside its failure domain* still requires evidence.
3. **Trustworthy on-router publisher:** demonstrate who actually runs it as root, where its immutable/protected executable and staging directories live and how it binds verified source **inode and bytes** to the published name without a hostile source-basename writer, old owner FD or in-flight root process.
4. **JFFS2 and power-loss:** representative target filesystem interruption and persisted safe rollback or operator recovery for *each* path; do not import ext4/Btrfs success as JFFS2 proof.
5. **DNS and startup continuity:** root-Cron, primary-WAN event, manually triggered emergency hook and services-start re-entry all exist independently. Do not remove recovery channels or claim new init-start guard solves untrusted firmware script dispatcher.
6. **Separate human approval steps:** evidence-only design review now; later separate explicit operator approval for staging, apply and restart — not implied by signing a manifest or merging docs.
7. **Security issue scope:** this covers the **two privileged scripts** and does not close Issue #235's distinct RouterCloud runtime privilege and active-file origin-isolation acceptance criteria.

## Decision

**Candidate A — independently operator-approved, separately protected canonical manifest SHA-256 — SELECTED FOR FURTHER DESIGN REVIEW ONLY**; no real signer, key, token, approval record or ACL/provisioning action created. Alternative B (signed GPG/Ed25519) remains a separately reviewed option; signature verification cannot compensate for an unprotected signer/key or keyring policy.

```text
V27_APPROVAL_ARCHITECTURE=DESIGN_REVIEW_ONLY
OPERATOR_APPROVAL=NOT_ISSUED
INDEPENDENT_TRUST_ROOT=NOT_PROVEN
TWO_TARGET_REAL_SOURCE_APPROVAL=NOT_GRANTED
TRUSTED_ROOT_PUBLISHER=NOT_IMPLEMENTED
JFFS2_POWERLOSS_RECOVERY=NOT_PROVEN
DNS_FAILOPEN_DURING_APPLY=NOT_PROVEN
PRIVILEGED_EXECUTION_TRUST_GATE=HOLD
DEPLOYMENT_GATE=HOLD
```
