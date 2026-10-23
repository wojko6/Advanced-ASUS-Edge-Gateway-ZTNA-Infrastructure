# Issue #235 — two privileged script targets: trusted publication authority design (2026-10-20)

> **Status:** DESIGN CANDIDATE / NOT A RUNBOOK / `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD` / `DEPLOYMENT_GATE=HOLD`.
> **Targets only:** active **full** `/jffs/scripts/services-start` and `/jffs/addons/asus-edge/bin/dns-guard`.
> **Not authorized:** any router write, chown/chmod, Cron/NVRAM edit, hook rewrite, service restart, reboot, generic installer, or changes to the separately managed SSD/DUFS/RouterCloud tracks.

## Problem and decision

Both target files were observed **nonroot-owned but owner-writable** despite point-in-time matches to independently reviewed source bytes. Firmware `run_custom_script` checked execution bits but not root ownership in the reviewed GNUton tagged source, while a named root-Cron target and direct WAN/emergency code paths can invoke DNS Guard. See the [privileged trust maintenance design](issue235-privileged-startup-trust-maintenance-design-2026-10-20.md), [services-start evidence](../../evidence/2026-10-20/issue-235-services-start-trust-chain-v14-v17.md) and [DNS Guard evidence](../../evidence/2026-10-19/issue-235-dns-guard-root-cron-trust-and-rollback.md).

**Candidate decision:** evaluate a *separately trusted* publisher that creates **new root-owned, correct-mode inodes from pinned, independently authenticated source bytes**, binds the checked object to the published pathname without exposing unverified bytes, and repairs **one target at a time**. Do not rely on an in-place `chown` of a previously writable inode or on a last-second hash of the old live pathname.

This proposal requires an actual trusted identity boundary, filesystem-specific interruption proof and safe DNS recovery. It is **not accepted for production**.

## Roles and trust boundaries

| Role | May do | Must not do / evidence gap |
| --- | --- | --- |
| Off-router evidence authority | Review the precise *currently active* full hook and DNS Guard bytes; issue a versioned, authenticated digest/manifest; retain independent recovery copies | Do not treat past single-time checksums as source immutability, and do not publish private copies or security-sensitive identifiers |
| Isolated transfer/importer | Deliver authenticated inputs to a staging area whose **identity, contents, ancestry and permissions** are verified by the trusted publisher | No untrusted-UID writable directory or mutable basename can be part of the publish handoff; a signed receipt alone does not enforce directory DAC |
| On-router trusted publisher (**not built**) | As separate trusted/root authority, create root-owned `0755` regular single-link candidate in a private root-controlled JFFS directory; verify provenance and exact inode/bytes/mode; publish only one approved target per separately controlled transition | Cannot grant root publication to HTTP/RouterCloud user, original nonroot owner, shell snippets from unknown provenance, or generic installer; no claim of race-free handoff until mechanism reviewed |
| Independent safety/recovery operator | Maintain LAN recovery and independently verified DNS fallback; approve every maintenance transition; verify live behavior after publication | Must not quietly disable WAN/break-glass, automatically resume after interrupted publish, silently roll back to original nonroot ownership or assume a normal-boot journal is a preboot guard |

**Proof obligations:** root-exclusive staging/parent ownership must be demonstrable *during* publication; the publisher's executable and startup chain must not depend on the compromised ownership boundary; ordinary group/other mode bits alone are not proof of no ACL/xattr bypass or other authorized writers. An FD hash does **not** pin the source basename for later `rename` if any adversary can rewrite that basename; [V2.3](../../evidence/2026-10-20/issue-235-fd-to-name-publication-race-v23.md) reproduced this intentionally under one UID.

## Reuse of prior work (without cross-project edits)

- **Issue #235 previous isolated tests:** operator-reported, Fedora-only rootless / three-role UID, same-FD handoff / copy-verify, pinned source, signed offline approval, external importer Stage B, ARMv7 trust helper and negative matrices. These demonstrate *test patterns*, **not** a deployed publisher for these two targets. They must be individually matched to source artifact/version and exact target-specific assumptions before being cited as acceptance. **Not re-run in this work.**
- **Separate [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) / [JFFS Stage B draft](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/blob/security/issue235-ssd-mount-mode-post-mount-lab-20261015/docs/issue235-jffs-staging-activation-rollback-runbook-draft.md):** useful review patterns include allowlisted file targets, exact source pinning, root-owned root-only staged materials, collision refusal, post-stage identity verification, and independent recovery. They address SSD root modes and **must not be installed, edited, merged or treated as direct proof of trust repair** for `services-start` / DNS Guard.
- **V2.0–V2.3 synthetic results:** [V2.0 crash model](../../evidence/2026-10-20/issue-235-dual-target-quiescence-model-v20.md) 20/20 operator Fedora, [V2.1 monotonic model](../../evidence/2026-10-20/issue-235-monotonic-two-target-model-v21.md) 19/19 operator Fedora, [V2.2 inode fixture](../../evidence/2026-10-20/issue-235-rootless-file-inode-publish-v22.md) 19/19 operator Fedora and [V2.3 FD/name race](../../evidence/2026-10-20/issue-235-fd-to-name-publication-race-v23.md) 20/20 operator Fedora, including expected-red exposure. They **do not** add a deployable mechanism or demonstrate real JFFS2 power-cut behavior.

### V2.4 recovered-source decision for REUSE_REVIEW

The [V2.4 archive/source cross-check](../../evidence/2026-10-20/issue-235-trusted-publisher-evidence-gap-review-v24.md) has now recovered and independently SHA-256-checked selected historical **Stage B v1.3/v1.4/v1.5 C/Python source files** against their recorded design-report pins. Additional V1.1, importer and V1.6 sources were located in the operator's file Library. This advances **`REUSE_REVIEW=SOURCE_BYTES_RECOVERED_FOR_SELECTED_ARTIFACTS`**, not `TRUST_ROOT=PASS` or `FD_BINDING=PRODUCTION_ACCEPTED`.

**Nontransferable approval scope:** the recovered Stage B contract concerns *three synthetic roles for SSD PR #245*, with a literal policy scope `pr245-ssd-mount-roots`. Neither the V1.4 independently held synthetic approval FD nor the V1.5 synthetic signer/keyring tests authorize a different, **two privileged-script** deployment. V1.5 explicitly demonstrates that a same-UID process that controls policy and keyring can subvert the simulated approval. A new independently reviewed operator authority and target-specific content/provenance map would be required; old PR #245/SSD inputs must remain untouched.

## V2.5 historical C/ZIP prerequisite (scope remains PR #245)

[V2.5 fixed-input read-only audit](../../evidence/2026-10-20/issue-235-original-c-zip-provenance-v25.md) records the exact original 18,074-byte Canonical Manifest C pin and its expected ZIP. The operator independently ran the fixed-path Fedora-only preflight against both historic inputs: original SHA-256 **EXACT_MATCH**, ZIP C bytes **EXACT_MATCH**, unique synthetic baseline **PASS**, exit 0, with **10/10 synthetic self-tests**. This resolves only original lab source identity, not the new two-target approval/publisher trust. No substitute sources were generated. **Even verified original C bytes remain solely a PR #245 lab dependency**, not approval to modify either privileged Issue #235 script.

## V2.6 — target-specific scope contract (no inherited SSD authority)

The [V2.6 synthetic contract](../../evidence/2026-10-20/issue-235-two-script-approval-contract-v26.md) establishes a **distinct schema** `ISSUE235-TWO-SCRIPT-APPROVAL/1` with exact scope `issue235-privileged-scripts-owner-repair`, and only two fixed ordered roles: the **existing full** `/jffs/scripts/services-start` plus `/jffs/addons/asus-edge/bin/dns-guard`. Mode `0755`, owner `root:root`, regular/single-link, source hashes and target paths must be independently authenticated by a new protected offline authority before any production consideration.

A purely in-memory Fedora-compatible validator **29/29 local PASS** correctly *rejects* PR #245 scope `pr245-ssd-mount-roots`, swapped/missing/extra roles, nonroot ownership, bad mode, changed synthetic source bytes, and revoked/stale approval. Its one accepted case is **synthetic only**; no real files were read or published, independent approval is not implemented. **DO NOT transplant the PR #245 authorizer or reuse its manifest as script owner-repair permission.**

## V2.7 — independent offline approval authority, not a privileged publisher

The [V2.7 approval authority design](issue235-two-script-offline-approval-authority-v27-2026-10-20.md) separates proposal bytes from a new operator-controlled, independently protected approval for exact scope `issue235-privileged-scripts-owner-repair`. The selected **review candidate** is a separately controlled approved manifest SHA-256 (option A), not yet issued. Signing alternatives require separate key governance; FD/approval record syntax does not authenticate the caller. Any future technical publication remains gated by root-only staging, no competing writable FDs, JFFS2 recovery and all DNS fail-open protections. **No GO and no cross-scope PR #245 reuse.**

## Three distinct failure boundaries — do not conflate

| Boundary | What is partially demonstrated | Missing real proof |
| --- | --- | --- |
| Before publication | Root-owned JFFS ancestor directories seen in **point-in-time** audits; reviewed source and private Fedora backup bytes | A trusted root-only publisher/stage which excludes any adversarial stage entry/content writer; stable identity and trusted source freshness |
| During publication | Linux fixture shows one-path name replace and retained old FD; wrong source basename race reproduced | A secure object-to-published-name handoff on the exact firmware/JFFS2; absence/coordination of old owner writers, already running root scripts, open script descriptors, Cron/WAN/manual triggers |
| After interruption/reboot | Abstract guard-first partial state leaves one untrusted boot-hook launch class; two-file atomicity **not** claimed | Persistent single-file publication durability, recoverable mixed states, ability to prevent unacceptable early-boot execution or to document/accept its **remaining** risk; safe Unbound/Pi-hole/DNS Guard/independent break-glass availability |

**Crucial constraint:** an ordinary JFFS `init-start` hook cannot simply be claimed a trusted pre-boot barrier; it uses the same checked-only-for-exec firmware script dispatcher. Global `jffs2_scripts=0` or Cron deletion would break or bypass important recovery paths and is not approved. Guard-first is only a **hypothesis for evaluating fewer modeled untrusted launcher classes after interruption**, not an approved order or safety probability.

## V2.8 independent recovery audit checkpoint

The [V2.8 read-only Fedora copy audit](../../evidence/2026-10-20/issue-235-recovery-copy-separation-v28.md) examines the existing off-router `services-start` and DNS Guard bytes under hidden operator-supplied local paths. Local **18/18** synthetic tests passed, but no actual Fedora backup-path replay or independent restore has been reported. Matching SHA and private file modes constitute point-in-time **input integrity only**. The script explicitly reports `INDEPENDENT_FAILURE_DOMAIN=NOT_PROVEN_BY_LOCAL_PATH_CHECKS` even if an optional second loose-file copy resides on a different filesystem. Independent Restic/offline restore, external credentials, approval custody, old-FD writer exclusion and JFFS2 crash recovery still require distinct evidence and approvals.



## V2.9 — physical failure-domain recovery still unproven

The [V2.9 metadata-only Fedora-loss assessment](../../evidence/2026-10-20/issue-235-independent-recovery-failure-domain-v29.md) supplements already PASS V2.8 primary-copy integrity, not real source byte attestation or restore. Local **9/9 self-tests** and disposable directory fixtures passed; operator Fedora scan pending. A second `st_dev` or separate SSD within the same computer is not sufficient evidence of independent off-host recovery. RouterCloud Restic staging is not known to include the two private script copies, while separate Fedora Recovery has **unverified #235 file coverage**. No new backup, approval authority, restore, production staging or permissions were changed.

### V2.10 workstream correction and immediate security priorities

The operator chose **not to create another backup as an immediate #235 activity**. V2.8 verified the existing primary Fedora copies point-in-time; V2.9 found both on `SAME_ST_DEV`. The completed Fedora Recovery set from 2026-10-19 covers root, `systemd-machines`, `/boot`, EFI and not a separately mounted `/home`; script backup inclusion there is therefore **not established**. The [V2.10 optional recovery choices](issue235-independent-script-recovery-options-v210-2026-10-20.md) remain deferred. The residual independent disaster-recovery gap is **not accepted as safe production deployment**.

**Focus instead on three real trust boundaries, not more synthetic hash/copy checks:**

1. **Execution suppression proof:** determine whether the actual GNUton firmware exposes a *separate, trusted, selective* mechanism to prevent all privileged boot/manual `services-start` and root-Cron/WAN/break-glass executions while maintaining effective DNS, before any potentially interrupted transition. Prior pinned source review found no such early-boot guard. Do not claim an ordinary JFFS `init-start` or global `jffs2_scripts=0` is one.
2. **Publisher authority and source identity:** establish a separately authorized, root-controlled importer and stage which bind independently authenticated two-script bytes to the **same inode published**. The previously observed nonroot owner or another same-UID process must not be able to modify the candidate basename, trust store, stage, policy or already opened old source FD. V2.3's expected-red stage basename swap remains a fail-closed gate.
3. **Failure/recovery mechanism:** precisely specify who can enter while Cron/WAN/boot hooks are inhibited; model a hard power cut after either individual publication on real compatible JFFS2 or explicitly retain a manually supervised NO-GO. Never present two single-name changes as one atomic transaction, or restore original nonroot owner-writable entrypoints.

**Engineering status:** offline feasibility review can progress. `TRUSTED_ROOT_PUBLISHER=NOT_BUILT`, `EARLY_BOOT_INHIBITOR=NOT_PROVEN`, `OLD_WRITABLE_FD_QUIESCENCE=NOT_PROVEN`, `JFFS2_POWERLOSS_RECOVERY=NOT_PROVEN`. No security GO or router access.

### V2.11 source-backed feasibility checkpoint

[Review of pinned GNUton boot and project dispatch](../../evidence/2026-10-20/issue-235-gnuton-dispatch-inhibition-feasibility-v211.md) confirms the *documented limitations* of Cron-only inhibition, cooperative `services-start` lock, independent WAN and emergency DNS Guard callers, untrusted normal JFFS `init-start`, and an installer that would turn the reviewed full firmware hook into a short wrapper. None is a root-owned publisher or crash-durable selective pre-execution gate. **Do not perform direct `chown`, Cron deletion, generic installer or name-only staging.** V2.10 additional backup remains optional/deferred. The next phase is a genuinely trusted firmware dispatcher/source identity and root publisher feasibility review, not another abstract lock/hash model.

### V2.12 first-party upstream dispatcher and `_eval` evidence

The [fresh tag-pinned GNUton source review](../../evidence/2026-10-20/issue-235-gnuton-firmware-launch-trust-boundary-v212.md) independently fetched source Git blobs for `run_custom_script`, `_eval`, `rc/services.c`, `rc/init.c`, and `cru`. The kernel-executed script path is checked with `stat` for **any** execute bit, then the child executes **the name again** via `execvp`; no same-FD or digest binding is visible in that chain. The `cru` lock protects crontab writing, not all DNS Guard dispatch. This source-level finding strengthens the **HOLD** for any old-owner in-place `chown` and name-based publish scheme; it is *not* attestation of the live router binary. To progress, an earlier trusted execution policy/protected publication boundary must actually be implemented and shown on the correct target model before considering production. No firmware patch or deployment requested.

## Decision states, proof gates and next engineering action

**V2.10 next recovery boundary:** [independent post-host-loss recovery choices](issue235-independent-script-recovery-options-v210-2026-10-20.md) are a design comparison only; no off-host medium or actual restore approved. V2.9 Fedora 9/9 PASS found both private backups on `SAME_ST_DEV`, not independent physical recovery. Trust authority, old-owner writer/FD exclusion, exact GNUton/JFFS2 publication and DNS safety gates are unchanged.



1. **REUSE_REVIEW:** inventory actual earlier isolated helper/FD/importer test artifacts and **explicitly tag** each `REUSABLE_PATTERN` / `NOT_TARGET_VALIDATED` / `UNVERIFIED`. Do not claim a missing artifact passed because a worklog mentions an earlier test.
2. **PROVENANCE:** independently protected recoverable source for *both* scripts; reviewed exact bytes and ownership expectations; cannot depend solely on SSD or local Fedora failure domain.
3. **TRUST_ROOT:** identify how authenticated sources enter a private, root-only JFFS staging area; demonstrate that the importer/publisher executable, keys/receipts, staging directory, source basename and checked inode cannot be modified by the observed old nonroot owner or an unrelated writable service.
4. **FD_BINDING:** independent review of the checked-byte/inode-to-publication handoff and replacement/collision semantics, including child namespace/parent path pinning. Negative race tests must fail closed *before* any unverified content is exposed to root dispatch.
5. **INTERRUPTION:** for each target, test interrupted local same-filesystem publish, persistence boundaries and recovery **on a representative disposable JFFS2/ARMv7 environment** where feasible; ordinary Fedora ext4/Btrfs `fsync` is not sufficient to prove physical router loss behavior.
6. **QUIESCENCE + DNS:** define independent, reliable LAN recovery and fail-open DNS plus the permitted/blocked behavior of boot `services-start`, named Cron, WAN-connected calls and operator break-glass; prove absence/drain of active writers/FDs. If no safe selective isolation exists, remain `NO-GO` rather than silently disabling all DNS recovery.
7. **OPERATOR ACCEPTANCE:** only once every gate is supported can a *separate* reviewed, narrowly authorized production staging and apply procedure be drafted. No script, command, checkmark, synthetic pass or PR merge constitutes such approval.

**Current decision:** `TRUSTED_PUBLISHER_BUILT=NO`, `JFFS2_CRASH_DURABILITY=NOT_PROVEN`, `EARLY_BOOT_INHIBITOR=NOT_PROVEN`, `RECOVERY_MEDIA_INDEPENDENCE=NOT_PROVEN`, `LIVE_DNS_RECOVERY=NOT_APPROVED_FOR_TEST`, `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.

Separate RouterCloud/DUFS HTTP-origin and privilege-drop issues retain their own scope and approvals; this document does **not** imply [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) overall is closed.
