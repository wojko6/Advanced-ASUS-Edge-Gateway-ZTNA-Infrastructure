# C.64.1 — injected local VictoriaMetrics HTTP transport contract (mock-only)

**Status: laboratory only / DEPLOYMENT_GATE=HOLD.** The CLI never opens a real TCP connection. No actual VictoriaMetrics, router, journald, Loki, Ollama, Qwen or system service is contacted.

This stage tests the *transport behavior* required before a separately approved live read. Unlike C.64.0 (direct in-memory JSON parsing), C.64.1 invokes the existing C.63.8.1 `vm.fetch()` client **only with an explicitly supplied in-memory connection factory**. That factory implements enough of `HTTPConnection` to check the GET contract and return fictional responses. It never creates a socket.

It uses C.64.0 for fictitious envelopes, the strict source parser and source-identity safeguards. Consequently C.64.1 is submitted as a **stacked Draft PR based on the branch of Draft PR #354**, not independently on `main`.

## Exact commands (from repository root)

```bash
SCRIPT=experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_1_mocked_vm_transport_contract.py
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --mock-matrix
python3 -B "$SCRIPT" --summary-json --scenario baseline
```

Only explicitly named simulation scenarios are available; there is **no `--live` option**, alternate destination, user-defined query, file upload or automatic scheduling.

## Checked transport contract

- Expected destination: `127.0.0.1:8428`, **not contacted** during this lab.
- Eight sequential `GET` requests for four fixed DNS Guard metrics and their original sample timestamps.
- Exact `Accept: application/json` and `Connection: close` request headers, fixed PromQL query expression and evaluation clock.
- Three-second connection timeout contract; up to 8192 JSON bytes per answer, bounded byte reads and explicit connection closure.
- Reject unexpected status (including redirect), timeout, excessive response, malformed JSON, duplicate keys, foreign metric labels and refused mock connection.
- Eight positive laboratory scenarios + eight expected-failure transport/parsing scenarios.
- Explicitly mark each success as `SCRIPTED_HTTP_CONNECTIONS_IN_MEMORY_NOT_REAL_VM`, with **unattested source identity** and non-atomic observations.
- The existing C.63.8.1 parser does **not** validate HTTP response content-type. The result explicitly reports `response_headers_verified=false`; no source-authenticity or complete HTTP header-validation claim is made.
- Even good simulated samples always preserve `ABSTAIN_NO_MODEL_INFERENCE`, `DNS_HEALTH=NOT_ESTABLISHED`, `ROOT_CAUSE=UNDETERMINED`, `MODEL_ACTION_AUTHORITY=NONE`, `REMEDIATION_AUTHORIZED=false` and `DEPLOYMENT_GATE=HOLD`.

## Test and review limitations

Mock connection objects are useful for request-contract testing but are **not a proof that real socket, proxy, service, timeout or system-clock behavior is safe**. Tests exercise a fake transport; no production response or private log is included. Successful SHA-256 fingerprints only establish identity of fictional response bytes, never chain of custody.

The code is **not** a production reader, a new agent executor or a model inference route. Before any actual local VM read, obtain separate operator approval and review source authenticity, local listener ownership, SELinux confinement, network isolation, response header behavior, freshness, sampling skew, resource bounds and failure reporting. See `REVIEW_C64_0_PRE_C64_1.md` for the prior gate review.

### Relationship to other drafts

- **PR #353:** synthetic diagnostic CLI, independent and still Draft.
- **PR #354:** C.64.0 synthetic envelope adapter and preliminary security review, still Draft.
- **C.64.1:** this mock-only transport lab, **stacked on top of PR #354**; no merge, deployment or implicit elevation of permission.
