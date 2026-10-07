# Addressing and trust-zone plan

**Status:** CURRENT + PLANNED SEGMENTATION  
**Last reviewed:** 2026-10-07

## Purpose

Provide one authoritative public map of address ownership, service aliases and
trust-zone intent without publishing unnecessary deployment-specific endpoint
identifiers.

## Current reference addressing

| Role | Address / range | Ownership | Status |
| --- | --- | --- | --- |
| Main LAN | 192.168.50.0/24 | ASUS DHCP/LAN | CURRENT |
| Router LAN gateway | 192.168.50.1 | Asuswrt-Merlin | CURRENT |
| Pi-hole service alias | 192.168.50.253 | router-local dedicated alias | CURRENT |
| RouterCloud HTTPS alias | 192.168.50.254 | router-local dedicated alias | CURRENT |
| Tailnet IPv4 range | 100.64.0.0/10 | Tailscale overlay | CURRENT |
| WAN IPv4 | public/dynamic in reference deployment | ISP / ASUS WAN | CURRENT; exact address intentionally omitted |
| Native WAN/LAN IPv6 | none in current reference state | — | DISABLED / NOT EXPOSED |
| Tailscale IPv6 | overlay-controlled | Tailscale + project fail-closed guards | CURRENT, granular allow policy not claimed |

Per-device administrative DHCP reservations and individual Tailscale node
addresses are intentionally omitted from the public IPAM document. Private
deployment configuration remains the source for exact host assignments.

## Current zone model

The current production design does **not** yet implement separate VLAN-backed
Trusted/IoT/Guest zones.

| Zone | Current state | Security boundary |
| --- | --- | --- |
| Main trusted LAN/WLAN | IMPLEMENTED | platform LAN controls + source-restricted management |
| Tailscale remote-access overlay | IMPLEMENTED | Tailscale Grants + project-owned firewall rules |
| Router/service-local aliases | IMPLEMENTED | router-local address ownership + service/firewall policy |
| Guest | NOT DEPLOYED in validated baseline | guest BSS disabled in current documented state |
| IoT | NOT SEGMENTED | currently shares the main LAN where present |
| DMZ | NOT IMPLEMENTED / NOT REQUIRED for current WAN exposure model | no project application is intentionally exposed directly to WAN |

The lack of a DMZ is a deliberate current-state decision: the project does not
publish RouterCloud, Grafana, Pi-hole or the ASUS management plane directly to
the Internet.

## Planned Trusted / IoT / Guest design

Issue #143 owns the future segmentation design. VLAN IDs and subnets are
deliberately **TBD** until the target platform capability and device
dependencies are measured.

Provisional policy intent:

| Source zone | Trusted/Admin | IoT | Guest | Router management | Internet |
| --- | ---: | ---: | ---: | ---: | ---: |
| Trusted/Admin | allow | selected only | deny | allow | allow |
| IoT | deny by default | required local only | deny | deny | selected/allow as required |
| Guest | deny | deny | client-isolated | deny | allow |
| Tailscale admin | selected | selected only | deny | allow | policy-controlled |
| WAN | deny | deny | deny | deny | n/a |

This matrix is a **design target, not current production evidence**.

## Services that must be considered before segmentation

A future zone migration must explicitly test:

- DHCP and per-zone DNS advertisement;
- Pi-hole reachability and local/reverse naming;
- printer/service discovery;
- mDNS/multicast requirements;
- RouterCloud reachability;
- management-plane access;
- Tailscale subnet routing and exit-node behavior;
- monitoring/log forwarding;
- device onboarding and recovery paths.

## Address-management rules

- Do not reuse the router/service aliases as endpoint DHCP addresses.
- Keep infrastructure service addresses stable.
- Keep public documentation free of unnecessary endpoint-specific addresses.
- Any subnet/VLAN change requires updates to firewall policy, DHCP/DNS,
  Tailscale advertisement and validation evidence.
- Future VLAN IDs and subnets must be assigned only after the zone flow matrix
  is accepted.

## Claim boundary

This file documents the current public addressing model and the intended future
zone policy. It does not claim that VLAN segmentation is already active.
