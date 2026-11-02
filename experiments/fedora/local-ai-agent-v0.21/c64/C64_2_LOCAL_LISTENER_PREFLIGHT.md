# C.64.2 — local VictoriaMetrics listener identity preflight (no HTTP)

**Draft laboratory workflow. Manual inspection only.**

The operator may explicitly run this tool on Fedora to inspect the local TCP listener for port **8428** and cross-check it with the **victoriametrics.service** systemd unit. It **does not query VictoriaMetrics**, open a socket, execute curl, contact the ASUS router, invoke Qwen or write any files. The goal is to identify blockers before a separately approved one-shot read.

## Commands

From the C.64.2 repository checkout:

    SCRIPT=experiments/fedora/local-ai-agent-v0.21/c64/local_ai_agent_v021c64_2_listener_identity_preflight.py

    # Pure synthetic tests; no local machine inspection.
    python3 -B "$SCRIPT" --self-test

    # Explicit local metadata inspection; still NO HTTP requests.
    python3 -B "$SCRIPT" --inspect-local-listener

Run with the regular user account. **Do not use sudo.** Do not paste raw system logs, process command lines, socket inodes or private IP addresses into a public GitHub issue. The tool emits only bounded, classified counts and status codes.

## Data sources and limits

- **/proc/net/tcp and /proc/net/tcp6:** read-only, bounded to 1 MiB per table; inspect only LISTEN sockets with local port 8428. Classifies loopback, wildcard and other non-loopback bindings; omits actual addresses and socket inodes from JSON output.
- **systemctl --no-pager show --property=MainPID --property=ActiveState victoriametrics.service:** fixed local unit metadata query, 3-second timeout, no shell. Never reads or prints ExecStart or any environment/credentials.
- **/proc/<MainPID>/fd:** read-only descriptor symlink checks for a matching socket inode, capped at 4096 descriptors. Permission denial, process races, a different owner, absence of listener or uncertain state must not be interpreted as identity proof.
- **Safety invariants:** model_requests=0, http_requests=0, MODEL_ACTION_AUTHORITY=NONE, REMEDIATION_AUTHORIZED=false and DEPLOYMENT_GATE=HOLD in each successful JSON report.

## Interpretation

| Result code | Meaning | Action |
|---|---|---|
| OBSERVED_LOOPBACK_MAINPID_SOCKET_MANUAL_REVIEW_ONLY | A loopback listener and the service MainPID's matching socket descriptor were observable in this local process snapshot. | Manual review only; **not source authentication or permission to issue HTTP GETs**. |
| HOLD_NONLOCAL_BIND_PRESENT | At least one wildcard or non-loopback listener appears bound to 8428. | Review service exposure separately; do not use as proof of safe local-only binding. |
| HOLD_NO_LISTENER | No TCP LISTEN socket at 8428 was observed. | Do not infer why the service is unavailable; inspect independently. |
| HOLD_SERVICE_NOT_ACTIVE | systemd did not report active service with a nonzero MainPID. | Do not proceed to live data. |
| HOLD_LISTENER_OWNERSHIP_UNCONFIRMED | The process link could not be confirmed, e.g. rootless permissions or process race. | Do not use sudo automatically; request a distinct operator-authorized investigation. |
| C642_RESULT=HOLD_... | A bounded inspection stage failed (read/parse/timeout). | Treat as insufficient evidence. |

**Important limitations:** a local socket can be impersonated by another local process; socket/process metadata is not cryptographic attestation of VictoriaMetrics or of its underlying telemetry. /proc and systemd are not a synchronized snapshot. A container/network namespace may limit what the observer sees. PID reuse or a rapidly changing listener may invalidate a snapshot. The absence of a non-loopback binding does not prove broader system isolation or firewall effectiveness.

## Review gates before any future real read

1. Run and independently inspect the preflight output. Do not change any service in response to this script.
2. Resolve any non-loopback binding, unknown process ownership or permission limitation in a separate review.
3. Design a standalone, explicitly operator-triggered **one-shot GET-only** command; do not add a silent live path to C.64.0/C.64.1.
4. Re-check total deadline, response caps, strict series allowlist, JSON/headers policy, freshness/clock skew, provenance status and redacted output.
5. Preserve ABSTAIN_NO_MODEL_INFERENCE, ROOT_CAUSE=UNDETERMINED, DNS_HEALTH=NOT_ESTABLISHED, MODEL_ACTION_AUTHORITY=NONE, DEPLOYMENT_GATE=HOLD, and no automated actions.
6. Require a separate independent human security/privacy review and explicit owner approval **before** any actual HTTP GET.

**Branch stacking:** this C.64.2 Draft is based on C.64.1 Draft PR #355, which depends on C.64.0 Draft PR #354; the separate diagnostic Draft PR #353 remains out of scope. No automatic merges.
