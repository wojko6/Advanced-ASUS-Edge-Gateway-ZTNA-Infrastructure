# DNS Guard seven-series historical consistency preflight — Issue #319

2026-10-27 · **Fedora manual candidate, Draft only, DEPLOYMENT_GATE=HOLD**.

## Context / source provenance

Operator already verified the first one-series `/api/v1/export` read for 2026-10-27, returning **113** real samples and **two** sampled mode changes:
- LOCAL → BOOTSTRAP: **17:01:35.572–17:02:39.162 CET** (63.590 s observation gap).
- BOOTSTRAP → LOCAL: **17:04:48.836–17:05:55.563 CET** (66.727 s gap).

These are *observed sampling intervals*, not exact DNS switching timestamps. Assuming no hidden flips, one bootstrap episode length is bounded approximately **129.674–259.991 seconds**, not a guaranteed outage duration.

Source-only PR #320 introduced `tools/dns_guard_event_model_v01.py`, an offline conservative 7-field event model. PR #321 separately demonstrated a **single** historical mode-series preflight. **This PR is stacked on PR #320** (not on #321). It adds a separate, opt-in historical **seven-series** source adapter, without changing or importing the manual one-series PR #321 file.

The existing Fedora-side `scripts/dns-guard-metrics.sh` imports a coherent *router-generated textual metrics group* plus a Fedora collection timestamp into local VictoriaMetrics. However, VictoriaMetrics /api/v1/export GET calls are sequential, **not an atomic multi-series snapshot**. In addition, it is not yet proven that every series has identical retention, sample count or sample timestamp alignments. We must measure this, not assume it.

## Contract and limits

`tools/dns_guard_history_join_v01.py` exposes only:

- `--inspect`: no network, list literal metric suffixes and fixed 2026-10-27T14:40:00Z–16:43:00Z window;
- `--read-local`: operator-initiated, **seven** GET `/api/v1/export` requests to **127.0.0.1:8428 only**, 5 seconds max each, response cap 128KiB each, 200 sample max per series. No arbitrary endpoint, PromQL, HTTP body, router SSH, credentials or forwarded metrics query.
- Exact seven metric names: `mode_local`, `mode_bootstrap`, `state_valid`, `last_transition_timestamp_seconds`, `fallback_since_timestamp_seconds`, `fallback_transitions_runtime_total`, `collection_timestamp_seconds` under the fixed `asus_edge_dns_guard_` prefix.
- Strictly one metric per response, only `__name__` label, full `metric/timestamps/values` shape, no duplicate JSON keys, no malformed/NaN/Inf/mixed/bool/fractional values, strictly increasing millisecond timestamps in fixed history window. An untrusted label or identifier is **never printed**.
- Require equal series lengths and **index-correlated** sample timestamps within **5,000 ms** skew (provisional), collector epoch within **30s** of the mode anchor sample, and strictly increasing collection epochs. Reject nonmatching counts, missing historical samples or larger skew. This conservative gate may reject valid data. That is an **UNKNOWN preflight**, not a DNS Guard fault.
- Only after those checks, feed sanitized 7-field rows into source-only PR #320's `timeline(rows)`. Contradictory states, missed counter transitions or gaps fail the `corroborated_sampled_transitions` verdict. Independent raw mode windows remain explicitly scoped to samples, never exact transition times.
- No persisted event ID, guaranteed complete history, rolling new-window query, live UI, socket listener, watcher, timer, Grafana rule, Email/Telegram, SSH, router-side edits, Caddy changes or background task.

## Acceptance gates

1. Offline Python and Node regression, plus full repository workflow success, on the pinned branch SHA.
2. Operator `--inspect` local acceptance (no network).
3. Explicit operator `--read-local`, with strictly sanitized report. **If UNKNOWN, investigate safely; do not loosen timestamps just to get green.**
4. Before a LIVE dashboard endpoint, inventory source cadence and publication, align with reviewed one-series results, and approve separate server API/privacy/TTL/cache boundaries. Keep the currently running V0.4 independent.
5. Grafana source-vs-live Email+Telegram contact parity (#236) and informational transition notifications require a distinct approved phase. No new alerts or production fault injection.

Review tests at `tests/test_dns_guard_history_join_v01.py`. Run from `experiments/fedora/homelab-control-center-v0.1`:

```bash
python3 -B tools/dns_guard_history_join_v01.py --inspect
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.mjs
```

Do **not** run `--read-local` until the reviewed source gate; it is always manually opt-in, no background reads.

**DEPLOYMENT_GATE=HOLD**. No merge or live deployment authorized by this research PR.
