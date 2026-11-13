# Local AI Agent C.64.2 — explicitly gated, read-only local VM observer

**Status:** standalone Draft lab. Source review candidate; **not** an independent security audit, production approval, or deployment.

This module reuses the existing C.63.8.1 strict parser to examine four fixed DNS Guard metric series via eight ordered value/raw timestamp requests. Unlike C.64.1, the code includes an **explicit, manually selected** local VictoriaMetrics observation path; it is never invoked by tests, imports, clones or default execution. **Do not activate that path yet.** We first validate offline tests, documentation and privacy/review boundaries.

## Operator-reported preflight (2026-11-02)

On Fedora the operator reported: `victoriametrics.service` active/running and enabled; listening only at `127.0.0.1:8428`; the listener PID matched systemd's MainPID; the service was running under a dedicated `victoriametrics` account. This is an operator observation at one point in time. No PID, private filesystem records, logs, or credentials are embedded in the lab. Matching a PID does **not** provide cryptographic source authentication, and does not authorize reads.

## Offline acceptance commands

From the repository root:

```bash
SCRIPT=experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_2_manual_local_vm_gate_lab_v01.py
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --fixture-matrix
python3 -B "$SCRIPT" --summary-json --scenario baseline
```

Every command above is **synthetic-only** and uses a fictional fixed 2030 evaluation clock.

## Manual live-mode design — do not invoke during this stage

A separate `--local-vm-readonly` entrypoint is present for security review only. It **requires both explicit acknowledgment flags** and does not permit synthetic scenario selection with live mode. Its target, metrics, query paths, HTTP method, response-size caps and 3-second transport timeout derive from the reviewed C.63.8.1 source. It additionally checks run duration (≤24 s) and large discrepancies between wall and monotonic elapsed time (≤5 s). It is not a secure hardware/software attestation or an OS sandbox.

Any future live execution requires **another operator decision** after reviewing the exact CLI command, the updated source, the CI status and service identity. **Do not copy or run a guessed live invocation now.**

In all modes the summary preserves:

- `source_authenticity=NOT_CRYPTOGRAPHICALLY_ATTESTED`; even a matching loopback listener is not evidence of an authenticated source.
- `ABSTAIN_NO_MODEL_INFERENCE`, `DNS_HEALTH=NOT_ESTABLISHED`, `ROOT_CAUSE=UNDETERMINED`.
- `MODEL_ACTION_AUTHORITY=NONE`, `model_requests=0`, `remediation_authorized=false`, `DEPLOYMENT_GATE=HOLD`.
- No raw body/labels, private IPs, secrets, journal excerpts, operator actions, router commands or model requests in its output.
- Eight sequential GETs are **not** an atomic snapshot. Neither good-looking samples nor a successful HTTP response prove DNS health.

## Caveats

- No cryptographic guarantee of endpoint identity, nor external chain-of-custody proof.
- A human operator remains responsible for checking the process owner and source policy.
- A bounded synchronous reader cannot guarantee absence of all environmental side effects (e.g. network accounting), only that it performs no intentional mutations or repairs.
- Offline mocks do not prove correct performance against actual transient network failures, malicious listeners, SELinux, or long-lived operations.
- This branch is independent of Draft PRs #353, #354 and #356. No auto-merge, service installation or host config edits are proposed.

**LIVE_READ_GATE=HOLD** until explicit operator approval and independent review.
