# Availability, redundancy and single points of failure

**Status:** CURRENT  
**Last reviewed:** 2026-10-07

## Purpose

Separate **high availability** from **recoverability**. The project has strong
backup, validation and recovery engineering, but the current reference
deployment is not a redundant gateway architecture.

## Current availability model

| Dependency | Current state | Failure impact | Existing mitigation | Remaining gap |
| --- | --- | --- | --- | --- |
| ASUS gateway | single device | loss of routing, local gateway services and Tailscale edge role | backup/restore, health checks, documented recovery | no HA peer / FHRP |
| WAN/ISP | single documented WAN | Internet and remote-overlay loss | WAN recovery logic, local LAN remains available | no validated dual-WAN failover |
| Router power | single router power input; site backup-power state not documented | gateway outage | boot/recovery validation | UPS/power-continuity baseline not yet documented |
| Router-attached SSD | single local persistent-storage device | Entware/services/RouterCloud/swap impact | off-router backup, recovery procedures | no live storage redundancy |
| Fedora monitoring host | single monitoring/collector host | monitoring, dashboards and collector visibility lost | services restart automatically; gateway dataplane remains separate | no monitoring HA |
| Pi-hole + Unbound | co-resident on router | DNS filtering/resolution degradation if router/service fails | DNS Guard fail-open for local resolver-stack failure, health checks | does not survive complete router/power loss |
| Tailscale control/Internet dependency | external dependency | remote overlay unavailable | trusted local recovery path | no independent remote OOB channel |

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
4. During RT-BE88U migration planning, assess whether dual-WAN or standby-gateway
   capability is justified by the service objectives.
5. Keep monitoring availability separate from gateway availability.

## Service-level claim boundary

The project currently supports **validated recovery**, not high availability.
No SLA, measured failover time, gateway redundancy or uninterrupted power claim
should be inferred from successful reboot/restore tests.
