# Architecture

The current architecture is documented as a **source-controlled canonical diagram set** rather than a single raster image. Each diagram has one purpose, explicit claim boundaries and links back to current implementation or dated live evidence.

## Canonical architecture diagrams

1. [High-Level Architecture and Trust Boundaries](architecture/high-level-trust-boundaries.md)  
   Identity/policy, Tailscale overlay, project-owned firewall boundary, router management, selected LAN forwarding and optional exit-node egress.

2. [DNS Enforcement Flow](architecture/dns-enforcement-flow.md)  
   Exact LAN/br0 and Tailscale/tailscale0 classic-DNS paths, EDGE_LAN_DNS_PREROUTING, EDGE_TS_PREROUTING, dnsmasq, Unbound, direct LAN DoT/TCP 853 rejection and explicit encrypted-DNS scope limits.

3. [Tailscale Management and Exit-Node Flow](architecture/tailscale-management-exit-node-flow.md)  
   Source-scoped management, default-deny behavior, selected LAN forwarding, EDGE_TS_FORWARD, WAN egress and platform-owned NAT.

4. [Boot and Service Dependency Flow](architecture/boot-service-dependency-flow.md)  
   Current reference post-mount/AMTM ordering, pre-Entware swap evidence, repository services-start recovery behavior, Unbound/dnsmasq interaction, firewall apply and WAN-DNS-driven Tailscale restart.

The old [Architecture.png](images/Architecture.png) is retained only as a historical/illustrative artifact. It is not a source of truth for current ports, interfaces, chain ownership or validation status. See [docs/images/README.md](images/README.md).

## Logical components

| Layer | Component | Responsibility |
|---|---|---|
| Identity/policy | Tailscale Grants | User/group/device authorization and exit-node entitlement |
| Overlay | Tailscale | Encrypted connectivity, subnet advertisement and optional exit routing |
| Local enforcement | project-owned iptables/ip6tables | Router-service policy, selected LAN access, default-deny forwarding, LAN DNS/DoT controls and fail-closed Tailscale IPv6 guards |
| DNS | dnsmasq + Unbound | Local port-53 ownership, classic-DNS interception, recursive resolution and DNSSEC validation |
| Observability | syslog-ng | Local logging and optional remote forwarding |
| Operations | Merlin hooks + project scripts | Startup/recovery coordination, health checks, backup/restore, evidence collection and controlled updates |

## Ownership boundaries

### Tailscale versus local firewall

Tailscale is intentionally configured with **netfilter-mode=off**. The project owns the local EDGE_TS_* iptables policy instead of relying on Tailscale-managed ts-* chains.

Tailscale Grants and local firewall rules are independent boundaries:

- Grants decide which identities/devices are entitled to reach a resource or use the exit node.
- EDGE_TS_INPUT and EDGE_TS_FORWARD enforce local source, destination, port and WAN-interface policy.
- Router or service authentication still applies after network reachability is granted.

### Project forwarding versus platform NAT

The project owns exit-node forwarding policy in EDGE_TS_FORWARD. It does **not** add its own exit-node MASQUERADE rule. Current-firmware live evidence validates the reference ownership model as:

**project-owned filtering + platform-owned WAN NAT**

### DNS ownership

dnsmasq owns port 53 and forwards ordinary queries to Unbound on 127.0.0.1:53535.

Current validated IPv4 controls are intentionally scoped:

- LAN/br0 classic TCP/UDP 53: enforced through EDGE_LAN_DNS_PREROUTING.
- Tailscale/tailscale0 classic TCP/UDP 53: enforced through EDGE_TS_PREROUTING.
- Direct LAN/br0 DoT TCP/853: rejected through EDGE_LAN_DOT_FORWARD.
- DoH/HTTPS 443, DoQ/QUIC, VPN-carried DNS, application-specific encrypted DNS and IPv6 resolver paths: **not covered by a universal enforcement claim**.

### Boot ownership

On the reference router, AMTM owns normal Entware startup from post-mount. The project services-start hook detects that ownership, waits for /opt and external Entware startup to settle, then preserves stable services or performs bounded recovery.

The 2026-09-27 #66 evidence also records a current reference-router post-mount correction that activates swap **before** AMTM starts Entware. That live correction is not currently installed by this repository and must not be confused with the repository's own swap guard before Tailscale recovery.

## Current reference validation

Reference router: **ASUS TUF-AX5400**  
Reference firmware: **GNUton / Asuswrt-Merlin 3004.388.11_1-gnuton1_tuf**

Current architecture claims are anchored to dated evidence:

- **2026-09-23:** management negative test confirmed that tailnet membership alone does not grant TCP/8443 router management.
- **2026-09-23:** AUDIT-02 revalidated exit-node forwarding plus platform-owned WAN NAT on the current firmware.
- **2026-09-27:** AUDIT-03 revalidated the current-firmware Fedora classic-DNS datapath through tailscale0 → EDGE_TS_PREROUTING → dnsmasq → Unbound for both UDP and TCP 53.
- **2026-09-27:** #66 recorded 3/3 clean startup cycles after the reference pre-Entware swap-order correction.
- **2026-09-27:** #67 reconfirmed Android exit-node public-IP behavior after reboot with a clean router health check.
- **2026-09-27:** #65 accepted Diversion Large as the current filtering baseline after multi-day use, refresh, DNS-path and resource checks.

These dated results do not establish universal firmware compatibility or enforcement outside their stated protocol/interface scope. Time-sensitive project status remains governed by [PROJECT-STATUS.md](../PROJECT-STATUS.md) and the dated [evidence](../evidence/) tree.

## Primary implementation sources

- [router/scripts/firewall-start](../router/scripts/firewall-start)
- [router/scripts/services-start](../router/scripts/services-start)
- [router/scripts/wan-event-handler](../router/scripts/wan-event-handler)
- [scripts/healthcheck.sh](../scripts/healthcheck.sh)
- [config/edge.conf.example](../config/edge.conf.example)
- [config/dnsmasq.conf.add.example](../config/dnsmasq.conf.add.example)
- [config/unbound.conf.example](../config/unbound.conf.example)
- [config/tailscale/policy.example.hujson](../config/tailscale/policy.example.hujson)
