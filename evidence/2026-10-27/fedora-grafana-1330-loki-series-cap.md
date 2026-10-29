# Fedora Grafana 13.3.0 and Loki DNS-query series limit — 2026-10-27

> **Evidence:** operator-provided terminal outputs and browser screenshots, not direct independent host access.
> **Scope:** Fedora 44 observability host only; Grafana OSS package and Loki query-limit adjustment.
> **Production acceptance:** Grafana update PASS; Loki limit change PASS; bounded API/dashboard checks PASS; full 15-rule evaluation and notifier-delivery checks remain unverified.
> **Privacy:** this record omits individual queried domains, client names/IPs, authentication values and local backup paths.

## Change and validation

| Item | Observed result |
| --- | --- |
| Grafana OSS | `13.2.4-1.x86_64` → `13.3.0-1.x86_64`, manually installed from official [v13.3.0 release](https://github.com/grafana/grafana/releases/tag/v13.3.0) |
| Grafana RPM provenance | Downloaded x86_64 RPM, SHA-256 PASS; OpenPGP signature, header and payload integrity PASS |
| Grafana service and database | `grafana-server=active`; HTTP health returned `database=ok`, `version=13.3.0` |
| VictoriaMetrics | `active`; `/health=OK` in the earlier test |
| Loki | Version `3.7.9`, `active`; `/ready=200` at acceptance |
| Default 24h DNS ranking | Loki HTTP 400 at `max_query_series=500` |
| Selective JSON parse / `keep domain` | Insufficient at the former 500-series limit for a 24h query |
| Candidate | `limits_config.max_query_series: 1000`; `loki -verify-config` reported valid |
| Successful live change | `LOKI_READY=PASS`, `ACTIVE_LIMIT=1000`, 24h Loki query HTTP 200 / 10 series, `DEPLOYMENT_RESULT=PASS` |
| Browser follow-up | Both `Top 10 domen` and `Top 10 zablokowanych domen` visibly returned ranked values for last 24 hours with existing dashboard JSON expressions |
| Alerting | Grafana state-cache startup log had `rules=15`; provisioned rule UI displayed healthy indicators for visible rules; filtered post-change evaluation-error search returned no matches |
| Final systemd checks | Grafana, Loki, VictoriaMetrics all `active` |

The existing Loki `limits_config.retention_period: 168h`, ingestion settings, and DNS log source were not changed. The configuration file [`monitoring/loki/config.yml`](../../monitoring/loki/config.yml) now reflects the operator-reported new `max_query_series: 1000` value. This is **not** authorization to auto-deploy that file or to increase the limit again unboundedly.

## Unsuccessful first attempt and recovery

The first deployment passed candidate validation and restarted Loki with the new setting, but a postflight dependency on `/config?mode=diff` failed with HTTP 500, triggering an automatic rollback. A follow-up check showed the original configuration was byte-identical to its backup, normal `/config` returned HTTP 200, and `/config?mode=diff` still returned HTTP 500 on that restored baseline. Loki transiently reported `Ingester not ready: waiting for 15s after being ready`; a later `/ready=200` confirmed recovery. The second, successful deployment used the working `/config` endpoint and tested a real 24h query in addition to readiness. Its retained pre-change rollback file is on the operator host; its local path is deliberately not published.

## Plugin and query interpretation

Grafana loaded Loki data-source plugin `13.2.4`; filesystem inspection also found a bundled copy `13.2.2`. Dedupe warnings appeared for 13 plugin IDs. This was **not proven causal** for the 500-series query failure: multiple other DNS queries succeeded before the limit change. No plugin directories were deleted, and no Grafana dashboard panels were changed as part of the accepted final state.

The higher series limit is a **bounded operational mitigation**, not a permanent performance guarantee. If DNS cardinality grows further, test query costs and consider pre-aggregation or a dedicated metrics pipeline instead of endlessly increasing query limits.

## Open checks / evidence limits

- Verify the evaluated state/history of all 15 alert rules, not only service state and a filtered journal sample.
- Verify actual Email/Telegram notification delivery separately before asserting end-to-end alert continuity.
- Monitor Loki query cardinality, latency and memory after the 1000-series change.
- Keep historical Grafana 13.2.4 and prior Loki records as dated facts; do not rewrite them retroactively.
- No evidence in this record establishes Grafana database restore testing or a complete post-upgrade plugin compatibility certification.
