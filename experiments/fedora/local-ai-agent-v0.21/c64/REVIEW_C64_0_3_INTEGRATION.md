# C.64.0–C.64.3 integration review — stacked Draft checkpoint

**Date:** 2026-11-02
**Scope:** GitHub ancestry, file-level diffs, and offline Python contracts.
**Decision:** OFFLINE_REVIEW_ONLY / DEPLOYMENT_GATE=HOLD / NO_MERGE_AUTHORIZATION.
**Assurance:** preliminary integration review, not independent human security/privacy sign-off.

## 1. Verified PR topology

| PR | Area | Base | Reviewed parent head | Status |
|---|---|---|---|---|
| #354 | C.64.0 synthetic VM envelope parsing | main | main | OPEN DRAFT |
| #355 | C.64.1 mock-only HTTP transport | #354 branch | 6f964c0c82a85ed0f5f39552d02aa490ef9e08fb | OPEN DRAFT |
| #358 | C.64.2 local process metadata preflight | #355 branch | 7c52805975402319744a8e6dfe59600bf50b215a | OPEN DRAFT |
| #359 | C.64.3 synthetic independent-source HOLD gate | #358 branch | f24c8ba397ad84a2da5e8d4894561a5287b4a3b8 | OPEN DRAFT |
| #353 | Separate synthetic diagnostic entrypoint | main | main | OPEN DRAFT, outside this stack |

GitHub commit comparisons of each consecutive pair returned status=ahead, behind_by=0 and merge base equal to the parent's head commit. This verifies the current linear branch ancestry, not future mergeability or conflict-free rebases.

PR #353 modifies the agent entrypoint and its own workflow; PRs #354/#355/#358/#359 modify C.64 stage sources and stage workflows. No file-path overlap was observed with PR #353. This does not authorize a functional connection between the two implementations.

## 2. Integration architecture

C.64.3 uses C.64.2.evaluate() with fabricated /proc-like and systemd-like metadata and C.64.1.run_mock() with fake HTTP objects. C.64.1 reuses C.64.0.assess_packets() and the pinned C.63.8.1 parser. It must always inject the mock HTTPConnection factory. The preexisting C.63.8.1 explicit live mode is out of scope.

The C.64.2 explicit --inspect-local-listener is not invoked by the C.64.3 synthetic CLI.

The only C.64 README modification across parent stages is the C.64.1 documentation link. C.64.2/3 add files, while this integration checkpoint adds a new test and this report on the **existing PR #359**. No additional PR was created.

## 3. Cross-stage regression test and CI

The new file local_ai_agent_v021c64_0_3_integration_contract_offline.py provides 20 additional isolated unit tests. It checks:

- Exact C.64.2 and C.64.1 producer/consumer field parity with C.64.3.
- C.64.0–C.64.1 parity of eight synthetic scenarios (classifications, modes, gaps, safety labels, ordered byte fingerprints).
- The equal SHA-256 of two fictitious response streams is not provenance attestation.
- The rootless FD permission-denial case remains HOLD even if fake VM samples look complete.
- A fictional positive listener socket match still produces HOLD_SOURCE_NOT_ATTESTED.
- All eleven C.64.3 scenarios under all three synthetic review-code values remain HOLD.
- Missing fields, fake attestation, fabricated approval, a changed clock, and synthetic digest replacement cannot grant rights.
- Mock guards block real host metadata, socket, subprocess and file reads/writes along the synthetic integration path.
- Cross-source data never establishes DNS health, root cause, process identity, causal correlation or live access.

Execute from repository root:

    SCRIPT=experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_0_3_integration_contract_offline.py
    python3 -B "$SCRIPT" --self-test
    python3 -B "$SCRIPT" --summary-json

The existing C.64.3 workflow on PR #359 is extended to run these tests after all four stage suites. No new workflow and no new PR were introduced.

The existing 34+40+48+50=172 stage unit tests and the new 20 tests total **192 offline unit tests**. This count does not constitute independent security approval or a real-host validation.

## 4. Open security gaps and blockers

| ID | Blocker | Mandatory handling |
|---|---|---|
| I-01 | On the real Fedora host, rootless /proc/MainPID/fd access was denied. | Preserve HOLD_LISTENER_FD_ACCESS_DENIED; do not elevate permissions to bypass it. |
| I-02 | Simulated local process metadata and fake HTTP responses are two independent fictional inputs. | Keep source authentication, shared-process claims and cross-source causality false. |
| I-03 | SHA-256 of ordered bytes is not chain-of-custody or authenticated process identity. | Retain NOT_CRYPTOGRAPHICALLY_ATTESTED and avoid attested labels. |
| I-04 | Synthetic evaluation clock points to 2030, not a real event. | Do not infer production freshness, health, recovery or root cause. |
| I-05 | Reused C.63.8.1 fetch has a real default HTTPConnection argument bound at function definition. | Require a fake injected factory on every C.64.1 call; do not use pre-existing live mode. |
| I-06 | Operator review codes in C.64.3 are not authenticated approval. | ACKNOWLEDGE_OFFLINE_FINDINGS never enables live GETs, model inference or repair. |
| I-07 | PR #353's agent facade is independent and not coupled to C.64. | Require a separate human-reviewed contract before later integration. |
| I-08 | CI can be green on different commits while the stacked bases change. | Review exact target SHAs, changed files and CI again after every retarget/rebase. |

Other unresolved areas include local listener authenticity, read-only host identity checks, real HTTP headers/redirects, total-request deadline, non-atomic GETs and output privacy under actual failures.

## 5. Proposed merge sequence — NOT EXECUTED

1. Keep all five PRs in Draft. Obtain human code/security/privacy review and explicit permission before any merge.
2. If approved, review #354 against current main and merge only its intended synthetic source changes; do not activate a service.
3. Retarget/rebase #355 onto updated main, review its **delta only** and rerun CI; obtain separate approval before merge.
4. Repeat the same controlled process for #358, preserving the unverified socket-ownership HOLD.
5. Retarget/rebase #359 last; rerun all contract tests on the exact resulting SHA, review its intended delta and obtain approval.
6. Review #353 independently; physical co-location in main is not evidence of a safe coupling.

Never merge the full stacked head directly into main to bypass the separate approvals and review of each predecessor.

## 6. Final disposition

- Existing isolated C.64.0–C.64.3 tests: PASS at their prior reviewed heads.
- New offline integration checkpoint: requires dedicated CI and optional operator self-test on the exact updated PR #359 head.
- Production telemetry access: NOT_AUTHORIZED.
- Live source identity and process identity: NOT_ESTABLISHED.
- DNS health/root cause: NOT_ESTABLISHED/UNDETERMINED.
- Ollama/Qwen inference, remediation or privilege escalation: NOT_AUTHORIZED.
- PRs #353, #354, #355, #358, #359: all remain OPEN DRAFT; no merge operations performed.

MODEL_ACTION_AUTHORITY=NONE
REMEDIATION_AUTHORIZED=false
DEPLOYMENT_GATE=HOLD
