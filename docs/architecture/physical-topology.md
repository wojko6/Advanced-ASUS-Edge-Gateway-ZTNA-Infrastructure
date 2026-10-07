# Physical topology

**Status:** CURRENT  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton  
**Last reviewed:** 2026-10-07

## Purpose

This document fills the physical/L1-L2 view that the logical trust-boundary
diagrams intentionally do not provide. It records only the hardware and
attachment relationships supported by the current project documentation.

~~~mermaid
flowchart TB
    ISP["ISP / public IPv4 service"] -->|"WAN"| R["ASUS TUF-AX5400<br/>edge gateway"]

    SSD["Router-attached SSD<br/>ENTWARE + ROUTER_DATA + swap"] --- R

    R -->|"trusted LAN / WLAN"| F["Fedora administration + monitoring workstation"]
    R -->|"trusted LAN / WLAN"| C["LAN / Wi-Fi clients"]
    R -->|"trusted LAN / WLAN"| P["local peripherals / services<br/>where explicitly allowed"]

    T["Remote Tailscale clients"] -. "encrypted overlay over Internet" .-> R

    F --> VM["Off-router observability<br/>VictoriaMetrics / Grafana / Loki / Alloy<br/>Blackbox / syslog-ng collector"]
~~~

## Documented physical roles

| Component | Current role | Availability note |
| --- | --- | --- |
| ASUS TUF-AX5400 | Internet edge, routing, firewall, DHCP/local naming, DNS-service hosting, Tailscale gateway | Single gateway; no HA peer |
| Router-attached SSD | Entware runtime, RouterCloud data, swap and project service storage | Persistent storage is a single local failure domain; backups are separate |
| Fedora workstation | Administration, monitoring, logging/analytics and recovery tooling | Monitoring depends on this host being available; gateway forwarding does not |
| LAN/WLAN clients | Trusted reference clients and controlled test clients | Current main LAN is not yet segmented into Trusted/IoT/Guest production zones |
| Remote Tailscale clients | Remote administration / selected service access / exit-node use according to policy | Overlay availability depends on Tailscale and Internet reachability |

## What is not part of the documented reference topology

The repository does not currently document a managed access/distribution switch
layer, redundant gateway pair, redundant WAN, dedicated wireless-controller
plane, console server or physically separate out-of-band management network.

That means enterprise mechanisms such as LACP uplink aggregation, STP/RSTP root
design and FHRP/VRRP/HSRP are **not current implementation claims**. They become
relevant only if the physical topology gains redundant switches/links/gateways.

## Distribution / access layer boundary

No separate MDF/IDF or access/distribution hierarchy is claimed for the current
Home/SMB reference deployment. If a managed switch or additional AP layer is
introduced, this document must be updated with:

- device model and role;
- uplink/downlink media and negotiated speed;
- switch/AP management address ownership;
- VLAN/trunk/access-port mapping;
- STP/RSTP role and edge-port protections;
- LACP/MLAG behavior where supported;
- power/UPS dependency;
- failure-domain impact.

## Recovery path

A separate hardware out-of-band channel is not available on the current
consumer-router platform. Trusted local LAN access and physical access remain the
break-glass recovery path if Tailscale or normal remote administration fails.

## Claim boundary

This is a topology document, not cabling certification. Port numbers, cable
category, exact physical room placement and ISP CPE details are not currently
recorded as validated design data and must not be invented from the logical
architecture.
