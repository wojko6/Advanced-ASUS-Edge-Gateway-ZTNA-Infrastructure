# C.64.0 → C.64.1: bounded security review and acceptance gates

**Review class:** preliminary source/contract review, 2026-11-02.
**Disposition:** `HOLD` for live data, production deployment and autonomous remediation.
**Review scope:** C.64.0 branch source and its reused C.63.8.1 VM parser only. This note is **not an independent human security audit, provenance attestation or production sign-off**.

## Verified from the reviewed source and available CI

- C.64.0 has a fixed, public, synthetic 2030 fixture and eight explicit VM-like envelopes (four whitelisted series names × value/raw sample time). Its CLI does not expose a URL, file upload, arbitrary query or arbitrary evidence input.
- `assess_packets()` caps the input to the exact eight keys and bounded bytes, reuses C.63.8.1's strict JSON/envelope validation and does not invoke a transport function. Direct caller-provided bytes retain `CALLER_PROVIDED_VM_LIKE_BYTES_ORIGIN_UNVERIFIED`; only the internal fixture generator uses the synthetic source label.
- The test suite covers malformed/duplicate JSON, bad labels and nonfinite values, freshness gaps and clock mismatch, flag contradictions, authority invariants, absence of model calls, and explicit mocks against C.63 fetch/observe and socket connection attempts.
- C.63.8.1 contains an **already existing explicit** `--live-vm-readonly` mode. C.64.0 does **not** invoke this option and does not activate it. Reusing its parser is not a permission to run its live mode.
- On 2026-11-02, GitHub Actions `c64-offline` passed **34/34** unit tests and the eight-case matrix at branch head `466d1cd9a1cc14d2727576d022d10e459e71a6d2`; the operator separately reported **34/34 PASS** on Fedora. Those outcomes validate these fixtures and checks, not real-source authenticity or operational resilience.

## Remaining risks and interpretation boundaries

| ID | Open issue | Required disposition before live data |
|---|---|---|
| G-01 | A loopback HTTP listener is not cryptographically authenticated. Another local process or misconfiguration could supply plausible samples. | Treat transport as *source-claimed*, not attested. Verify and document the endpoint owner using independent operator checks, or retain an explicitly unverified result. Never let successful HTTP imply authentication. |
| G-02 | C.63.8.1 performs eight separate GETs; the results are not an atomic snapshot. | Preserve evaluation time, raw sample timestamps and cross-series skew; do not infer a network outage, recovery or root cause from non-atomic samples. |
| G-03 | C.64.0 hardcodes a fictional evaluation clock in 2030; it does not implement the contract for a real host clock. | Implement a separate C.64.1 bounded wall-clock adapter with clock/time consistency tests, not by changing the meaning of synthetic C.64.0 outputs. |
| G-04 | Output fingerprint covers ordered bytes, not chain of custody or host identity. | Never expose `SHA-256 verified` as `source attested`. Consider operator-controlled source metadata with explicit `UNVERIFIED` semantics. |
| G-05 | Provenance and quality checks are separate from model eligibility. | The eventual real-source quality gate must remain `ABSTAIN_NO_MODEL_INFERENCE`; reject any attempt to transfer the separate C.63.6 synthetic baseline readiness into live observations. |
| G-06 | Running Python from a locally modified checkout or shadowed import path expands the trust boundary. | Require a clean, reviewed commit and independent scope/permissions check before any live read. CI checksum tests for the existing C.63 files are not a runtime binary/source attestation. |
| G-07 | Dedicated offline tests do not exercise DNS, process restart, SELinux denials, unexpected service responses or multi-day real-world behavior. | Include explicit controlled fault injection and resource limits in an isolated environment; obtain a separate human review before operator-initiated read-only observation. |

## C.64.1 proposed design — not yet authorized or implemented

**First implementation target:** a standalone, explicitly operator-invoked, **read-only local VM observer** that produces a bounded **UNVERIFIED source observation**, never a health verdict.

1. Entry point has an exact `--local-vm-readonly` opt-in; no autostart, timer, daemon, webhook, HTTP listener, background task or user-configurable host/query.
2. Only `127.0.0.1:8428`, four fixed DNS Guard metrics, eight value/timestamp queries, a fixed GET-only path format, ≤3-second per-request timeout and ≤8192-byte per-response reads (limits inherited from reviewed C.63.8.1 until explicitly re-reviewed). No redirects, proxies, arbitrary queries, path parameters, sudo or router connections.
3. On error, reject oversized/partial/malformed/multi-series/duplicate/unknown responses. Keep source authenticity `NOT_CRYPTOGRAPHICALLY_ATTESTED`; retain non-atomicity, freshness and sample alignment constraints.
4. Output only whitelisted codes, durations, missing-data reasons and tightly bounded non-sensitive metadata. Do not emit raw query bodies, series labels from untrusted sources, private addresses, credentials, router configuration or original journal messages.
5. Regardless of sampled DNS Guard mode, output `DNS_HEALTH=NOT_ESTABLISHED`, `ROOT_CAUSE=UNDETERMINED`, `ABSTAIN_NO_MODEL_INFERENCE`, `MODEL_ACTION_AUTHORITY=NONE`, `REMEDIATION_AUTHORIZED=false` and `DEPLOYMENT_GATE=HOLD`.
6. No Ollama/Qwen request, tools, executor, service restart, file write, systemd update, remote router action or monitoring configuration mutation.
7. Test both mocked successful responses and failures (HTTP status, socket denial, timeout, partial content, unexpected headers/body, clock skew, stale values, untrusted source labels, replay). Tests must show **zero** router/model calls and explicit fail-closed results.
8. Include a separate **manual operator acceptance step** before enabling any real read, and another independent security/privacy review before considering a deployment or model integration.

## Decision

- **C.64.0 synthetic adapter:** test checkpoint `PASS` only.
- **C.64.1 real telemetry adapter design:** defined for future review, **not authorized or implemented** by this document.
- **Live source identity, real DNS health, root cause and repair rights:** `NOT_ESTABLISHED` / `NONE`.
- **Repository merges:** PR #353 and PR #354 remain separate Drafts; neither gets auto-merged by this review.

`NO_NETWORK_FOR_C64_0=YES` · `MODEL_ACTION_AUTHORITY=NONE` · `DEPLOYMENT_GATE=HOLD`
