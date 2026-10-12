# Grafana / Alloy / Loki monitoring and notification audit — 2026-10-12

**Evidence class:** sanitized operator-reported Fedora monitoring-host checks and UI confirmation.  
**Scope:** ASUS Edge Gateway observability stack; current Grafana notification configuration.  
**Environment:** Fedora-hosted Alloy, Loki, Grafana, VictoriaMetrics; ASUS reference router not modified.  
**Verdict:** **STATIC ROUTING PASS**, basic ingest/runtime checks PASS, **E2E FIRING AND AUTOMATIC EMAIL + TELEGRAM DELIVERY PASS**; recovery/cleanup still pending.

## Observations

| Layer / method | Observed result | Interpretation |
|---|---|---|
| Loki 15-minute ASUS stream discovery | One ASUS-related stream; 353 matching entries under all four checked selector dimensions | ASUS-related log stream visible in the observed window; not an exact-loss audit |
| Service state and Loki readiness | Alloy, Loki, Grafana active; Loki `/ready` PASS | Services available when inspected |
| Loki 3 × 5-minute count | 62 / 110 / 85 | Nonempty consecutive windows; query covered all nonempty `job` labels |
| Loki 5 × 1-minute freshness | 25 / 143 / 17 / 31 / 16 (newest first) | Fresh entries present; these counts are not ASUS-only |
| `journald` 30-minute priority audit | Loki 716 entries, Grafana 493 entries, zero warning/error priorities in either | No warning/error **journal priorities** observed in this window; app-internal error fields were not fully audited |
| Alloy `journald` | Zero entries | **Inconclusive**, not proof of error-free Alloy operation |
| Alloy metrics | `loki_write_sent_entries_total=18388`; `loki_write_dropped_entries_total=0`; `loki_write_batch_retries_total=0` | No drops/retries in exposed aggregate counters at snapshot |
| Loki metrics | `loki_distributor_lines_received_total=18388`; `loki_discarded_samples_total=NOT_EXPOSED` | Received-counter snapshot matches sent-counter snapshot; cannot prove exact once delivery or absence of Loki-side discards |
| 20-second metric delta | Sent/dropped/retried/received deltas all zero | No counter movement in this short interval; not a throughput test |
| Grafana health API | `database=ok` | PASS |
| Provisioned alert rules | 15 total, zero paused | PASS |
| Alert runtime API | One group, 15 rules; 15 `inactive`; 15 `health=ok`; 15 with last-evaluation data; zero `firing`, `pending`, `error`, `nodata` | Rules evaluate successfully and were not alarming at snapshot |
| Grafana scheduling metrics | `grafana_alerting_schedule_alert_rules=15`; `grafana_alerting_scheduler_behind_seconds=0.00106344` | 15 scheduled, low observed scheduler lag at snapshot |
| Notification metrics | `grafana_alerting_notification_latency_seconds_count=0`; notification total/failure and history-failure counters `NOT_EXPOSED` | No transport-success/failure conclusion from these metrics |
| Contact API inventory | Two integration entries, one unique contact name; one Email and one Telegram integration | One logical contact point containing both integrations |
| UI contact tests | Operator confirmed receiving test notification in Gmail **and** Telegram | Both contact transports passed manual delivery test; does not demonstrate automatic rule-to-notification E2E |
| Direct routing | 15/15 rules have `notification_settings`; zero unresolved direct receivers | PASS |
| Default policy (before) | Receiver `empty` not matched to available named contact; no child routes | Earlier static fallback mismatch, direct 15 rules unaffected |
| Default policy (after UI edit) | Receiver `ASUS Edge Gateway Email`; API `DEFAULT_RECEIVER_VALID=PASS`; 15 rules still direct/unpaused/resolved; `FINAL_ROUTING_AUDIT=PASS` | Default fallback routing corrected and verified through read-only API |
| Controlled E2E preflight | VictoriaMetrics `vector(0)` and `vector(1)` query PASS; Grafana health PASS | Synthetic query-only preflight, no metric injection |
| Controlled E2E rule firing | Temporary `E2E-TEST-2026-10-12` under `Network`, `vector(1)` above 0.5; screenshot displays `FIRING`, `A=1`, `C=1` | **PASS**: real Grafana-managed temporary test rule fired, no simulated router/DNS failure |
| E2E automatic delivery | Operator-supplied Gmail notification screenshot and Telegram bot screenshot both explicitly reference `E2E-TEST-2026-10-12` and firing event | **PASS for automatic Firing delivery on both channels**, distinct from manual contact test |
| E2E recovery/cleanup | Not yet reported; planned edit back to `vector(0)`, verify normal/resolved, then remove temporary rule | **PENDING**. Do not claim resolved, final deletion, or closure |
| Provisioning inventory | 3 local alerting files: `asus-email-contact.yml`, `asus-tuf-alerts.yml`, `sample.yaml`; all readable with appropriate account; no `policies` or `resetPolicies` declaration observed | No default-policy source in inspected files; external configuration management still not conclusively excluded |

## State and drift boundary

The tracked `monitoring/grafana/provisioning/alerting/asus-email-contact.yml`
currently defines an Email receiver only. The **live** contact API on
2026-10-12 exposed Email **and** Telegram integrations for one logical
contact point. This is **live/source parity not yet reconciled**; do not
invent or commit a Telegram token or silently replace the live contact.

The default-policy receiver was changed through the UI to an existing
contact, and the operator's subsequent API inspection returned
`DEFAULT_RECEIVER_VALID=PASS` and `FINAL_ROUTING_AUDIT=PASS`.
Persistence across provisioning reload or service restart was **not
tested**. The direct receiver assignment of all 15 rules is unchanged.

## Safety / evidence boundaries

- Read-only service/API/metric/provisioning tests did not restart services or change router state.
- The **one intentional configuration change** during the session was the operator's Grafana UI change to the **default notification policy receiver**; therefore a global "zero production changes" claim for the *whole session* would be inaccurate.
- Operator confirmed delivery of the Email and Telegram **test** messages; no mail payloads, destination addresses, chat IDs, API tokens, or credentials are included here.
- Controlled `E2E-TEST-2026-10-12` rule **Firing** and automatic Email + Telegram delivery are observed **PASS** in operator screenshots. Return to `Normal`, resolved delivery, and deletion of the temporary rule remain **PENDING**. Historical WAN-speed Email and RouterCloud firing/recovery validation remain separate earlier evidence.
- Alert grouping, anti-flap behavior, repeated delivery, persistence after reload and all service-failure modes are not accepted by this audit.
- No screenshots containing private destination identifiers, raw logs, labels or credentials are published.

## Next gate

The synthetic `vector(0)` / `vector(1)` and Grafana-health preflight passed. The temporary rule fired and both automatic Firing notifications arrived. **Next:** operator must return its query to `vector(0)`, confirm Grafana Normal/recovery and optional resolved notifications, then delete the rule and verify baseline remains 15. No router, DNS Guard, Pi-hole, Tailscale, or WAN failure was caused. Follow up on #178 and verify live/declared Telegram provisioning parity without exposing secrets.
