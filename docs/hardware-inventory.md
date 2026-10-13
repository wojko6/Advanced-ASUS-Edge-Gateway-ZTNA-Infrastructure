# Hardware and infrastructure inventory

**Status:** CURRENT / PUBLIC SUMMARY  
**Last reviewed:** 2026-10-12 (platform strategy only; hardware identification unchanged)

## Purpose

Provide a concise inventory of infrastructure roles relevant to the network
design. Deployment-specific serial numbers, MAC addresses, public addresses and
unnecessary endpoint identifiers remain private.

## Current reference components

| Component | Role | Current design status | Notes |
| --- | --- | --- | --- |
| ASUS TUF-AX5400 | primary edge gateway, firewall, routing, DHCP/local naming, Tailscale gateway, local DNS/service host | REFERENCE / CURRENT | Asuswrt-Merlin GNUton 3004.388.11_1-gnuton1_tuf; consumer platform with no gateway HA claim |
| Router-attached SSD | persistent Entware, RouterCloud data, swap and service storage | CURRENT | separate logical storage roles are documented; no live storage redundancy |
| Fedora workstation | trusted administration, monitoring, analytics, logging collector, build/recovery tooling | CURRENT | kept off the gateway dataplane; monitoring availability depends on this host |
| LAN/WLAN endpoints | clients and controlled validation peers | CURRENT | exact device inventory is not part of the public network-device inventory |
| Remote Tailscale peers | remote management/validation/exit-node clients | CURRENT | individual node identities and addresses intentionally omitted |
| ISP handoff/CPE | WAN connectivity | PROVIDER-SPECIFIC / NOT PUBLICLY INVENTORIED | public design records the WAN dependency, not unnecessary provider identifiers |

## Current gateway and future platform evaluation

**CURRENT:** ASUS TUF-AX5400. **No ASUS RT-BE88U purchase/migration is
planned** following the 2026-10-12 decision. The RT-BE88U technical/benchmark
records are retained solely as historical research.

**POSSIBLE FUTURE:** OPNsense/x86; no purchase, production deployment or
timeline agreed. Initial research may run as an isolated VM on a separate
Windows 11 laptop with 16 GiB RAM. The available external USB Ethernet
adapter is not needed to produce two **virtual** WAN/LAN NICs. Hypervisor and
guest are **not installed/validated** as of this checkpoint. Do not publish
private host IDs or adapter MACs.

Any later OPNsense edge migration is a new-design and full-revalidation project,
not an in-place port of Asuswrt/iptables/Entware/JFFS workflows. Protect the
current ASUS, gateway availability and trusted LAN recovery at all stages.
See [platform decision](architecture/platform-direction-2026-10-12.md).

## Selection criteria

Infrastructure changes should be evaluated against:

- supported firmware lifecycle and reproducibility;
- ability to preserve the project-owned firewall model;
- sufficient memory/storage behavior for the bounded router workload;
- VLAN/network capability required by issue #143;
- predictable local recovery access;
- logging/monitoring integration without exposing new management listeners;
- backup/restore and controlled rollback;
- measurable performance rather than advertised throughput alone.

## Distribution/access layer

No managed MDF/IDF, access/distribution switch hierarchy or redundant switch
fabric is part of the current documented reference topology.

If a managed switch or dedicated AP layer is added, record at minimum:

- vendor/model/firmware;
- role and management boundary;
- uplink media/speed;
- access/trunk port map;
- VLAN membership;
- STP/RSTP role and edge protections;
- LACP/stacking if used;
- PoE/power dependency;
- UPS dependency;
- configuration-backup method.

## Claim boundary

This is a public design inventory, not an asset-management database. Exact
serials, MACs, per-device reservations and private administrative identifiers
belong in private operational inventory rather than the public repository.
