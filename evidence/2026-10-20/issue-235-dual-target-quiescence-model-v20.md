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

## Independent operator replay — Fedora, 2026-10-20

The operator independently re-ran the hash-pinned `issue235_dual_target_quiescence_model_v20.py` tool on Fedora using `python3 -B ... --self-test && python3 -B ... --matrix` and provided the entire sanitized terminal output:

- `sha256sum -c` reported **DOBRZE** for the expected local script.
- `SELFTESTS=20/20` and `ALL_TESTS=PASS_OFFLINE_MODEL_ONLY`.
- All eight expected scenarios reproduced: baseline (four unsafe trigger classes); Cron only (three); all hypothetical launchers gated (zero **under assumption**); partial trusted hook followed by reset (three); partial trusted DNS Guard followed by reset (one); reset before first publish (four); assumed persistent barrier (zero **under assumption**); both trusted in abstract model (zero).
- `ASUS_CONTACTED=NO`, `ROUTER_FILES_MODIFIED=NO`, `CRON_MODIFIED=NO`, both privileged-execution and deployment gates `HOLD`.

**Important interpretation:** these are successful **reproductions of the model**, not a live scheduler barrier, physical power-fail test, secure root-ownership transition, real WAN fail-open validation, or evidence of JFFS2 durability. In particular, the `HYPOTHETICAL_DURABLE_BOOT_GATE` scenario **assumes all four launch classes remain blocked** across reboot. That includes **operator break-glass**, which is unacceptable unless an independent, proven DNS recovery mechanism remains usable. The model declares such independent recovery as a Boolean precondition; the operator has **not** proved it exists on the router.

**Ordering observation, not deployment advice:** publishing DNS Guard first leaves one abstract untrusted boot-hook trigger upon a crash, whereas publishing the hook first leaves three untrusted DNS Guard triggers. This supports evaluating **guard-first** as a possible narrower exposure interval *only after* all real quiescence, independent recovery, early-boot and JFFS2 requirements are proven. Trigger counts are not vulnerability probabilities or a production risk score; neither ordering is currently authorized.

The next useful test is **not another repetition of these model assertions**. It is source-backed evaluation of an actual firmware-compatible pre-execution barrier and recovery path; failing that, keep production `NO-GO` and distinguish explicitly between the operator-accepted pre-existing risk and any claimed new safety guarantee.

## New decisive readiness gap

**Even perfect in-memory quiescence is insufficient for safe interruption handling.** If a power failure or reboot occurs between two single-path publishes, firmware may dispatch the still-nonroot-owned privileged target **before** a later recovery controller can run. A conventional journal placed alongside those scripts does not automatically protect the early-boot execution boundary, and a `flock` or named Cron deletion does not gate WAN-connected or break-glass invocations.

A **hypothetical** persistent, privileged, earlier-than-hook boot dispatcher block could change the model outcome, but such a trustworthy GNUton mechanism is **NOT PROVEN**. Nor has a recovery channel been proven that avoids a dangerous early-boot launch on JFFS2.

**Design decision / HOLD:** before any live apply, either prove a specific interruption-safe maintenance approach for *both* privileged targets that does not rely on an unverified pre-boot gate, or explicitly rule out automated rollout and document an operator-mediated recovery strategy with its residual power-loss risk. Do **not** infer that a crash-safe two-file transaction exists on JFFS2; there is no general two-path atomic rename.

## Pinned GNUton firmware source review — trust boundary and potential boot gate

**Source only, no router contact:** inspected the precise GNUton tag `3004.388.11_1-gnuton1` rather than relying on generic Merlin lore.

- [`release/src/router/shared/scripts.c`](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/shared/scripts.c#L54-L88), `run_custom_script`: builds the pathname `/jffs/scripts/%s`, calls `stat`, checks global `jffs2_scripts` not being the literal `0` and checks that **any** user/group/other execute bit is set; then calls `_eval` with the pathname. The reviewed function does **not** check `st_uid == 0`, `st_gid == 0`, group/other writability, regular-file type, link identity, a pinned digest, or a same-FD execution binding. `stat` is a separate lookup before `_eval`, leaving a potential replacement window. **This is a source-level absence of checks in that function, not an exploitation test or full firmware security audit.**
- [`release/src/router/rc/services.c`](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/rc/services.c#L11489-L11510) invokes `run_custom_script("services-start", 0, NULL, NULL)` near its startup completion path. This substantiates the full-hook root-execution design risk. It does **not** prove the exact production invocation timing or rule out platform-specific other callers.
- [`release/src/router/rc/init.c`](https://github.com/gnuton/asuswrt-merlin.ng/blob/3004.388.11_1-gnuton1/release/src/router/rc/init.c#L21139-L21151) invokes `run_custom_script("init-start", 0, NULL, NULL)` earlier in the boot sequence. The [upstream Merlin user-script specification](https://github.com/RMerl/asuswrt-merlin.ng/wiki/User-scripts) places `init-start` after JFFS mounting and before regular services.
- **Crucial design consequence:** adding another ordinary `init-start` hook is *not by itself* a proven trusted durable gate: it, too, is a script in writable JFFS dispatched by the same `run_custom_script` policy without an owner check. A new wrapper/guard may merely relocate the trusted-origin problem; using the global `jffs2_scripts=0` switch is not a selective two-target inhibitor and would impact unrelated recovery hooks. Neither modification is approved.
- `_eval` implementation, permission checks elsewhere in the kernel/process tree, and actual live firmware binary equivalence have **not** been exhaustively verified by this focused review. No root-owned firmware-level owner enforcement or safe pre-boot barrier was established.

**Go/no-go conclusion:** no verified firmware-native, selective, crash-durable early-boot inhibition mechanism has been found by this source review. The V2.0 hypothetical gate must remain hypothetical. Do **not** turn this source review into instructions to disable JFFS script execution, add an `init-start` guard, change NVRAM, or publish either owner repair.

## Remaining no-go requirements

1. Independently protected, recoverable copies for **both** scripts and a trusted source-to-root-owned publish authority.
2. Evidence-backed, independently approvable suppression/coordination of root-Cron, boot/manual `services-start`, direct WAN handler and operator break-glass while maintaining a safe DNS fallback.
3. Writer/FD drain and anti-race guarantees, including trusted parent chains and receipt/lock ownership.
4. A credible **power interruption / early-boot** strategy; no assuming a volatile `flock`, inactive cron schedule or Fedora fixture predicts GNUton/JFFS2 reboot behavior.
5. Review of per-file immutable input binding, phase reconciliation, failure states and rollback that **never restores nonroot-owned privileged scripts**.
6. Explicit change-window staging/apply and separate reboot approvals. No general installer or SSD / DUFS deployment.

**Production verdict:** `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `STAGE_B_C_E_AUTHORIZATION=NOT_GRANTED`, `DEPLOYMENT_GATE=HOLD`.
