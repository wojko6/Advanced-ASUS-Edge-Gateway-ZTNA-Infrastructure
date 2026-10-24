# Case study: DNS fail-open succeeded while Grafana alerts were delayed

> **Incident date:** 2026-10-24 (CEST, UTC+02:00).
> **Status:** forensic investigation documented; **DNS Guard production transitions observed**, notification-delivery dependency and DNS Guard TCP-probe defect **not remediated or fully root-caused**.
> **Scope:** ASUS TUF-AX5400 / GNUton Merlin / Entware Unbound + Pi-hole + firmware dnsmasq; Fedora 44 with systemd-resolved, Blackbox Exporter, VictoriaMetrics and Grafana 13.2.4.
> **Evidence class:** operator-provided read-only router-log, Fedora-journal, VictoriaMetrics, Grafana SQLite and received-notification outputs. The public report is sanitized; no live systems were modified by this investigation.
> **Related incident:** [Unbound RFC 5011 trust-anchor / opkg outage and recovery](unbound-dnssec-autotrust-opkg-incident-2026-10-24.md). The Unbound package rollback and later successful R2 1.26.2 deployment are described there; this document addresses **service-continuity and alert-delivery consequences**, not a second Unbound upgrade.

## Executive summary

During the first October 24 Unbound maintenance attempt, the resolver daemon exited because it could not create an RFC 5011 automatic trust-anchor temporary file inside its unprivileged chroot. Restoring the previous IPKs alone did not restore usable resolution. A focused permission/configuration repair recovered the daemon, and a separate, later operator-authorized R2 production upgrade succeeded. The package and filesystem root-cause evidence is documented in the companion case study.

A subsequent **historical** log and time-series investigation uncovered two important, distinct facts:

1. **Router-system DNS Guard fail-open/failback actually occurred** during the incident: the system resolver switched to independent WAN bootstrap DNS at **10:25:02** and was promoted back to local Pi-hole at **11:08:01**. The bootstrap-health metric reported success and the watchdog was registered in the sampled period. This is a spontaneous production incident observation, **not** a planned, isolated fault-injection acceptance test. It does not establish DNS continuity for LAN/Tailscale classic-DNS clients.
2. **Grafana notification delivery was impaired concurrently:** direct router-DNS Blackbox probes failed while IP reachability and the separate HTTPS probe remained healthy; Grafana logged **14** `ngalert.notifier` errors classified with DNS lookup, timeout and exhausted retry signals. The `dns_guard_sustained_failopen` FIRING e-mail arrived at **11:07:03** and RESOLVED at **11:12:02**. The FIRING message states its alert was observed at **10:36:30**, about **30m33s** before delivery. The errors explain why delayed delivery is plausible, but their precise channel, resolver dependency and Grafana notification routing chronology remain incompletely proven.

The incident therefore demonstrated **successful router-system fail-open** alongside **unavailable client-facing DNS and compromised timeliness of monitoring notifications**. Availability, recoverability and timely alert delivery are different assurance properties.

## Architecture and failure-domain boundary

~~~text
                             ASUS TUF-AX5400
LAN client / Fedora -> Pi-hole :53 -----------+
LAN intercepted DNS -> firmware dnsmasq :53 --+--> shared Unbound :53535
                                               |
                         failure of Unbound ---+

ASUS router system resolver -> DNS Guard v3.2
    healthy                  -> Pi-hole -> Unbound
    local DNS unhealthy      -> independent WAN/bootstrap DNS

Fedora:
    systemd-resolved stub -> configured upstream (Pi-hole in current snapshot)
    Blackbox Exporter -> direct router DNS probe (firmware dnsmasq path)
    VictoriaMetrics -> Grafana evaluation -> alert notification integrations
~~~

DNS Guard's bootstrap policy changes the **router system resolver**, not the resolver DHCP advertises to LAN clients or the upstream used by the two local DNS front ends. The WAN bootstrap path intentionally does not apply Pi-hole filtering. Both firmware dnsmasq and Pi-hole ultimately depend on the same local Unbound.

The current Fedora `resolvectl dns` snapshot identified the ASUS Pi-hole as upstream. Historical Grafana error messages identified the local `systemd-resolved` stub as the resolver used for failed lookups. **The historic upstream configuration at the exact incident time was not recovered**, so the observed current configuration is not by itself proof of the upstream used for every earlier failed lookup.

The source-controlled Blackbox job `internet_dns` targets firmware dnsmasq on the router using UDP/53, a query for `example.com`, and `NOERROR` acceptance. It is **not** a direct probe of the separate Pi-hole alias on Fedora; both paths share Unbound. The HTTPS check may succeed thanks to successful independent lookups or caching; its PASS does not establish Pi-hole health.

## Evidence and chronological reconstruction

All timestamps below are **2026-10-24 CEST** unless noted otherwise.

| Time | Evidence | Interpretation / limitation |
| --- | --- | --- |
| 08:51:03 | First of 565 same-day `dig is installed but not runnable` DNS Guard warnings, as observed through 15:00:01 | TCP-probe warnings predate the identified 10:24 DNS incident; do not attribute them all to the Unbound upgrade |
| 10:24:30 | First failed `internet_dns` Blackbox observation in the 10:20–11:20 query window | Direct router dnsmasq DNS probe began failing; no contemporaneous outage of the independent HTTPS or ICMP probes |
| 10:25:02 | Router syslog: `system resolver restored to functional WAN bootstrap DNS` | A real DNS Guard bootstrap transition was logged; does not show client DNS failover |
| 10:28:17 | First classified `ngalert.notifier` delivery error | DNS-lookup/timeout/retry problem while incident was ongoing; before the sustained-failopen alert's cited observation time |
| 10:36:30 | Start/observation timestamp reported inside Grafana's FIRING e-mail | Not independently established as the precise Pending-to-Firing state transition |
| 10:36:32 onward | Repeated `ngalert.sender.router`: `Sending alerts to local notifier` | Internal forwarding activity, **not** proof of final transport or delivery |
| 11:03:31 | Last of 14 classified notifier errors | Cause and affected downstream integrations require further event-level investigation |
| 11:05:30 | Last failed `internet_dns` sample | Subsequent Blackbox samples passed; not a guaranteed packet-by-packet recovery timestamp |
| 11:07:03 | FIRING e-mail received, `dns_guard_sustained_failopen` | End-to-end e-mail delivery eventually succeeded; roughly 30m33s after message's alert-observation timestamp |
| 11:08:01 | Router syslog: `system resolver promoted to Pi-hole` | Real production local recovery / promotion |
| 11:12:02 | RESOLVED e-mail received | Confirmed e-mail notification on resolution, not evidence that every relevant alert had delivered |
| 11:10–11:20 | Bootstrapped-mode metric back to 0 and direct router DNS Blackbox PASS | Post-recovery state observed through time-series |

**Blackbox validation (VictoriaMetrics, 10:20–11:20, 30-second samples):**

| Job | Samples | PASS | FAIL | Bounds of observed failures |
| --- | ---: | ---: | ---: | --- |
| `internet_dns` (router dnsmasq, UDP/53) | 121 | 38 | **83** | First **10:24:30**, last **11:05:30** |
| `internet_icmp` (IP literal) | 121 | **121** | 0 | None in window |
| `internet_https` | 121 | **121** | 0 | None in window |

This is evidence that the tested DNS path failed while tested IP connectivity and HTTPS remained available. It does **not** demonstrate that *every* hostname lookup, device or client application failed continuously for the entire window.

**DNS Guard historical metrics (1-minute query samples, 10:20–11:20):**

- `asus_edge_dns_guard_mode_bootstrap=1` for the sampled 10:30–11:08 portion; `0` by the 11:10 sample.
- `asus_edge_dns_guard_bootstrap_dns_healthy=1` throughout sampled checkpoints; bootstrap health probes passed, not an exhaustive proof of every possible bootstrap lookup.
- `asus_edge_dns_guard_watchdog_present=1` for the queried checkpoints: the cron registration was observed. The transition log and subsequent recovery provide stronger evidence of action than registration alone, but do not provide a full per-minute execution trace.
- `asus_edge_dns_guard_collection_timestamp_seconds` age at the presented checkpoints was between **2 and 63 seconds**, below the rule's **180-second** freshness bound.

This corrects the earlier October 24 acceptance report's limited statement that DNS Guard failover had not been tested: **no deliberate fault injection was performed**, but the later log audit uncovered **actual fail-open and failback during an unplanned outage**. The evidence remains limited to the router system resolver.

## Grafana notification investigation

The live Grafana SQLite read-only audit identified `tuf_probe_failed` as **present, not paused**, with a pending interval equivalent to **120 seconds**, an expression that includes `internet_dns`, and an existing notification receiver configuration. This was a **current** configuration read, not proof of its exact historical evaluation state or a successful notification. No matching `tuf_probe_failed` e-mail was found in the available Gmail search on this date. Neither the absence of a matching e-mail nor current SQLite settings alone prove that the alert fired or that all configured notification channels failed.

The separate `dns_guard_sustained_failopen` rule is configured with a **10-minute** `for` period and fresh-data gate; its later FIRING and RESOLVED e-mails were actually received. The FIRING e-mail included Grafana's text `Observed 30m32s before this notification was delivered`, with an observation timestamp of 10:36:30. Avoid treating this timestamp as an exact Grafana state-machine transition without a corroborating alert-state history.

**Journal classification (10:20–11:20):**

- Initial broad match counted 67 `ERROR_OR_RETRY` entries; the more precise inspection identified **14 actual `level=error` / `logger=ngalert.notifier` / `Notify for alerts failed` records**, from **10:28:17 to 11:03:31**. Generic informational lines had previously been counted as errors because their text included keyword substrings. The corrected number is 14.
- The 14 error messages' classification flagged `DNS_LOOKUP`, `TIMEOUT` and `RETRY_EXHAUSTED`; this is powerful evidence that failed name resolution contributed to the notification difficulties, but the full redacted error payload and endpoint attribution were not separately reviewed.
- Informational `Sending alerts to local notifier` messages appeared repeatedly. One classifier split them into 53 general and 44 DNS-Guard-referencing matches, but these categories are **not necessarily distinct delivery attempts** and must not be summed as 97 successful notifications.
- An earlier sanitized heuristic labeled all 14 errors `EMAIL` because it searched the whole error text for an `email[` marker. This **does not prove Email alone failed**, especially where the same message may carry other integration details. Recipient/channel isolation remains open.
- The fact that the final e-mail was delivered while the ASUS system resolver was still documented as bootstrap is consistent with independent timing of restoration, cache behavior, per-host resolver settings, or retries; **no singular cause is proven**.

**Historical DNS lookup evidence:** 14/14 notifier errors referred to the local `systemd-resolved` stub as their lookup resolver. The contemporaneous upstream choice was not independently captured; current Fedora DNS configuration points to the ASUS Pi-hole. Thus: local lookups demonstrably failed and the shared resolver failure is a strong architectural explanation, but the exact per-connection historical chain is not proven.

## Auxiliary discovery: DNS Guard TCP readiness probe skipped

The router archive contained **565** warnings of the form:

~~~text
WARNING: dig is installed but not runnable; skipping active TCP DNS query probe
~~~

The warning frequency extended from **08:51:03 to 15:00:01** and is **not** a proxy for 565 DNS outages. Code review shows the DNS Guard v3.2 `dns_probe_tcp_ready` branch calls `bounded_exec dig -v`; when that returns nonzero, the optional TCP DNS probe is **skipped as a success**. The required BusyBox UDP `nslookup` readiness probe remains active.

A *separate read-only router test* returned:

~~~text
/opt/bin/dig -v = DiG 9.20.18, RC=0
PATH-invoked dig -v = DiG 9.20.18, RC=0
/bin/busybox sleep 0 = RC=0
~~~

The same diagnostic's `command -v dig` output reported `NOT_FOUND`, while the immediately following direct PATH invocation succeeded. **Do not reconcile this inconsistency by assumption.** The root cause may involve the bounded execution wrapper, execution context, PATH resolution or transient process behavior. No `dig` reinstall, DNS Guard code modification or forced fallback has occurred.

**Impact boundary:** direct production Unbound TCP/UDP DNSSEC acceptance in the later R2 deployment passed, but DNS Guard's optional **own active TCP probe** was not reliably exercised. A functional Unbound TCP socket is not proof that DNS Guard's TCP health check executed.

## Findings, status and remediation backlog

| Finding | Current classification |
| --- | --- |
| Shared Unbound caused an actual resolver-service incident | **CONFIRMED** by the companion case study |
| Independent IP and HTTPS Blackbox checks stayed healthy while router DNS failed | **CONFIRMED** for tested probes |
| DNS Guard selected WAN bootstrap and later local Pi-hole | **CONFIRMED** by live production logs and matching metrics |
| WAN bootstrap health probe returned healthy during selected samples | **CONFIRMED**, bounded observation |
| Client DNS preserved continuously by DNS Guard | **NOT PROVEN**; DNS Guard is router-system-resolver-only |
| Grafana sent FIRING and RESOLVED messages | **CONFIRMED**, but late |
| Grafana notification component logged 14 DNS lookup/timeout/retry failures | **CONFIRMED** by sanitized classifier |
| All 14 failures were strictly SMTP-only | **NOT PROVEN**; channel heuristic insufficient |
| Historical Fedora upstream for failed `systemd-resolved` lookups was Pi-hole | **PLAUSIBLE, NOT PROVEN** from current snapshot alone |
| `tuf_probe_failed` fired and its message was lost | **NOT PROVEN**; current live rule active and Gmail search negative only |
| DNS Guard optional TCP probe ran successfully | **NOT PROVEN**; repeated skip warnings |
| Permanent independent monitoring DNS or delivery fallback deployed | **NO** |
| Full deliberate fault injection, cold reboot after R2, long soak | **NOT TESTED** |

**Recommended follow-ups, requiring separate review:**

1. **Read-only forensic gate:** inspect Grafana alert state history and notification-delivery logs for both `dns_guard_sustained_failopen` and `tuf_probe_failed`, distinguishing initial observation, Pending/Firing, queueing, retries, individual transport errors and Resolved. Preserve evidence without publishing recipients or tokens.
2. **Independent monitoring DNS design:** break Fedora's alert-delivery dependency on the sole on-router Unbound failure domain, while preserving Pi-hole filtering where appropriate. Test DNSSEC, local names, fallback policy, resolver leaks, alert transport and restore behavior before any production change. An unconditional switch of all Fedora applications to public DNS is **not** authorized by this report.
3. **Fedora-only DNS Guard wrapper reproduction:** investigate direct `dig -v` versus `native_bounded_exec` in a controlled harness. Validate actual TCP probe execution and logging without modifying the ASUS production controller or mixing the separate #287 timer-cancel worktree.
4. **Explicit end-to-end alert gate:** test DNS-failure alert delivery including a deliberately failed local resolver, a truly independent transport resolution path, notification route correctness and bounded delay in a maintenance or synthetic environment. A healthy Grafana HTTP endpoint is insufficient.
5. **Maintain failover boundary:** a second independently powered Pi-hole/Unbound (research #216) and client DNS failover (#212) remain *not deployed*. Review LAN/Tailscale DNS interception, policy parity and real-client failure semantics before any pilot.

## Cross-references

- [Unbound 1.26.2 DNSSEC / opkg incident](unbound-dnssec-autotrust-opkg-incident-2026-10-24.md) — immediate daemon failure, first failed upgrade/rollback, targeted recovery and later successful R2.
- [October 24 production R2 bounded acceptance](../operations/unbound-1.26.2-production-deployment-2026-10-24.md) — package/runtime DNSSEC acceptance; separate from client availability.
- [DNS enforcement paths](../architecture/dns-enforcement-flow.md) and [availability/failure domains](../architecture/availability-and-redundancy.md).
- [DNS Guard v3.2 recovery and partial live validation](../dns-guard-v3.2-recovery-audit-live-validation.md) — historical 2026-10-08 testing; distinct from October 24 incident.
- [Grafana provisioning](../../monitoring/grafana/provisioning/alerting/asus-tuf-alerts.yml) and [source Blackbox probes](../../monitoring/config/prometheus.yml).
- [October 24 public worklog](../worklog/2026-10-24.md).

> **Publication/closure boundary (post-merge update):** documentation was published in merged [PR #297](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/297) on 2026-10-24; that publication made **no router/Fedora DNS, Grafana alerting, notification or service change**. Controlled fault-injection, monitoring independence and optional probe remediation remain **OPEN**. The separate successful Unbound R2 upgrade is **not** undone by these findings.
