# Local AI Agent — C.64.0 synthetic VictoriaMetrics adapter

**Experimental, offline-only code. No production data. No live VM connectivity.**

This module composes the existing **C.63.8.1** bounded VictoriaMetrics JSON parser with an **in-memory synthetic provider**. It exercises eight independent VM-like envelopes (four fixed metric names, each paired with a value and a raw sample timestamp) and produces a small, sanitized machine-readable summary.

The fictional evaluation clock is **2030-02-13 09:00 Europe/Warsaw**. It is not a historical incident window or production recording.

## Run

From the repository root:

```bash
python3 -B experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_0_synthetic_vm_envelope_adapter.py --self-test
python3 -B experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_0_synthetic_vm_envelope_adapter.py --fixture-matrix
python3 -B experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_0_synthetic_vm_envelope_adapter.py --summary-json --scenario baseline
```

The only accepted `--scenario` values are `baseline`, `stats_envelope`, `missing_local`, `stale_local`, `future_local`, `stale_collection`, `contradictory_flags`, and `invalid_guard`.

## Security and interpretation

- The CLI **never calls the C.63.8.1 network fetch function**. All eight CLI JSON envelopes are generated directly in RAM; there is no arbitrary URL, query, file path, payload, or host data input.
- When the Python `assess_packets()` API is called directly with caller-supplied VM-shaped bytes, it returns `CALLER_PROVIDED_VM_LIKE_BYTES_ORIGIN_UNVERIFIED` and `OFFLINE_VM_ENVELOPE_VALIDATION_ONLY`. Only `scenario_summary()`, which itself constructs the selected fictional fixture, labels the origin synthetic. Neither path attests to a real source or grants model access.
- The existing C.63.8.1 parser rejects unknown labels, extra series, duplicate keys, malformed envelopes, nonfinite values, skewed evaluation clocks and oversized responses.
- Strict sets, byte caps and a fixed evaluation clock prevent silently dropping, adding or replacing metric queries.
- An SHA-256 fingerprint identifies the *ordered synthetic bytes only*. It is **not** a cryptographic attestation of real-source origin.
- The output contains **no actual metric values, raw messages, private IP addresses or agent commands**.
- The response is **not an atomic snapshot**. A valid synthetic mode flag is **not proof of DNS health, network recovery, or root cause**.
- Every scenario remains `ABSTAIN_NO_MODEL_INFERENCE`, `MODEL_ACTION_AUTHORITY=NONE`, `REMEDIATION_AUTHORIZED=false`, and `DEPLOYMENT_GATE=HOLD`.
- The `--self-test` suite is intentionally self-contained and has no network, subprocess, model or filesystem-writing step.

## Acceptance

The new `agent-c64-offline.yml` workflow checks the existing C.63 manifests and runs the C.64 self-tests, fixture matrix, and structured JSON invariant checks. This does not grant approval for host telemetry access, any deployment, Qwen inference or repairs.

## Preliminary security review

See [REVIEW_C64_0_PRE_C64_1.md](REVIEW_C64_0_PRE_C64_1.md) for the documented, **non-sign-off** source/contract review, remaining trust-boundary risks and C.64.1 design acceptance gates.

## C.64.1 mock HTTP transport lab

The follow-on stacked Draft branch includes [C64_1_MOCK_TRANSPORT.md](C64_1_MOCK_TRANSPORT.md), a 40-test in-memory transport contract suite and dedicated GitHub Actions verification. **This is still offline-only**: no live telemetry option, no socket calls and no deployment authorization.

## Next stage (design only)

A *separate*, explicitly authorized reader may eventually use a fixed loopback-only VictoriaMetrics endpoint, strict source freshness bounds and operator-controlled execution. Such a reader must keep unverified provenance separate from syntactic validity. It must not silently swap this synthetic provider for live data, and it requires a separate security review and an explicit operator acceptance gate.

This C.64.0 branch is **independent** of the open PR #353; the two changes must not be merged or deployed implicitly together.
