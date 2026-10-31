# Local AI Agent V0.21 — Fedora-only, read-only analytical checkpoint

**Checkpoint:** 2026-10-30. **State:** isolated manual Fedora laboratory, `DEPLOYMENT_GATE=HOLD`. The scripts in this directory are the selected byte-identical, operator-tested artifacts of the C.48/C.54/C.57/C.58/C.59.1 sequence. This is **not** an installed or remotely accessible application, and is not a router deployment.

## Scope and entry points

| Source | Role | Acceptance boundary |
|---|---|---|
| `local_ai_agent_v021c57_consolidated_vm_loki_readonly_lab_v01.py` | **Primary host collector**; seven fixed local VictoriaMetrics historical range reads, one fixed local Loki count aggregate, input validation, sampled alignment and deterministic Polish draft | Self-contained; operator-reported Fedora `30/30` offline and `PASS_INDEPENDENT_DUAL_SOURCE_HOST_BASELINE_ONLY` |
| `local_ai_agent_v021c58_c57_hcc_c54_compatibility_audit_v01.py` | **Optional compatibility audit**; checks C.57 against frozen HCC offline event model and C.54 evidence schema | Operator-reported `20/20` offline and `PASS_C57_FROZEN_HCC_C54_COMPATIBILITY_AUDIT_ONLY` |
| `local_ai_agent_v021c59_1_ollama_transport_hotfix_shadow_lab_v01.py` | **Qwen SHADOW adapter**; after host preflight sends bounded evidence codes to local Ollama `qwen3.5:4b` | Operator-reported `36/36` offline and `PASS_DUAL_SOURCE_QWEN_SHADOW_ONLY`; no model action authority |
| `local_ai_agent_v021c54_minimal_host_evidence_contract_v01.py` | Standalone, schema-only `incident-evidence.v1` validator used by the optional audit | `38/38` offline in earlier operator run; schema validation is **not** provenance authentication |
| `local_ai_agent_v021c48_frozen_hcc_event_model_parity_lab_v01.py` | Immutable support source embedding the reviewed HCC offline event-model snapshot (`03442de09a6492a20184f3b5f3d60caa18e8ae3e` Git blob SHA-1) | C.58 uses its embedded model. **C.48's own CLI self-test requires its older pinned C.47 dependency, not included in this compact checkpoint** |

All five files are retained **unchanged** to preserve their hardcoded SHA-256 source pins. See [SHA256SUMS](SHA256SUMS). Do not reformat these Python files without explicitly revising pin contracts and rerunning regression tests.

The C.57 primary path does **not** import older C.19–C.56 scripts. C.58 and C.59.1 intentionally retain a *small, pinned audit chain*. Previous experimental scripts have not been deleted from the operator's local laboratory; they are **not** promoted into a live service by this checkpoint.

The first C.59 adapter failed on Fedora with `UnboundLocalError` in `ollama_call()` due to a local `http` name-shadowing bug. C.59.1 corrects it and adds six offline transport regression tests. C.59 must **not** be used as the current SHADOW entry point.

## Data and claims

Historical, fixed-window investigation: **2026-10-27 15:40–16:40 UTC** (16:40–17:40 CET). VictoriaMetrics yielded 61 grid rows: 58 `LOCAL`, three `BOOTSTRAP`, 56 distinct collections and five repeated collections. The bounded Loki count aggregate yielded 15/15 minute bins and **726 Pi-hole log entries**. Source selectors: `dataset="dns-activity"`, `job="dns-activity"`, `source="pihole"`.

Sampled event uncertainty windows (CET):

- `BOOTSTRAP_OBSERVED`: **17:01:35–17:02:39**.
- `LOCAL_RESTORED`: **17:04:48–17:05:55**.

Full-minute counts overlapping these windows total **180** and **37**, respectively. These are **not** counts restricted to the events, DNS success counts, switch timestamps or evidence of causality. No control period, cryptographic source attestation, actual DNS query-path health verification, deployed HCC parity check or atomic dual-source snapshot was performed.

Pinned host JSON checksums observed on Fedora:

- C.57 joint evidence: `557914157204f5b888459efacb4f0e6f13489ad6b21a91042c3be7e76c675b83`.
- C.54-style evidence: `6855974fed1bdd9294893d18b2538b2e7713a78e2efa257e85a2d79cbb61c14d`.

These hashes confirm canonical serialization consistency **only**; they are not external source attestations. Raw Loki log lines were not passed to the model. Qwen output is constrained by host-side code validation and has no action authority.

## Manual use on the Fedora lab only

Requires Python 3, local VictoriaMetrics at `127.0.0.1:8428`, local Loki at `127.0.0.1:3100`, and optionally the locally served Ollama model `qwen3.5:4b` at `127.0.0.1:11435`. Use a **non-root** user, manually and only after source review. Do not enable systemd/autostart, arbitrary LogQL/PromQL selectors, remote binding, container execution, tool calls or router write access.

```bash
cd experiments/fedora/local-ai-agent-v0.21
sha256sum -c SHA256SUMS
python3 -B local_ai_agent_v021c54_minimal_host_evidence_contract_v01.py --self-test
python3 -B local_ai_agent_v021c57_consolidated_vm_loki_readonly_lab_v01.py --self-test
python3 -B local_ai_agent_v021c58_c57_hcc_c54_compatibility_audit_v01.py --self-test
python3 -B local_ai_agent_v021c59_1_ollama_transport_hotfix_shadow_lab_v01.py --self-test

# Optional, explicit local read-only checks, separate from offline tests:
python3 -B local_ai_agent_v021c57_consolidated_vm_loki_readonly_lab_v01.py --historical-preflight
python3 -B local_ai_agent_v021c58_c57_hcc_c54_compatibility_audit_v01.py --audit-live
python3 -B local_ai_agent_v021c59_1_ollama_transport_hotfix_shadow_lab_v01.py --host-preflight

# Optional only after all host gates PASS and local Ollama is intentionally running:
python3 -B local_ai_agent_v021c59_1_ollama_transport_hotfix_shadow_lab_v01.py --qwen-shadow
```

A failing source, missing historical data, invalid model output or hash mismatch must remain **HOLD**, not fall back to a plausible-looking incident report. These commands are for a **historic data sample**; do not call them a continuous health monitor.

## Safety and next work

- No router/ASUS, RouterCloud, production DNS Guard, Pi-hole, Unbound, firewall, Grafana, Loki/Alloy configuration or HCC runtime changes.
- No model-initiated shell, OpenCode execution, Podman dispatch, deployment, ACK or persistent checkpoint effects. `DEPLOYMENT_GATE=HOLD`.
- Review data provenance and avoid publishing raw query logs, private operator notes, identifiers, credentials or local host paths.
- Next laboratory phase: model error/timeout/invalid JSON tests, missing-source and stale-data negative cases, and an architecture review before considering **C.60**. Treat any future write-capable executor as a **separately approved** workstream. Do not implicitly enable it.
- This checkpoint does not replace [HCC's own implementation and acceptance gates](../homelab-control-center-v0.1/README.md).

**Evidence classification:** Fedora results above are **operator-reported terminal outputs**, not freshly verified by GitHub CI or independent host access. See the [October 30 public engineering worklog](../../../docs/worklog/2026-10-30.md). Public documentation follows the [repository language policy](../../../docs/language-policy.md).

## October 31 addendum — C.60 / C.60.1

**Current Qwen SHADOW entry point:** `local_ai_agent_v021c60_1_strict_ollama_completion_shadow_lab_v01.py`. C.59.1 remains unchanged as a historical, pinned artifact. This section extends (does not rewrite) the October 30 checkpoint.

- **C.60:** an offline-only pinned negative/fault matrix for C.59.1. Fedora operator reported `40/40 PASS`. The audit confirmed an actual defect: omitted Ollama `done_reason` was implicitly accepted as `stop`. The audit PASS does **not** certify hostile-model safety.
- **C.60.1:** requires `done is True` and explicitly `done_reason == "stop"`; rejects missing, null, incomplete (`length`), extra-whitespace and other incorrect values. Twelve additional tests bring the total to `48/48 PASS` offline on Fedora. Host preflight passed using fixed historical VictoriaMetrics and Loki data.
- **Real SHADOW acceptance:** first run failed safely with `OLLAMA_LOOPBACK_UNAVAILABLE` because portable Ollama had not been started since the workstation was shut down. After the operator manually started the existing local service, `qwen3.5:4b` at `127.0.0.1:11435` returned `VALID_SHADOW_CODES_ONLY` and `PASS_DUAL_SOURCE_QWEN_SHADOW_ONLY`. This is *one bounded response*, not evidence of autonomous authority.
- Source identity is recorded in [SHA256SUMS](SHA256SUMS). The files are read-only laboratory sources; no ASUS, HCC runtime, VM/Loki configuration, Ollama service setup, autostart or executor changes were authorized. **`DEPLOYMENT_GATE=HOLD`.**

Manual test commands (from this directory, as a non-root operator):

```bash
sha256sum -c SHA256SUMS
python3 -B local_ai_agent_v021c60_offline_fault_matrix_audit_v01.py --self-test
python3 -B local_ai_agent_v021c60_1_strict_ollama_completion_shadow_lab_v01.py --self-test
# Optional explicitly manual read-only host evaluation:
python3 -B local_ai_agent_v021c60_1_strict_ollama_completion_shadow_lab_v01.py --host-preflight
# Optional, only after host preflight PASS and operator-started local Ollama:
python3 -B local_ai_agent_v021c60_1_strict_ollama_completion_shadow_lab_v01.py --qwen-shadow
```

**Scope of proof:** pinning and a single historical VM+Loki+Qwen SHADOW response; no cryptographic source attestation, exact fallback timings, DNS-success measurement, live HCC parity, adversarial-model certification or production readiness. The Qwen model has **no execution authority**. Refer to [October 31 worklog](../../../docs/worklog/2026-10-31.md).

## October 31: C.61 six-category synthetic fixture contract (operator-accepted)

**C.61 is offline/synthetic ONLY**, not a production detector or live-model integration. Pinned source `local_ai_agent_v021c61_multi_incident_host_fixture_lab_v01.py`, SHA-256 in [SHA256SUMS](SHA256SUMS). Operator-reported Fedora `55/55 PASS` for `--self-test` and again `55/55 PASS` for `--fixture-matrix`, with six expected scenarios: DNS Guard BOOTSTRAP, Pi-hole log activity, synthetic Unbound DNSSEC failure, synthetic Tailscale peer unreachable, stale/missing Fedora collector evidence, and a normal-looking sample (not health proof).

The schema is `local-ai-agent.multi-incident.host-observation.v1`, source origin `SYNTHETIC_FIXTURE_ONLY`, fixed test clock `2026-10-31 08:00 UTC`. A stale/missing/UNKNOWN/UNAVAILABLE signal cannot be upgraded to healthy or failed. No real source, model, ASUS, HCC or executor contacted; no file writes; `DEPLOYMENT_GATE=HOLD`.

Manual non-root offline verification:

```bash
python3 -B local_ai_agent_v021c61_multi_incident_host_fixture_lab_v01.py --self-test
python3 -B local_ai_agent_v021c61_multi_incident_host_fixture_lab_v01.py --fixture-matrix
```

**Bridge boundary:** The existing historical C.57 VM/Loki data must **not** be passed directly into C.61's fixed-clock synthetic classifier. The separate historical evidence adapter (C.61.1) has now passed operator verification and is included in this same Draft PR. Its result is **not** evidence of fresh Unbound/Tailscale/Fedora incidents. See the next section.

## October 31: C.61.1 historical VM/Loki bridge — operator-accepted

**Entry point:** `local_ai_agent_v021c61_1_historical_vm_loki_to_multi_incident_bridge_lab_v01.py` (pinned SHA-256 in [SHA256SUMS](SHA256SUMS)). This is a separate **historical** real-source adapter; it does **not** invoke the fixed-clock C.61 synthetic classifier on live data and does not add new Unbound, Tailscale or Fedora measurements.

Reported on the operator's Fedora workstation:

- Script integrity check: **PASS**; offline `--self-test`: **40/40 PASS**, no network contact.
- Manual `--historical-adapter-preflight`: **`PASS_HISTORICAL_VM_LOKI_ADAPTER_ONLY`**. Exactly seven fixed local VictoriaMetrics range reads plus one local Loki aggregate; all sources cover **2026-10-27 15:40–16:40 UTC**, *not* current health.
- C.57 source SHA-256 `758e5155c72136bca98371f59e3df01c3655d22401d9faada818b33934ef3115`; C.61 source SHA-256 `fcc6a5bbc526f4f49700411a133a8657976d80371f575b1ca17ae7d9c5dfa024`; source joint evidence SHA-256 `557914157204f5b888459efacb4f0e6f13489ad6b21a91042c3be7e76c675b83`.
- Output schema `local-ai-agent.multi-incident.historical-vm-loki-bridge.v1`, **three bounded observations** for **DNS Guard and Pi-hole**; **Unbound, Tailscale and Fedora explicitly unobserved**. The Pi-hole full minute ending 17:02 CET contains **141 log entries**, **not** a count of successful DNS resolutions.
- Canonical bridge evidence: **1,825 bytes**, SHA-256 `07e92be151d1cf6f27b6100d365da856d83c73babb045820e2e5472d9e3cdbbe`. This hash is an internal serialization identity, **not cryptographic authentication of underlying telemetry**.
- No raw Loki log lines, Ollama, ASUS, deployed HCC, executor, Podman or output file writes. `MODEL_ACTION_AUTHORITY=NONE`; `DEPLOYMENT_GATE=HOLD`.

Manual non-root testing (use only after reviewing source and choosing the correct local environment):

```bash
sha256sum -c SHA256SUMS
python3 -B local_ai_agent_v021c61_1_historical_vm_loki_to_multi_incident_bridge_lab_v01.py --self-test
# Explicitly opt in to historical loopback reads after the offline test passes:
python3 -B local_ai_agent_v021c61_1_historical_vm_loki_to_multi_incident_bridge_lab_v01.py --historical-adapter-preflight
```

**Next design boundary:** a separate, carefully reviewed *freshness-aware* observational contract is needed before querying current metrics. Missing observations, host shutdowns and stale collectors must not be silently promoted into failures or healthy status. Current DNS resolver paths and live HCC parity remain **unverified**.
