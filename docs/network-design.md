# Network design documentation index

**Status:** CURRENT  
**Applies to:** reference ASUS TUF-AX5400 deployment  
**Last reviewed:** 2026-10-07

This document is the entry point for the network-design view of the project.
It complements the repository's incident/case-study material by organizing the
current design from physical topology through security, operations and
acceptance.

The project remains an **enterprise-style Home/SMB lab**, not an enterprise
high-availability network. Where a classic enterprise control is not supported
or not justified by the current topology, the documentation marks it as
N/A, PLANNED or NOT VALIDATED instead of implying that it exists.

## 1. Scope and requirements

- [Project status](../PROJECT-STATUS.md)
- [Requirements and acceptance map](requirements.md)
- [Compatibility and revalidation](compatibility.md)

## 2. Physical topology and hardware boundary

- [Physical topology](architecture/physical-topology.md)
- [High-level architecture and trust boundaries](architecture/high-level-trust-boundaries.md)

The current reference design uses one ASUS edge gateway and off-router Fedora
for monitoring/administration. No redundant gateway or redundant WAN is claimed.

## 3. Addressing, trust zones and segmentation

- [Addressing and zone plan](architecture/addressing-and-zones.md)
- [Firewall policy](firewall-policy.md)
- [Tailscale management and exit-node flow](architecture/tailscale-management-exit-node-flow.md)

Current production traffic is still based on a trusted main LAN plus Tailscale
overlay controls. Trusted/IoT/Guest segmentation is a planned design item under
issue #143 and must not be described as deployed.

## 4. Routing, NAT and DNS

- [DNS enforcement flow](architecture/dns-enforcement-flow.md)
- [Firewall policy](firewall-policy.md)
- [Android Pi-hole/Tailscale policy](android-pihole-tailscale-policy.md)

The project explicitly separates project-owned filtering from platform-owned WAN
NAT and keeps encrypted-DNS bypasses outside universal enforcement claims.

## 5. Security architecture

- [Security design](security.md)
- [Threat model](threat-model.md)
- [L2 and network-access security applicability](architecture/l2-security-applicability.md)
- [Port exposure and trust-boundary audit](case-studies/port-exposure-trust-boundary-audit-2026-10-07.md)

## 6. Management plane

- [Operations](operations.md)
- [Deployment guide](deployment-pl.md)
- [Tailscale maintenance](tailscale-maintenance.md)

The current recovery/management model uses trusted LAN access, SSH, router HTTPS,
and Tailscale. A physically separate out-of-band management network or console
server is not part of the current reference platform.

## 7. Monitoring, logging and alerting

- [Monitoring reference deployment](../monitoring/README.md)
- [Centralized logging with mTLS](centralized-logging.md)
- [DNS visibility and client analytics](network-dns-visibility-client-activity-analytics.md)

SNMP and NetFlow/IPFIX are not required for the current validated baseline.
Read-only SSH collection, Traffic Analyzer import, Blackbox probes, syslog-ng,
VictoriaMetrics, Loki, Alloy and Grafana provide the present observability path.

## 8. Availability, redundancy and failure domains

- [Availability, redundancy and single points of failure](architecture/availability-and-redundancy.md)
- [Swap and memory reliability](swap-and-memory-reliability.md)
- [Router disaster recovery](router-disaster-recovery.md)

High availability must not be confused with recoverability. The reference
deployment has documented recovery controls but no gateway HA, no redundant WAN
and no validated power-continuity/UPS baseline.

## 9. Testing and evidence

- [Testing and evidence collection](testing.md)
- [Evidence collection](evidence-collection.md)
- [Case-study index](CASE-STUDIES.md)

Expected behavior, CI/static checks and live observations are separate evidence
classes.

## 10. Known gaps and roadmap

- [Roadmap](roadmap.md)
- issue #176 — router-local exit-node source scoping
- issue #129 — Pi-hole-aware current-state disaster recovery
- issue #143 — Trusted/IoT/Guest segmentation design
- issue #178 — complete Grafana notification policy and mobile escalation

This index is intentionally concise. Detailed implementation and operational
truth remains in the linked source documents.
