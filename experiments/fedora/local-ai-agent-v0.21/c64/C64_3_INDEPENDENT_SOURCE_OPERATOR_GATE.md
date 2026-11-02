# C.64.3 — independent source claims and operator review gate (synthetic only)

**Status: Draft / NO_NETWORK / DEPLOYMENT_GATE=HOLD / MODEL_ACTION_AUTHORITY=NONE.**

C.64.3 joins two **independent fictional datasets** entirely in process memory: C.64.2's synthetic port-8428 listener/process metadata assessment and C.64.1's mock HTTP responses. Neither reaches a local host service.

This is a **contract validation lab**, not authenticated source correlation. The objects need not refer to the same machine, process, timeframe or incident. Even internally consistent samples cannot prove listener ownership, DNS health, root cause or authorization for a live read.

## Local commands (standard user; no sudo)

From the repository root:

    SCRIPT=experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_3_independent_source_operator_gate.py
    python3 -B "$SCRIPT" --self-test
    python3 -B "$SCRIPT" --synthetic-matrix
    python3 -B "$SCRIPT" --summary-json --scenario fd_denied
    python3 -B "$SCRIPT" --summary-json --scenario loopback_match --review-code ACKNOWLEDGE_OFFLINE_FINDINGS

The CLI has **no live data mode, systemd read, filesystem input, external URL, arbitrary PromQL or command execution**. It does not invoke C.64.2 local metadata inspection or C.63.8.1's existing live mode.

## Synthetic scenarios

| Scenario | Fictional condition | Expected gate outcome |
|---|---|---|
| fd_denied | Unreadable descriptor directory; VM mock baseline consistent | HOLD_FD_ACCESS_DENIED |
| loopback_match | Positive fake socket match, synthetic samples look valid | HOLD_SOURCE_NOT_ATTESTED |
| owner_mismatch | Wrong or unconfirmed socket owner | HOLD_OWNER_NOT_ESTABLISHED |
| wildcard_bind / nonlocal_bind | Non-loopback listener | HOLD_NONLOCAL_BIND |
| no_listener | No listener | HOLD_NO_LISTENER |
| inactive_service | Inactive service | HOLD_SERVICE_NOT_ACTIVE |
| stale_metric / missing_metric | Unqualified VM sample | HOLD_UNQUALIFIED_SYNTHETIC_SAMPLES |
| invalid_guard | DNS Guard validity flag zero | HOLD_UNQUALIFIED_SYNTHETIC_SAMPLES |
| ipv6_loopback | IPv6 loopback, descriptor access denied | HOLD_FD_ACCESS_DENIED |

The fd_denied scenario is fictional and resembles the *classification* from the user's actual C.64.2 preflight; it does not load that host output or read /proc.

## Review-code semantics

The simulation-only values are UNREVIEWED (default), ACKNOWLEDGE_OFFLINE_FINDINGS (test acknowledgment of **fictional** data), and DECLINE_FURTHER_REVIEW (maintains HOLD). There are no APPROVE, ENABLE_LIVE, RUN_MODEL or REMEDIATE codes. A fake acknowledgement is not real operator approval or an authentication credential.

## Independent input validation

The evaluate_inputs() Python function can receive caller-provided in-memory dictionaries. Strict validations check the exact C.64.2/C.64.1 schemas, field types, whitelisted source labels, consistency of counts, classifications and fixed fictional timestamps, and forced safety invariants. Unknown keys, forged authority, missing fields and contradictory source data fail closed.

**Successful structure validation never establishes provenance.** A caller could forge plausible objects. Outputs therefore always state:

- input_objects_are_authenticated=false
- source_identity_cryptographically_attested=false
- independent_inputs_prove_same_process=false
- sources_are_same_evidence=false
- cross_source_causality_established=false
- review_code_authenticated=false
- live_http_authorized=false

Other invariants: HTTP_REQUESTS=0, MODEL_REQUESTS=0, QUALITY_GATE=ABSTAIN_NO_MODEL_INFERENCE, DNS_HEALTH=NOT_ESTABLISHED, ROOT_CAUSE=UNDETERMINED, MODEL_ACTION_AUTHORITY=NONE, REMEDIATION_AUTHORIZED=false and DEPLOYMENT_GATE=HOLD.

Outputs are bounded, fixed codes and small counts; no raw service command line, PID, inode, private IP, credential, VM payload or journal entry is emitted.

## Tests and limits

50 tests cover source/authority spoofing, extra fields, contradictions, timestamps, invalid gaps, process metadata uncertainty, operator-code refusal, network/model isolation and file-write absence. CI also executes C.64.0, C.64.1 and C.64.2 regressions.

This lab **cannot validate** real socket identity, operator identity or consent, genuine source authenticity, production sampling freshness, or real-world service behavior. An artificial positive socket match cannot override the actual Fedora FD_PERMISSION_DENIED HOLD.

## C.64.0–C.64.3 integration checkpoint

See [REVIEW_C64_0_3_INTEGRATION.md](REVIEW_C64_0_3_INTEGRATION.md) for stacked PR ancestry verification, cross-stage contract validation, risk register and the **manual-only** proposed merge sequence. The additional source-only integration suite is `local_ai_agent_v021c64_0_3_integration_contract_offline.py`; it remains synthetic, offline and non-authorizing.

## PR dependencies

This is a stacked Draft based on PR #358 (C.64.2), which follows PR #355 (C.64.1) and PR #354 (C.64.0). The independent diagnostic PR #353 remains separate.

No live reads, merges, sudo, privilege changes, Qwen calls, executor actions, repairs or deployment are authorized.
