# C.64.1 → first controlled VM read: preliminary security gate

**Date:** 2026-11-02  
**Scope:** Local AI Agent v0.21 C.64.1 simulated transport and reused C.63.8.1 reader only.  
**Status:** **LAB PASS; LIVE READ HOLD**. This is a preliminary source-level assessment, **not** an independent human security review, provenance attestation, or production approval.

## Verified laboratory evidence

- The owner reported successful Fedora checkout and **50/50** C.64.1 tests, the eight-scenario matrix and an offline baseline result on 2026-11-02.
- The latest reviewed C.64.1 GitHub Actions workflow passed **50/50** tests, matrix and JSON invariants; all nine check runs were green on head `ee36fa3ea3b53a584ca59cb835330eff45e970eb` before this documentation-only update.
- The C.64.1 entrypoint has no real-read CLI switch; its eight GET calls are handled by a bounded in-memory fake connection factory, not by the network stack. The simulated socket target string is not a real connection.
- The fake response tests require fixed GET method, fixed query paths and headers, eight response slots, a read-size cap, and closure of all fake connections. Simulated 503, 302, timeout, refusal, oversized/malformed/duplicate/partial/nonfinite JSON and evaluation-time errors fail closed.
- The fake clock remains **2030-02-13** and does not establish host-clock validity.
- All output retains `ABSTAIN_NO_MODEL_INFERENCE`, `DNS_HEALTH=NOT_ESTABLISHED`, `ROOT_CAUSE=UNDETERMINED`, `MODEL_ACTION_AUTHORITY=NONE`, `REMEDIATION_AUTHORIZED=false`, and `DEPLOYMENT_GATE=HOLD`.

## Findings and outstanding controls

| ID | Source-level finding | Requirement before any live observation |
|---|---|---|
| H-01 | In-memory fake transport cannot establish actual process identity or localhost service ownership. | Operator checks owner, executable, service unit and listener binding separately; capture only non-sensitive summary, never credentials or raw logs. Treat service identity as **unverified** until independently justified. |
| H-02 | Tests constrain the *fake* 2030 clock; they do not cover host time jumps or suspended/resumed operation. | Separate bounded wall-clock check, monotonic interval for run duration, raw sample freshness and explicit time-skew failure. |
| H-03 | The existing C.63.8.1 live mode is an independent entrypoint, not invoked by C.64.1. | No accidental/implicit execution. Require a distinct operator-approved invocation and an explicit `--local-vm-readonly` gate in a **separately reviewed** module. |
| H-04 | Eight sequential GETs cannot establish an atomic snapshot or full health. | Keep source evidence non-atomic and unauthenticated; no inference of outage, recovery or root cause, even after eight clean responses. |
| H-05 | The fake factory is an in-process test double, not a security sandbox. | For any live operation, separately constrain endpoint, address family, redirects, proxies, timeouts and response bytes at the actual transport boundary; test denied connections and resource limits. |
| H-06 | A SHA-256 test fingerprint can establish test-byte identity, not a chain of custody. | Source labels and trust metadata must not be inferred from parsed payload content or a matching hash. |
| H-07 | A well-formed response may still contain stale or incorrect metric claims. | Retain strict per-series raw sample time, collection timestamp, cross-series skew and independent quality-gate abstention. |
| H-08 | A successful read of DNS Guard mode cannot grant model/executor authority. | Keep `MODEL_ACTION_AUTHORITY=NONE`, `model_requests=0`, `remediation_authorized=false` and `DEPLOYMENT_GATE=HOLD` as mandatory invariants. |

## Next operator-only preflight (no VM HTTP query)

Before writing or invoking a live reader, obtain a **minimal, operator-run** Fedora report for the local service's existence and listener identity; exclude full command lines, environment, access tokens, logs and internal network addresses other than the fixed local endpoint.

A possible read-only preflight is:

```bash
printf 'VICTORIAMETRICS_SERVICE='
systemctl is-active victoriametrics || true
printf 'VICTORIAMETRICS_UNIT='
systemctl is-enabled victoriametrics || true
printf 'VM_LOOPBACK_LISTENER='
ss -H -ltn '( sport = :8428 )' |
  awk '$4 == "127.0.0.1:8428" {found=1} END {print found ? "PRESENT" : "NOT_CONFIRMED"}'
```

These commands do **not** read metric values or validate the listener's owner. A matching TCP listener alone does not authenticate VictoriaMetrics. No production service, monitoring configuration or firewall rules should be modified by this step.

## Explicit stop condition

**Do not run** the existing C.63.8.1 `--live-vm-readonly` option, call the VM HTTP API, enable a systemd unit, deploy Qwen, or change router configuration as part of this PR. A separate security/privacy review and operator approval are required before any live data access. Both source and operator acceptance gates stay **HOLD** until those conditions are met.

**Decision:** C.64.1 = `PASS_SYNTHETIC_TRANSPORT_ONLY`; live telemetry gate = `HOLD`.
