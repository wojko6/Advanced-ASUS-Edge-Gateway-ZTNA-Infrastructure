# Local AI Agent C.63.0–C.63.10 — manual laboratory review

**Status:** Draft only. `DEPLOYMENT_GATE=HOLD`, `MODEL_ACTION_AUTHORITY=NONE`. Never enable autonomous remediation.

## Scope

This directory contains 13 SHA-256-pinned source files from the C.63.0–C.63.10 laboratory series, including C.63.3/C.63.3.1 and C.63.8/C.63.8.1. These are manual operator experiments, **not** production services. The historical C.63.11–C.63.14 operator-specific incident report/snapshot, raw system logs, router credentials and private addresses are explicitly excluded.

**Publication status (2026-11-01):** The 13 source files have been added to Draft PR #347. After the upload, their remote Git blob IDs were independently compared with the 13 local checksum-verified archive blobs (13/13 matching). The SHA-256 source manifest is present in the PR. This is publication/integrity verification only, not deployment approval, source provenance attestation, or a sign-off to merge.

## Safety boundary

- C.63.0–C.63.2, C.63.5, C.63.7, C.63.10 and fixtures operate offline. C.63.6 has a manual-only model path after the evidence gate.
- Network-reading modes must be manually requested. C.63.8/C.63.8.1 and C.63.9 query a **local loopback-only** VictoriaMetrics endpoint; C.63.3/C.63.3.1 and C.63.4 can query a **local loopback-only** Ollama service with **synthetic inputs only**.
- No router deployment, sudo, service autostart, repair, executor access, Podman actions, or monitoring-config changes.
- A successful local HTTP GET is **not** authenticated provenance. Fresh raw timestamps alone are **not** DNS health proof, restored telemetry after a gap, or outage causality.
- C.63.3 superseded by C.63.3.1 for the tested 11435 port; C.63.8 superseded by C.63.8.1 for VictoriaMetrics `stats` envelope validation. Older files remain pinned for regression and negative evidence.
- Avoid executing any `--qwen-*`, `--historical-*`, `--live-*`, or `--ollama-preflight` arguments in CI.

## Source verification and bounded offline regression

From this directory:

```bash
sha256sum -c SHA256SUMS
for source in local_ai_agent_v021c63*.py; do
    python3 -B "$source" --self-test || exit 1
done
```

The 13 included sources passed 499/499 manual offline tests on Fedora per operator report and were independently rechecked in a disposable runtime on 2026-11-01. This is source/contract regression evidence only, not a production guarantee.

## Final C.63.10 evidence-label boundary review (2026-11-01)

- The `INSUFFICIENT_EVIDENCE` label alone does not count as a gap. Every declared gap code must match an independently checkable witness *inside the bounded observation report* (missing raw sample timestamp, sample staleness, stale collection value, time mismatch or sample-time spread). Arbitrary or invented gap codes are rejected.
- VM value-dependent conditions that cannot be reconstructed from the bounded report, including contradictory DNS Guard mode flags, are conservatively rejected by C.63.10 rather than interpreted as recovery evidence.
- The source report remains **unattested**: internal consistency checks do not cryptographically authenticate VictoriaMetrics, prove a network outage, identify an incident cause, or authorize model inference.
- After the additional negative tests: **C.63.10 34/34** and **13-module offline suite 507/507** in the disposable test environment. The separate `c63-offline` GitHub check must also pass at the latest commit before review.
- Scoped privacy inspection of the 13 Python source files found no private IPv4 address, email address, PEM private-key block, user account name or actual incident snapshot. One comment references the historical date 2026-10-30 only to clarify that accompanying test fixtures use synthetic 2030 values. This is a limited review, not a comprehensive secrets audit.

## Merge gate

Keep PR as Draft; do not auto-merge. All 13 sources have been staged and their content identities verified against the local archive; the uploader ran 13/13 offline self-tests in a fresh branch clone, and an independent disposable run passed 499/499 offline unit tests. Still pending: final code/security and privacy review, source provenance explanation, parent PR #343→#344→#345 coordination, and explicit reviewer approval. Documentation-only C.62 evidence is tracked separately in Draft PR #346. No CI check runs have been claimed.
