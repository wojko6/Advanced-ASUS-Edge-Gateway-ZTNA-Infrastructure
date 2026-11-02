# Local AI Agent C.64.1 — fake loopback HTTP transport lab

**Status:** offline transport simulator only. **No real VictoriaMetrics reads are enabled.**

C.64.1 exercises the transport boundary of C.63.8.1, but replaces every HTTP connection with an **in-memory test double**. It does not call `socket.connect()`, open a real HTTP connection, read host telemetry, invoke a model, write files, or modify the router. This work is independent of draft PRs #353 and #354.

## Run on Fedora

From the repository root:

```bash
SCRIPT=experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_1_fake_loopback_http_transport_lab_v01.py
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --fixture-matrix
python3 -B "$SCRIPT" --summary-json --scenario baseline
```

No `--local-vm-readonly` or `--live-vm-readonly` option exists in this new CLI. Do not invoke the separate older C.63.8.1 live option as part of the C.64.1 exercise.

## Enforced simulation contract

- Fictional clock `2030-02-13 09:00 Europe/Warsaw` via `FakeClock`; no host-time access. A two-read fake clock must remain nondecreasing with no more than 24 seconds of elapsed simulated time.
- Eight sequential GETs: exactly four approved metric names × `value` and `timestamp(...)` lookups. Each fake connection verifies host `127.0.0.1`, port `8428`, timeout `3` seconds, exact C.63.8.1 query path, and fixed `Accept`/`Connection` headers.
- The fake response accepts the existing C.63.8.1 max response read of 8193 bytes (the 8192-byte payload cap plus one sentinel byte), then its strict parser and assessor are reused.
- Every fake connection closes. Simulated refusal, timeout, redirect, non-200 status, oversized/empty/malformed/duplicate/nonfinite/partial body, unexpected label and skewed query evaluation time must fail closed.
- Eight scenarios cover valid mocked data, VM stats, absent/stale/future samples, stale collector timestamp, contradictory mode flags and invalid DNS Guard state. None are real observations.
- Output explicitly states `IN_MEMORY_SIMULATED_HTTP_ONLY`, `FAKE_INJECTED_CLOCK`, `FICTIONAL_HTTP_LOOPBACK_SIMULATOR_NOT_REAL_VM`, `real_network_requests=0`, and `operator_authorized_live_reads=false`. There is no claim of authenticated provenance or atomic sampling.
- All cases preserve `DNS_HEALTH=NOT_ESTABLISHED`, `ROOT_CAUSE=UNDETERMINED`, `ABSTAIN_NO_MODEL_INFERENCE`, `MODEL_ACTION_AUTHORITY=NONE`, `REMEDIATION_AUTHORIZED=false`, and `DEPLOYMENT_GATE=HOLD`.

This is a Python **test double**, not an OS network sandbox or a guarantee against malicious code in the checkout. Importing the pre-existing C.63.8.1 module does not authorize executing its live-read CLI. A separate security/privacy review and explicit human approval are required before enabling any live reads.

## C.64.1 verification gate

The `agent-c641-offline.yml` workflow verifies C.63 pinned checksums, 50 tests, the eight-scenario matrix, and structured output invariants. This is **source/test acceptance only**, not release or deployment approval.

## What remains

Any future live-reader design must separately address actual clock provenance/jumps, VM listener identity and access controls, non-atomicity and raw sample freshness, resource exhaustion, and operator authorization. This PR intentionally implements **none** of those live operations.
