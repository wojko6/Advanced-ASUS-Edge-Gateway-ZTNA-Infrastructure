# C.64.1 mock HTTP transport — pre-live safety review

**Date:** 2026-11-02  
**Scope:** C.64.1 mock-only transport (stacked Draft PR #355) and its C.64.0/C.63.8.1 dependencies.  
**Disposition:** `PASS_OFFLINE_TEST_CHECKPOINT` for the mock-only lab; `HOLD` for real host queries, model inference, any remediation, merge and deployment.  
**Review type:** preliminary source/contract inspection, **not** an independent human security audit or production sign-off.

## 1. Evidence reviewed

- The operator ran the C.64.1 tests on Fedora: `C641_TESTS=40 STATUS=PASS_OFFLINE`, and the 16-scenario matrix: eight `PASS_MOCK` cases and eight `EXPECTED_HOLD` cases.
- The synthetic baseline returned `transport_requests=8`, `transport_closed_connections=8`, `transport_method=GET_ONLY`, `source_identity=SCRIPTED_HTTP_CONNECTIONS_IN_MEMORY_NOT_REAL_VM` and `destination_contract=FIXED_127_0_0_1_8428_NOT_CONTACTED`.
- GitHub Actions `c641-mocked-transport` passed 40/40 C.64.1 tests, 34/34 C.64.0 regression tests, upstream C.63 source manifest checks, all 16 matrix scenarios and JSON invariants at commit `29e696d2e1edaccdf4e2e9c206ec3b1190fdb892`.
- The code invokes C.63.8.1 `vm.fetch()` with an explicit injected fake `factory`. Its CLI has `--self-test`, `--mock-matrix` and `--summary-json` only; there is no C.64.1 live option.
- The *separate pre-existing C.63.8.1 script* has an explicit `--live-vm-readonly` option. The C.64.1 CLI does not exercise it. Passing C.64.1 tests **does not authorize** running the C.63.8.1 live option.

## 2. Threat-boundary assessment

| ID | Assessed condition | Evidence/limitation | Required before a real read |
|---|---|---|---|
| T-01 | Mock-to-real escalation | The injected factory is the core mock boundary. C.63.8.1 `vm.fetch` has a default real `HTTPConnection` argument bound at import time; patching only the global class cannot prove its default path is unreachable. The C.64.1 regression checks `factory` on all eight calls and patches socket entry points, but mocks are not a system-level network sandbox. | Implement an independently reviewed, manually invoked live observer with no hidden fallthrough from the mock CLI; confirm system-level network confinement where appropriate. |
| T-02 | Local endpoint identity | `127.0.0.1:8428` is the fixed destination of the existing C.63.8.1 client. Localhost alone does not authenticate the actual listener, its process owner or its data. | Confirm listener ownership/permissions via separate read-only host inspection and retain `NOT_CRYPTOGRAPHICALLY_ATTESTED` absent independent proof. |
| T-03 | HTTP responses and redirects | Non-200 statuses, including simulated redirects, are rejected. The existing C.63.8.1 client does **not** validate response `Content-Type`, `Content-Length` or headers as an authentication mechanism. | Decide whether header validation is required; add explicit rejection tests and clearly distinguish header consistency from source authentication. |
| T-04 | Time and atomicity | C.64.1 tests a fictional clock in 2030 and eight independent GETs. The results are not an atomic sample, and synthetic clock/freshness success does not validate a real clock. | Capture a bounded real UTC evaluation clock, preserve raw `timestamp()` values, collection freshness, skew and non-atomic semantics; prohibit causal or recovery claims. |
| T-05 | Timeouts and resource limits | C.63.8.1 uses a 3-second per-connection timeout and 8192-byte per-response read cap. Mock timeouts do not reproduce all real HTTP/network delays; there is no proven end-to-end 8-request deadline. | Define total-run deadline and bounded failure output. Test timeouts, partial data, stalled reads and process interruption with an isolated setup. |
| T-06 | Output minimization/privacy | The mocked summary carries fixed classification/gap codes and a byte fingerprint but no raw JSON. A fingerprint is byte identity, **not chain-of-custody evidence**. | Establish a redaction/output schema; audit for raw labels, IPs, journal content, credentials and accidental traceback leakage under real errors. |
| T-07 | Model and action authority | Tests verify zero model requests, no remediation, `ABSTAIN_NO_MODEL_INFERENCE`, `ROOT_CAUSE=UNDETERMINED`, `DNS_HEALTH=NOT_ESTABLISHED`, and `DEPLOYMENT_GATE=HOLD`. | Carry these as enforced invariants into any separately approved reader. No Qwen call, tool execution, router modification or service restart may be inferred from a successful read. |
| T-08 | Repository integrity/dependency | C.64.1 is stacked on Draft PR #354. The passing source tests do not provide independent third-party security approval; a locally modified checkout or untrusted Python dependency can bypass assumptions. | Review exact commit SHAs of both PRs, check a clean local checkout and inspect dependency/import paths; obtain human approval before any change in scope. |

## 3. Required independent operator gate for any eventual live-read pilot

All of the following must be **explicitly approved in a separate step**. This document is not that approval.

1. Authorize only a **single, operator-triggered, read-only observation**, with a clearly named standalone command (not `C64.1 --summary-json` silently switching to live).
2. Restrict the destination to `127.0.0.1:8428`; allow only the four already reviewed DNS Guard series names and their matching timestamp queries, exactly eight GETs and no user-controlled PromQL, redirects, proxies or remote targets.
3. Inspect who owns the local VictoriaMetrics listener and whether a process can impersonate it. Treat all samples as **source claims** without cryptographic provenance.
4. Fix response-size, overall-run time, timeout, JSON-shape, timestamp and freshness bounds. Reject partial, missing, stale, contradictory or unexpected data without guessing.
5. Keep outputs bounded, redacted and **unattested**; never publish raw production logs in public repositories or PR fixtures.
6. Keep `DEPLOYMENT_GATE=HOLD`, `MODEL_ACTION_AUTHORITY=NONE`, `ABSTAIN_NO_MODEL_INFERENCE`, `REMEDIATION_AUTHORIZED=false`, `ROOT_CAUSE=UNDETERMINED`, `DNS_HEALTH=NOT_ESTABLISHED`, and `model_requests=0`.
7. Prove that the proposed pilot performs no writes, no process restarts, no router calls and no model requests; review the exact script and commit before execution. Use an isolated mock/protocol-fault test before contacting the live endpoint.
8. After the pilot, independently evaluate whether results justify any further integration. Do not equate "HTTP 200" or a fresh mode sample with "DNS healthy", a root-cause diagnosis, or permission for remediation.

## 4. Release and merge boundaries

| Item | State |
|---|---|
| C.64.1 mock-only lab and offline test results | **PASS_OFFLINE_TEST_CHECKPOINT** |
| C.64.1 actual VictoriaMetrics access | **NOT_IMPLEMENTED / NOT_AUTHORIZED** |
| Real-source identity and response-header security claims | **NOT_ESTABLISHED** |
| Model inference, agent actions, fixes, operational diagnosis | **NOT_AUTHORIZED** |
| PR #353, PR #354 and stacked PR #355 | **DRAFT / NO_AUTOMATIC_MERGE** |
| Deployment gate | **HOLD** |

This document records review findings and required acceptance criteria. It neither changes a production service nor grants any permission to conduct a live read.
