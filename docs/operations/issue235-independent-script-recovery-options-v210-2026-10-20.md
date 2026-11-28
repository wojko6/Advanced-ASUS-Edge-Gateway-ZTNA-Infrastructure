# Issue #235 — V2.10 independent recovery options after Fedora loss (2026-10-20)

> **Decision memo, not an implementation/runbook.** No copy, Restic, new directory, permission change, mount, router access or production service action authorized. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Evidence that led to the decision

- [V2.8](../../evidence/2026-10-20/issue-235-recovery-copy-separation-v28.md): operator's Fedora primary **full `services-start`** and **DNS Guard** backup copies both had `BYTES_OWNER_MODE_PASS_AT_READ_TIME`; `RECOVERY_COPY_READONLY_CHECK=PASS_PRIMARY_SNAPSHOTS_ONLY`, exit 0.
- [V2.9](../../evidence/2026-10-20/issue-235-independent-recovery-failure-domain-v29.md): operator's independently pinned Fedora metadata scan **9/9 PASS**, exact one ordinary file per role, `PRIMARY_COPY_DEVICE_RELATION=SAME_ST_DEV`, `V29_INVENTORY_RESULT=PASS_METADATA_ONLY_INDEPENDENCE_NOT_PROVEN`, exit 0. No bytes were read. Sharing one filesystem is an observed correlated filesystem failure; physical media topology, off-host access, encryption key custody and archive inclusion are **not proven**.
- Existing [RouterCloud Restic wrapper](../../scripts/routercloud-backup.sh) backs up its **RouterCloud staging** path. Its backup store and scope are not accepted as containing #235 copies. The separate Fedora Recovery project remains independently managed; its #235 file coverage has not been demonstrated. Do not change either merely to address #235.

## Recovery objective and baseline

**Recovery goal:** independently obtain the exact two approved-for-recovery script bytes, necessary metadata and a separately reviewed provenance record **after a total loss or unavailability of the Fedora laptop**, verify SHA-256 of *both* files in a disposable location, and keep the operator's future production change authorization **distinct** from source backup custody. This is not permission to run restored bytes as root or publish to ASUS; restoration to a private scratch area must precede a separate root/JFFS2 application plan and explicit human GO.

The two files' historical reviewed SHA-256 values are recorded in V2.8 evidence. Preserve the full existing `services-start` rather than substituting the installer's short generated wrapper. Do not save raw private backup contents, router account identifiers, decryption passwords or approvals to this public document or a PR.

## Options, without choosing or deploying a storage destination

| Option | Benefit | Correlated failure and trust caveat | Decision |
| --- | --- | --- | --- |
| **A. Encrypted, periodically disconnected removable medium**, stored away from the Fedora laptop | Can survive loss/theft/corruption of the whole Fedora computer; operator can practice restore on another machine | Requires trusted physical custody, an independent decryption secret, reliable update cadence and test of spare-reader/tool availability. An attached USB drive in the same computer during an incident is not reliably independent | **Preferred design candidate** if a separate removable device and safe custody are available |
| **B. Independently administered second host or authenticated off-site object repository**, encrypted client-side | Off-host failure-domain separation and potentially more frequent backups; usable when local machine is unavailable | Requires external access, availability, independently recoverable credentials and immutable/versioned deletion controls; online compromise or ransomware can affect both if the same credentials have write/delete access | **Viable alternative** after verifying independent administration and restore access |
| **C. Existing second internal NVMe / same-host Restic snapshots** | Helpful against individual drive corruption and for routine restore | Same laptop, battery/power/controller/theft, account and recovery access can fail together; scope of current backups unproven | **Supporting tier only — not enough for this failure goal** |
| **D. Production ASUS SSD, JFFS, or current RouterCloud data store** | Physically outside Fedora in some cases | Mixing authorization, recovery and live gateway can introduce boot/DNS/security dependencies, existing projects' permission conflicts, and lack of proven encrypted independent custody | **NO implicit use; would require a new separately reviewed architecture and approval** |

**No purchase requirement implied:** option A or B is a design choice and may use appropriate already-owned equipment *if* independently verified. This document does not infer what removable media, NAS, cloud credentials or storage the operator currently owns.

## Required proof before saying independent recovery PASS

1. **Location and failure-domain mapping** — demonstrate different physical host/medium or normally disconnected custody; not merely distinct inode, `st_dev`, Btrfs subvolume, mounted filesystem or attached NVMe.
2. **Source provenance** — exact preserved *full hook* and DNS Guard SHA-256, file type, mode and metadata, recorded in a nonsecret offline verification sheet. A checksum alone does not authenticate an untrusted issuer; compare to the source reviewed in the Issue #235 evidence.
3. **Encryption and key availability after Fedora failure** — ensure key/passphrase and trusted verification software are accessible from another clean device without needing data left solely on the failed laptop. Never print secret contents/paths into logs or conversation.
4. **Recovery independence** — a disposable restore on another suitable host or a live Fedora lab explicitly simulating unavailable primary path, with no router contact. Demonstrate the full hook and guard bytes can be recovered and verified; no publication to `/jffs` or root-owned live locations.
5. **Retention and update policy** — a controlled version/generation and provenance record for any new backup, explicit rollback of old *data copies only*, and bounded disaster recovery testing. Do not repurpose PR #245 synthetic generation/approval.
6. **Approval separation** — V2.7 future independent operator approval record and protected launcher are **not** co-generated from candidate files, no same-UID writable policy/keyring and no automatic production GO after restoring files.
7. **DNS/boot/JFFS2 gates unchanged** — even perfect source recovery does not prove safe runtime quiescence, writer FD drain, JFFS2 crash behavior or DNS continuity.

## Operator decision — V2.10 is optional, not the immediate Issue #235 workstream (2026-10-20)

The operator explicitly deprioritized making another backup and requested returning to the two privileged-script **owner/trust repair**. This memo remains a **contingency design**, not a prerequisite to continuing *offline security engineering*. Do not perform a new storage inventory, purchase, Restic profile change, file copy or restore rehearsal under Issue #235 without a distinct request.

**Current related Fedora Recovery scope, based on the completed 2026-10-19 recovery checkpoint:** encrypted Restic copy on a separate internal physical NVMe with verified isolated restore for system root, `systemd-machines`, `/boot` and EFI; the separately mounted `/home` was outside that recovery scope. Therefore the two existing private `$HOME/issue235-*-backup-*` copies **are not established as included** in the finalized Fedora Recovery set. Do not rewrite its profile to include them and do not assume RouterCloud's separate staging backup covers them. This is a **scope finding based on prior operator evidence**, not a newly opened/revalidated live Restic snapshot.

**Security gate interpretation:** source-byte integrity of both private primary copies has already passed V2.8; further external redundancy is deferred but the missing independently usable *post-host-loss* recovery remains a documented **residual risk and production-approval gap**. Design review can proceed; a root-owned staging/apply GO cannot be inferred from this decision. Future intentional acceptance of residual loss exposure must be distinct and explicit.

**Active engineering priority:** [two-target trusted publisher and full execution-source isolation](issue235-two-target-trusted-publisher-design-2026-10-20.md), covering old nonroot writable file/FDs, root-Cron, primary WAN events, full `services-start` boot/manual dispatch, emergency DNS break-glass, root-only source/object binding and JFFS2 interruption. Do not duplicate V2.0–V2.9 abstract tests or reuse PR #245 SSD approvals.

## Recommended controlled next stage

**V2.10 DESIGN COMPLETE; APPLY NOT APPROVED.** The highest-value next action is to **choose an independent recovery destination**, then separately approve creation of one encrypted copy and a disposable restore proof. Avoid another generic SHA self-test; V2.8/V2.9 already established current primary source and filesystem relationship. If no independent medium/host exists yet, record `OFF_HOST_RECOVERY=HOLD` and stop, rather than counting an internal SSD or current Restic instance as an external backup.

```text
V28_PRIMARY_BACKUP_BYTES=PASS_AT_READ_TIME
V29_OPERATOR_METADATA=PASS
V29_PRIMARY_COPY_DEVICE_RELATION=SAME_ST_DEV
V210_RECOVERY_TARGET=DESIGN_OPTIONS_ONLY
V210_PHYSICAL_OFF_HOST_COPY=NOT_CREATED
V210_INDEPENDENT_DECRYPTION_AND_RESTORE=NOT_TESTED
V27_INDEPENDENT_OPERATOR_APPROVAL=NOT_ISSUED
TRUSTED_TWO_TARGET_PUBLISHER=NOT_IMPLEMENTED
PRIVILEGED_EXECUTION_TRUST_GATE=HOLD
DEPLOYMENT_GATE=HOLD
```
