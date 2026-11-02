# Local AI Agent v0.21 — unified diagnostic operator entrypoint

**Experimental source only.** `DEPLOYMENT_GATE=HOLD`, `MODEL_ACTION_AUTHORITY=NONE`, `REMEDIATION_AUTHORIZED=false`.

This directory contains one bounded CLI which *composes existing contracts*, rather than adding another live-reading experiment:

1. **C.63.14** validates the bundled fictional 2030-02-13 C.63.13 incident JSON, then derives a sanitized operator-facing incident report. The fixture is not historical operator data.
2. **C.63.6** independently demonstrates the evidence-quality gate on its own fixed synthetic `baseline`. It executes **without** a sender callback, generating **zero** Qwen/Ollama requests.
3. The CLI produces a machine-readable **summary** or human-readable **report**, preserving `ROOT_CAUSE=UNDETERMINED`, `DNS_HEALTH=NOT_ESTABLISHED` and `MANUAL_REVIEW_ONLY`.

**Important distinction:** The C.63.6 `baseline` is **not the C.63.13 incident fixture**. Its readiness cannot be applied to the incident. The incident remains `ABSTAIN_NO_MODEL_INFERENCE`; the demonstration's independent pass never authorizes inference or remediation.

## Run on a checked-out repository

```bash
cd experiments/fedora/local-ai-agent-v0.21
python3 -B agent/diagnostic_agent.py --self-test
python3 -B agent/diagnostic_agent.py --summary-json
python3 -B agent/diagnostic_agent.py --operator-report
```

No `pip install`, model download, network connection, user credentials, existing local service, root privilege or host telemetry is required. The entrypoint also compares the bundled fixture's SHA-256 with the fixed expected digest and fails closed if a still-schema-valid fixture has been changed. The CLI has no arbitrary file path, URL, command or text input. It reads only the public synthetic JSON shipped in the repository.

## Allowed and prohibited behavior

| Topic | Boundary |
|---|---|
| Input | Only bundled, fictional, schema-validated C.63.13 JSON and separate fixed C.63.6 fixture |
| Output | Sanitized bounded fields; no operator logs, SSIDs or private addresses |
| External services | No queries to VM, journald, Ollama, ASUS, Pi-hole or Tailscale |
| Model | `model_requests=0`, `model_invoked=false` |
| Actions | No shell, sudo, subprocess, device or service writes |
| Interpretation | Temporal correlation is **not** proof of an outage, DNS health, root cause or network repair |
| Deployment | `HOLD`; source-only; not a daemon and not production-connected |

## Validation

- Standalone `--self-test` runs fail-closed negative tests for injected keys, gate escalation, authority, provenance, repeatability and mocked network/subprocess denial.
- The separate `agent-diagnostic-offline.yml` workflow validates the C.63 checksum manifests, runs the 17 pinned C.63 `--self-test` suites, tests this entrypoint and verifies key JSON output invariants.
- No historical private incident evidence belongs in this directory or its CI logs.

## Next gate (not implemented)

After independent code/security/privacy review, design an **operator-controlled read-only evidence adapter** with explicit provenance and freshness/quality checks. Do not attach live data to the currently synthetic-only entrypoint and do not grant the model tool/executor authority without a separate explicit design and acceptance gate.
