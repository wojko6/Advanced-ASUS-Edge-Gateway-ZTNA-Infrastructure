# DNS Guard historical source preflight — fixed raw VictoriaMetrics export

Date: 2026-10-27. Related: Issue #319, Phase A offline event model Draft PR #320, HCC V0.4 Draft PR #318.

**Status: isolated manual Fedora diagnostic ONLY; no live HCC backend, alert rule, notification sender, persistence or deployment. DEPLOYMENT_GATE=HOLD.**

## New operator evidence — raw samples, not extrapolated query_range steps

The operator confirmed one unlabeled historical `asus_edge_dns_guard_mode_bootstrap` metric series from Fedora-local VictoriaMetrics: 113 raw samples across 2026-10-27 15:41:03–17:42:43 CET, with initial LOCAL and final LOCAL. Two successive-sample value changes:

| Observed change | Previous sample (CET) | Next sample (CET) | Gap |
| --- | --- | --- | --- |
| LOCAL → BOOTSTRAP | 17:01:35 | 17:02:39 | 63.6s |
| BOOTSTRAP → LOCAL | 17:04:48 | 17:05:55 | 66.7s |

This is evidence for two **sampled mode changes**, and intervals in which they occurred, **not exact switch times**. Assuming one uninterrupted bootstrap interval, its possible length from the rounded wall-clock display would be approximately **129–260 seconds**; shorter intermediate transitions cannot be ruled out by these samples. This is compatible with the current source-controlled Grafana sustained fail-open `for: 10m` not alerting; it does **not** prove live receiver configuration or delivery behavior.

## Proposed isolated candidate

`tools/dns_guard_history_export_v01.py` is a deliberately *historical snapshot preflight*, rather than a long-running or dynamic live adapter.

- Only operator `--inspect` (NO network) or `--read-local` (explicit single GET to **127.0.0.1:8428**).
- Hardcoded `GET /api/v1/export`, a literal allowlisted metric `asus_edge_dns_guard_mode_bootstrap`, fixed absolute historical **2026-10-27T14:40:00Z** through **16:43:00Z**. No user-controlled PromQL, target, endpoint, port, window, or query.
- Max 128 KiB bytes, 5s socket timeout, 200 returned samples, exactly one line/series, exact-only `__name__` metric label, nondecreasing valid binary flags and strictly increasing millisecond timestamps bounded inside the request window.
- Emits UTC and Europe/Warsaw observation windows, `BOUNDED_OBSERVATION` or `DNS_GUARD_OBSERVATION_GAP` when adjacent samples are separated by more than the **provisional** 180s threshold. No fabricated exact outage or event timestamps.
- If source returns too much, malformed, changed labels, duplicate time series, non-binary values, future/out-of-window times or HTTP failure, it fails closed to UNKNOWN. No raw series or internal IDs are printed to user-readable output.
- Never contacts ASUS, Pi-hole, Unbound, Loki or Grafana, and does not execute DNS commands or emit a notification.
- No import/use by any HCC live server, no changes to V0.3/V0.4 page/assets, no Caddy, systemd, network exposure, service install, router config, SMS/Telegram/Email or Grafana rules.

**Two important separation limitations:** (1) The single mode gauge is **not** the complete 7-field event model in separate Draft PR #320; this preflight only proves that raw sampled mode windows can be parsed conservatively. (2) The export URI is intentionally fixed to the already approved October 27 historical window. A future moving time range, multi-metric join and durable dedupe require a new source and safety review before HCC LIVE history or notifications can be authorized.

## Test on Fedora (no privileged permissions)

From checkout `experiments/fedora/homelab-control-center-v0.1/`:

```sh
python3 -B tools/dns_guard_history_export_v01.py --inspect
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.mjs
```

For operator's *optional*, explicit fixed historical read:

```sh
python3 -B tools/dns_guard_history_export_v01.py --read-local
```

The report remains bounded; it intentionally cannot track new future DNS Guard transitions outside its fixed validation window. HCC panel V0.4 may continue running independently.

**STOP conditions:** unexpected labels, count mismatch, incomplete source window, sample gap, data volume, out-of-range timestamp, contradictory bytes or any nonlocal endpoint requested. Do **not** correct data with sorting, extrapolation, inherited last-good, or default-green status.

Deployment gate: **HOLD**; GitHub merge, live UI, Grafana or ASUS modifications require separate approval.
