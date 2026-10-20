# Issue #235 — offline dual-target quiescence and crash model V2.0 (2026-10-20)

> **Status:** Fedora-only abstract state machine; **20/20 self-tests PASS** including **expected-red exposures**. Not router execution, integration, ACL/DAC repair, scheduler inhibition, filesystem transaction or JFFS2 crash validation. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.

## Inputs and reviewed constraints

Dated user-reported V1.4–V1.12 evidence established:

- Nonroot-owned, owner-writable **firmware `/jffs/scripts/services-start` hook** with bytes matching pinned full source, and separately **nonroot-owned root-Cron `dns-guard` target** with approved historical source-byte match.
- Privately backed up both target byte streams on Fedora with checksum / private DAC checks. Neither copy is yet proven recoverable if the Fedora failure domain is lost.
- Standard WAN wrapper → addon WAN hook → handler → DNS Guard source chain passes pinned byte comparison, and its ordinary DAC/ancestor metadata passed read-only snapshot. The optional legacy WAN hook is **absent at snapshot**; runtime triggering, ACL/xattrs and future writers are not excluded.
- Direct DNS Guard entrypoints extend beyond Cron: primary-WAN connected handler and operator emergency break-glass. The firmware `services-start` hook can register the root-Cron entry during boot/manual invocation.

This model addresses **privileged execution during a two-target owner-trust remediation window**, not the distinct RouterCloud/DUFS HTTP origin, UID/GID or SSD PR #245 workstreams.

## Artifact and actual local evidence

- Standalone Fedora-only Python script: `issue235_dual_target_quiescence_model_v20.py`.
- Script SHA-256: `6cdf30d4158bb6af1481740e8344718fea05a67aff5f55408d3a0f00b49f1584` (local tested copy).
- Executed `python3 -B issue235_dual_target_quiescence_model_v20.py --self-test`: **20/20 PASS**. Executed `--matrix`: eight scenarios classified, covering baseline, Cron-only inhibition, all assumed inhibitors, first-file-only publication in each order, premature crash, hypothetical persistent early-boot barrier and both-file completion.
- `ASUS_CONTACTED=NO`, `ROUTER_FILES_MODIFIED=NO`, `CRON_MODIFIED=NO` in tool output; no SSH, JFFS, Cron or production path handling in script.
- The model represents trusted ownership as **Boolean state** and launcher blocks as **hypothetical perfect inhibitors**, rather than implementing actual Linux UID changes, hook interception or JFFS2 persistence. The abstract barrier *is not present or approved on the router*.

## Eight state scenarios and outcomes

| Scenario | Model exposure / conclusion |
| --- | --- |
| Initial hook and guard owner-untrusted, no inhibition | **EXPECTED RED** — four modeled classes can execute an untrusted-owned target |
| Only named Cron inhibited | **EXPECTED RED** — boot hook, WAN-connected direct call and operator break-glass classes remain |
| All four class-specific blocks assumed while required drain, recovery and writer gates hold | **Conditional model block only** — no real inhibitor has been implemented |
| Hook trusted, guard still untrusted, then power loss releases volatile blocks | **EXPECTED RED** — Cron, WAN and break-glass calls again expose the guard target |
| Guard trusted, hook still untrusted, then power loss releases volatile blocks | **EXPECTED RED** — boot/manual hook execution remains exposed |
| Power loss before any publication | **EXPECTED RED** — both untrusted-owned targets could again be launched |
| Hypothetical durable **trusted** pre-boot execution barrier | **Conditional model block only** — no source or live proof that firmware can enforce it before invoking compromised-owner hooks |
| Both target owners trusted, then power loss | No *modeled nonroot-owner* hazard, **not** full JFFS2 / DNS service or production acceptance |

PASS in this self-test means the assertions **correctly detect expected unsafe cases** as well as conditional model behavior. It does **not** mean the unsafe cases are fixed.

## New decisive readiness gap

**Even perfect in-memory quiescence is insufficient for safe interruption handling.** If a power failure or reboot occurs between two single-path publishes, firmware may dispatch the still-nonroot-owned privileged target **before** a later recovery controller can run. A conventional journal placed alongside those scripts does not automatically protect the early-boot execution boundary, and a `flock` or named Cron deletion does not gate WAN-connected or break-glass invocations.

A **hypothetical** persistent, privileged, earlier-than-hook boot dispatcher block could change the model outcome, but such a trustworthy GNUton mechanism is **NOT PROVEN**. Nor has a recovery channel been proven that avoids a dangerous early-boot launch on JFFS2.

**Design decision / HOLD:** before any live apply, either prove a specific interruption-safe maintenance approach for *both* privileged targets that does not rely on an unverified pre-boot gate, or explicitly rule out automated rollout and document an operator-mediated recovery strategy with its residual power-loss risk. Do **not** infer that a crash-safe two-file transaction exists on JFFS2; there is no general two-path atomic rename.

## Remaining no-go requirements

1. Independently protected, recoverable copies for **both** scripts and a trusted source-to-root-owned publish authority.
2. Evidence-backed, independently approvable suppression/coordination of root-Cron, boot/manual `services-start`, direct WAN handler and operator break-glass while maintaining a safe DNS fallback.
3. Writer/FD drain and anti-race guarantees, including trusted parent chains and receipt/lock ownership.
4. A credible **power interruption / early-boot** strategy; no assuming a volatile `flock`, inactive cron schedule or Fedora fixture predicts GNUton/JFFS2 reboot behavior.
5. Review of per-file immutable input binding, phase reconciliation, failure states and rollback that **never restores nonroot-owned privileged scripts**.
6. Explicit change-window staging/apply and separate reboot approvals. No general installer or SSD / DUFS deployment.

**Production verdict:** `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `STAGE_B_C_E_AUTHORIZATION=NOT_GRANTED`, `DEPLOYMENT_GATE=HOLD`.
