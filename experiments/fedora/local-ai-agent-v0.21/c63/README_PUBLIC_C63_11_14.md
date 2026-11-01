# C.63.11–C.63.14 — PUBLIC SYNTHETIC review candidate

**State:** Draft / five synthetic source artifacts uploaded and checksum-verified. **Not a deployment.** `DEPLOYMENT_GATE=HOLD`, `MODEL_ACTION_AUTHORITY=NONE`.

This is a **new synthetic-only public fork**, not the original private incident-reading tools.

## Scope

Four modified Python modules (C.63.11–C.63.14) and one clearly synthetic JSON fixture, placed beside the existing 13 C.63 modules merged in PR #347. The synthetic example uses a **fictional 2030-02-13 window**, a **4-qualified/4-unqualified** matrix, invented low event counts, and a documentation-range example SSH host. It does not contain the operator's actual timestamps, counts, log rows or historical JSON.

The public source adapters deliberately **fail closed** on manual VM, journald and operator-stdin modes. Direct public `fetch` and `journal_read` functions also return `HOLD`; no live telemetry or model interaction is needed.

## Validation of the uploaded files (2026-11-01)

```bash
cd experiments/fedora/local-ai-agent-v0.21/c63
sha256sum -c SHA256SUMS
sha256sum -c SHA256SUMS_PUBLIC_C63_11_14.txt
for f in local_ai_agent_v021c63_*.py; do python3 -B "$f" --self-test || exit 1; done
python3 -B local_ai_agent_v021c63_14_operator_incident_report_offline_lab_v01.py --report-bundled-snapshot
```

Verified: **17 modules / 658 offline unit tests PASS**, plus a synthetic report. The workflow `.github/workflows/c63-agent-offline.yml` now requires exactly **17** modules, checks both SHA-256 manifests, and executes only `--self-test`. The GitHub `c63-offline` check passed at the uploaded source commit `a1db868b2b736f2b74c670996ace4707d2b99f52`. The five remotely fetched blob IDs match their checksum-verified local archive bytes.

## Security and merge boundary

Do not publish the original operator incident snapshot or raw logs. Do not imply provenance attestation, DNS health, outage causation or sampling recovery. No router changes, service changes, model actions, CI live probes or auto-merge.

The parent C.63 source path is already in `main` (PR #347). Other historical PRs #343 → #344 → #345 are a separate Draft chain and PR #346 is documentation-only. This PR targets `main`, and remains Draft. The synthetic source upload, checksum verification, bounded offline CI and scoped privacy scan are complete. The independent human security/privacy review and explicit merge authorization are still pending. Historical read-only entry points are intentionally disabled here; older unreachable branches should be reviewed for cleanup before any eventual release.
