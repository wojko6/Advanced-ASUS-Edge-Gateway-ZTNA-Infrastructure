# Availability, redundancy and single points of failure

**Status:** CURRENT  
**Last reviewed:** 2026-10-24 (incorporates the October 24 incident evidence; documentation only)

## Purpose

Separate **high availability** from **recoverability**. The project has strong
backup, validation and recovery engineering, but the current reference
deployment is not a redundant gateway architecture.

## New operational evidence — 2026-10-24

The single-Unbound DNS failure domain is no longer just a hypothetical availability warning. During an **unplanned**, initially failed Unbound upgrade, DNS Guard v3.2 selected independent **router-system** WAN bootstrap DNS at 10:25:02 and restored Pi-hole at 11:08:01, while a separate Blackbox probe of firmware dnsmasq failed 83/121 selected samples. This does **not** show that LAN/Tailscale client DNS followed the system-resolver failover, nor that every client was continuously offline. The later, separate Unbound 1.26.2 R2 upgrade and an ordinary router reboot passed bounded DNSSEC/client tests.

**Monitoring is not a fully independent failure domain either.** Fedora's current resolver snapshot used Pi-hole, and historical Grafana recorded 14 DNS/timeout/retry-related notifier errors plus delayed FIRING delivery during the incident. The historical resolver configuration and full per-channel cause were **not conclusively established**. A future independent alert-transport resolution/fallback policy requires a separate reviewed design; it is not currently deployed. [Case study with chronology and evidence](../case-studies/dns-guard-grafana-alert-delivery-dns-failure-2026-10-24.md).

Open DNS Guard concerns include optional TCP-query skip when `bounded_exec dig -v` fails, limited wrapper-timer descendant cleanup (#287), root-Cron trust (#235), full missing-watchdog recovery (#214), fresh-recursion cache oracle (#213), client failover (#212 PAUSED) and full Pi-hole-aware DR (#129). No additional redundancy, alternative resolver, firewall change or failure-injection test was activated by this documentation update.

## Current availability model

| Dependency | Current state | Failure impact | Existing mitigation | Remaining gap |
| --- | --- | --- | --- | --- |
| ASUS gateway | single device | loss of routing, local gateway services and Tailscale edge role | backup/restore, health checks, documented recovery | no HA peer / FHRP |
| WAN/ISP | single documented WAN | Internet and remote-overlay loss | WAN recovery logic, local LAN remains available | no validated dual-WAN failover |
| Router power | single router power input; site backup-power state not documented | gateway outage | boot/recovery validation | UPS/power-continuity baseline not yet documented |
| Router-attached SSD | single local persistent-storage device | Entware/services/RouterCloud/swap impact | off-router backup, recovery procedures | no live storage redundancy |
| Fedora monitoring host | single monitoring/collector host | monitoring, dashboards and collector visibility lost | services restart automatically; gateway dataplane remains separate | no monitoring HA |
| Pi-hole + Unbound | co-resident on router, with firmware dnsmasq sharing the same Unbound | client DNS filtering/resolution degraded if FTL or shared Unbound fails; all services lost if router/SSD/power fails | health checks; DNS Guard v3.2 **router-system-resolver-only** bootstrap/fail-open | no proven LAN/Tailscale client DNS failover; no independent filtered secondary |
| Tailscale control/Internet dependency | external dependency | remote overlay unavailable | trusted local recovery path | no independent remote OOB channel |

## DNS availability boundaries — 2026-10-13

- **Router versus clients:** DNS Guard v3.2 can move the **router's own
  system resolver** to an independent WAN bootstrap resolver under documented
  conditions; this is not a general continuity guarantee for LAN DHCP clients
  or Tailscale peers. The bootstrap DNS intentionally does **not** preserve
  Pi-hole blocking policy.
- **Shared upstream:** current Pi-hole and firmware dnsmasq both depend on
  the single ASUS Unbound. Two local DNS frontend processes do not constitute
  independent DNS failure domains.
- **Missing recovery coverage:** [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129)
  remains OPEN for full Pi-hole-aware clean-device restoration;
  [#213](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/213)
  covers cache-masked upstream failures;
  [#214](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/214)
  covers independent monitoring for lost DNS Guard cron scheduling.
- **Current scheduling decision (2026-10-13):** [client DNS failover #212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212) is **PAUSED** because no suitable independent hardware is available. A second DNS listener on the same ASUS is not a separate failure domain. Merged PR #227 documents lab research only; it does not resolve the direct-sidecar bypass or authorize a pilot.
- **Optional, not purchased or deployed:** [#216](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/216)
  evaluates a second, separately powered/storage-backed Pi-hole **and its own
  Unbound**. It could reduce dependence on the ASUS DNS stack, but two DHCP
  DNS addresses do not ensure strict standby selection; ASUS classic-DNS
  interception rules, client filtering parity and real failover must be
  validated before considering it resilient.
- **Gateway remains a single point of failure:** even a second functioning DNS
  host would not preserve WAN routing or the existing ASUS Tailscale exit node
  if the main router fails. A shared switch/power source may also remain an SPOF.

No secondary resolver, DNS failover or additional network hardware is present
in the validated topology. No live configuration was changed in this review.

## Enterprise HA mechanisms applicability

| Mechanism | Current status | Reason |
| --- | --- | --- |
| VRRP/HSRP/FHRP | N/A | only one documented gateway |
| LACP | N/A | no documented redundant managed-switch uplinks |
| STP/RSTP design | N/A | no documented switched access/distribution topology requiring loop prevention |
| MLAG/stacking | N/A | no redundant managed switch pair |
| redundant WAN | NOT IMPLEMENTED | current reference design explicitly has no redundant WAN |
| redundant PSU | NOT AVAILABLE / NOT CLAIMED | consumer-router platform |
| UPS | NOT YET DOCUMENTED / VALIDATED | requires separate power-continuity assessment |

These are not configuration omissions on the current topology; most require
additional hardware and a different physical design.

## Recoverability already present

The project already includes:

- verified project backup and manifest checks;
- restore dry-run and clean-room validation for the pre-Pi-hole baseline;
- rollback logic;
- current-state DR gap tracking for Pi-hole under issue #129;
- validated boot ordering, swap recovery and health checks;
- off-router encrypted/versioned RouterCloud backup;
- source-controlled configuration and CI.

## Required next maturity steps

1. Complete the current Pi-hole-aware DR rebuild and measure actual recovery
   time and acceptable data/configuration-loss window before publishing RTO/RPO.
2. Document power dependencies for router, ISP CPE/ONT and Fedora.
3. Decide whether a UPS is required; if adopted, record capacity, expected
   runtime, monitored status and shutdown/restart behavior.
4. Preserve the present single-gateway baseline. If OPNsense is revisited in an
   unscheduled future, compare dual-WAN, standby gateway, separate DNS power/
   network failure domains and physical recovery needs before any purchase.
   No ASUS RT-BE88U migration is currently planned.
5. Keep monitoring availability separate from gateway availability.

## Service-level claim boundary

The project currently supports **validated recovery**, not high availability.
No SLA, measured failover time, gateway redundancy or uninterrupted power claim
should be inferred from successful reboot/restore tests.
