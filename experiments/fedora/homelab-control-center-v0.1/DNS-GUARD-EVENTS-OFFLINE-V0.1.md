# DNS Guard resolver transition history — Issue #319, offline V0.1

Date: 2026-10-27
Status: **FEDORA SOURCE-ONLY / PURE OFFLINE MODEL / NO LIVE INGESTION / NO NOTIFICATIONS**
Deployment gate: **HOLD**. Independent of #314 / Draft PR #318 and Black Box #304.

## Why an event ledger is needed

On 2026-10-27 the operator saw the V0.4 candidate show DNS Guard **BOOTSTRAP / DEGRADED** and, at the same time, a **successful** Blackbox router-DNS query. Subsequent metrics reported **LOCAL**. This illustrates two distinct signals; one successful DNS lookup does not invalidate a router-system resolver mode transition.

Current source-controlled Grafana alert `dns_guard_sustained_failopen` requires 10 minutes in bootstrap. `dns_guard_recovery_flapping` requires more than two transitions to bootstrap in 15 minutes, plus 2 minutes of rule persistence. Neither provides an informational message for each observed transition. The deployed Grafana rule configuration and Email/Telegram receiver routing still require fresh read-only reconciliation under #236; lack of a short-transition message alone does **not** prove an alert delivery fault.

## Evidence source: what already exists, and what does not

`router/scripts/dns-guard` emits:
- `asus_edge_dns_guard_mode_local`
- `asus_edge_dns_guard_mode_bootstrap`
- `asus_edge_dns_guard_state_valid`
- `asus_edge_dns_guard_last_transition_timestamp_seconds`
- `asus_edge_dns_guard_fallback_since_timestamp_seconds`
- `asus_edge_dns_guard_fallback_transitions_runtime_total`

`scripts/dns-guard-metrics.sh` imports these numbers plus the Fedora exporter-generated `asus_edge_dns_guard_collection_timestamp_seconds` into the local VictoriaMetrics, using an existing scheduled path. The collector's collection timestamp is **not** an exact instant of a router DNS resolver switch. The router's `metrics` command itself reconciles observed resolver mode, which can update router-maintained mode timestamps. Runtime counters can reset on reboot or lost state.

Source convention suggests roughly minute-level collection, but **source declarations, actual sample cadence, and retention are not equivalent**. The HCC source inventory has not verified an appropriate, bounded historical query-range adapter, the full cardinality/label contract over historical samples, alignment of separately imported series, or persistent completeness. A brief transition may happen between samples and be invisible. A counter change can suggest a missing transition but cannot supply its precise time and direction.

Do not claim every historical transition from the gauges. Do not call the model a notification mechanism or an incident root-cause engine.

## What the proposed pure model actually does

New file: `tools/dns_guard_event_model_v01.py`

It accepts only an **operator-designed, sanitized synthetic sequence**, not VictoriaMetrics JSON or private logs. Each record has exactly seven numeric fields:
`collection_epoch, mode_local, mode_bootstrap, state_valid, last_transition_epoch, fallback_since_epoch, fallback_transitions_total`.
All timestamps are UTC Unix seconds and the input is constrained to 256 observations. Additional keys (including router IPs, labels, names, user/device identities) are rejected and never echoed.

It yields one bounded, deterministic `timeline(rows)` structure:
- `DNS_GUARD_BOOTSTRAP_OBSERVED`: contiguous valid LOCAL → BOOTSTRAP sample boundary;
- `DNS_GUARD_LOCAL_RESTORED`: contiguous valid BOOTSTRAP → LOCAL sample boundary;
- `DNS_GUARD_STATE_UNKNOWN`: malformed/contradictory, out-of-order, counter reset, inferred but unobserved transition or ambiguous duplicate;
- `DNS_GUARD_TELEMETRY_STALE`: a gap longer than the provisional 180-second collection-spacing threshold.

**No event for the first baseline observation**, even if it reports BOOTSTRAP: the previous state is unknown. A subsequent BOOTSTRAP → LOCAL observation may produce a limited recovery with unknown maximum duration.

For transitions, `window_start` is the preceding verified collection and `window_end` is the later collection. `observed_at` is the *later collection*, **not** asserted occurrence time. `reported_transition_at` is separately tagged as router-reported and shown only if it falls inside the observation interval; it is never treated as an independently verified switch timestamp. The model does not infer exact downtime or filtering success.

If both bounding observations exist and the bootstrap period has a positively observed span, the recovery event may include **lower/upper duration bounds** (seconds), not an exact downtime. When the initial LOCAL state was not observed, the upper bound is null. A broken chain has no paired duration.

Repeated identical input is deduplicated inside this one model evaluation. `dedupe_key` is **provisional and session-local**; no durable event identity or store exists yet, and repeated restarts cannot be made exactly-once by these keys alone. Clock correction and cross-source atomicity are not established.

## Critical boundaries

1. All normal runs are offline Python function calls. No HTTP, SSH, DNS, Grafana/Loki/VM access, file writes, operating-system notifications, credentials, systemd, timers, service restart, Caddy/hosts or production router contact.
2. This model cannot verify whether separately pulled metric series belong to one atomic collection. The later, **separately authorized** adapter must check source identity, label sets, matching collection semantics, timestamp skew and gaps or refuse LIVE history.
3. No externally visible third-party notification and no policy for Email/Telegram is deployed. Informational event history in HCC must be built before notification transport wiring, and notification delivery must meet #236's separate source/live receiver parity gate.
4. The October 27 operator readings are **real source observations** documented elsewhere, but are **not retroactively fabricated as exact fixture events**. Fixtures in tests are wholly synthetic.
5. This event ledger does **not** replace Black Box #304 incident correlation or the existing sustained-fallback, bootstrap-unhealthy and flapping alerts.

## Deterministic checks

From `experiments/fedora/homelab-control-center-v0.1`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.mjs
```

The new tests cover contiguous LOCAL → BOOTSTRAP → LOCAL with duration ranges, repeated observations, bootstrapped initial baseline, missing fallback-since, non-corroborating counter, missing/out-of-order/contradictory observations, resets, hidden transitions between samples, impossible timestamps, privacy/source limitations and bounded inputs.

## Independent future gates (not approved for implementation by this PR)

A. **Read-only live history source preflight:** determine exact field provenance, label/cardinality policy, scrape/import clock semantics and safe finite range query to 127.0.0.1:8428. Validate with sanitized outputs before wiring anything to the server.

B. **UI:** separate neutral "Ostatnie zdarzenia DNS Guard" panel and bounded history API, with source, evidence window, duration uncertainty and explicit missing-coverage states. All synthetic history stays hidden as DEMO until an approved real backend exists.

C. **Grafana:** read-only audit of deployed rules and Email+Telegram routing against source (#236). Design informational notification and matching LOCAL restoration with dedup, rate limits and correlation; then separate operator approval for *non-disruptive* synthetic Firing/Resolved delivery checks. No forced router DNS failure to test alerts and no Grafana provisioning reload from this PR.

**DEPLOYMENT_GATE=HOLD.**
