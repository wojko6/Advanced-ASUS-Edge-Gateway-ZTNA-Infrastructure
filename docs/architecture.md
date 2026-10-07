# Architecture

The current architecture is documented as a **source-controlled canonical network-design set** rather than a single raster image. The set now includes physical topology, addressing/trust-zone ownership, logical datapaths, availability/failure-domain boundaries and Layer-2 control applicability. Each document has one purpose, explicit claim boundaries and links back to current implementation or dated live evidence.

Start with the [Network design documentation index](network-design.md).

## Canonical architecture documents

1. [Physical Topology](architecture/physical-topology.md)  
   Hardware roles, attachment relationships, current single points of failure and the absence of a separate access/distribution or OOB layer.

2. [High-Level Architecture and Trust Boundaries](architecture/high-level-trust-boundaries.md)  
   Identity/policy, Tailscale overlay, project-owned firewall boundary, router management, selected LAN forwarding and optional exit-node egress.

3. [Addressing and Trust-Zone Plan](architecture/addressing-and-zones.md)  
   Current public IPAM/service-alias ownership plus the explicitly planned Trusted/IoT/Guest zone model.

4. [DNS Enforcement Flow](architecture/dns-enforcement-flow.md)  
   Exact LAN/br0 and Tailscale/tailscale0 classic-DNS paths, EDGE_LAN_DNS_PREROUTING, EDGE_TS_PREROUTING, dnsmasq, Unbound, direct LAN DoT/TCP 853 rejection and explicit encrypted-DNS scope limits.

5. [Tailscale Management and Exit-Node Flow](architecture/tailscale-management-exit-node-flow.md)  
   Source-scoped management, default-deny behavior, selected LAN forwarding, EDGE_TS_FORWARD, WAN egress and platform-owned NAT.

6. [Boot and Service Dependency Flow](architecture/boot-service-dependency-flow.md)  
   Current reference post-mount/AMTM ordering, pre-Entware swap evidence, repository services-start recovery behavior, DNS Guard v3.1 bootstrap/steady-state resolver policy, firewall apply and WAN-triggered Tailscale restart.

7. [Availability, Redundancy and Single Points of Failure](architecture/availability-and-redundancy.md)  
   Explicit separation between recoverability and high availability, plus applicability of FHRP/LACP/redundant-WAN controls.

8. [L2 and Network-Access Security Applicability](architecture/l2-security-applicability.md)  
   Current/deferred/N/A treatment of VLANs, DHCP Snooping, DAI, Port Security, STP protections, 802.1X, RADIUS and TACACS+.

The old [Architecture.png](images/Architecture.png) is retained only as a historical/illustrative artifact. It is not a source of truth for current ports, interfaces, chain ownership or validation status. See [docs/images/README.md](images/README.md).

## Logical components

| Layer | Component | Responsibility |
|---|---|---|
| Identity/policy | Tailscale Grants | User/group/device authorization and exit-node entitlement |
| Overlay | Tailscale | Encrypted connectivity, subnet advertisement and optional exit routing |
| Local enforcement | project-owned iptables/ip6tables | Router-service policy, selected LAN access, default-deny forwarding, LAN DNS/DoT controls and fail-closed Tailscale IPv6 guards |
| DNS | Pi-hole + dnsmasq + Unbound | Main-LAN DHCP filtering on the dedicated Pi-hole listener, firmware DHCP/local naming and classic-DNS interception, recursive resolution and DNSSEC validation |
| Observability | syslog-ng + off-router Fedora monitoring stack | Authenticated system-log forwarding, read-only metrics/probes, VictoriaMetrics/Grafana, and the live-validated Pi-hole-visible Alloy/Loki DNS analytics pipeline |
| Operations | Merlin hooks + project scripts | Startup/recovery coordination, health checks, backup/restore, evidence collection and controlled updates |

## Ownership boundaries

### Tailscale versus local firewall

Tailscale is intentionally configured with **netfilter-mode=off**. The project owns the local EDGE_TS_* iptables policy instead of relying on Tailscale-managed ts-* chains.

Tailscale Grants and local firewall rules are independent boundaries, but their
current strength differs by datapath:

- Grants decide which identities/devices are entitled to reach a resource or use the exit node.
- EDGE_TS_INPUT and selected-LAN EDGE_TS_FORWARD rules enforce local source, destination and port policy.
- The current exit-node EDGE_TS_FORWARD rule is WAN-egress scoped but not yet locally source-scoped; issue #176 tracks a second local source allowlist for tailnet -> WAN forwarding.
- Router or service authentication still applies after network reachability is granted.

### Project forwarding versus platform NAT

The project owns exit-node forwarding policy in EDGE_TS_FORWARD. It does **not** add its own exit-node MASQUERADE rule. Current-firmware live evidence validates the reference ownership model as:

**project-owned filtering + platform-owned WAN NAT**

### DNS ownership

The current reference router uses split port-53 ownership. Pi-hole FTL owns a dedicated main-LAN alias and is the only DNS server advertised to main-LAN DHCP clients. Firmware dnsmasq continues to own the router LAN and Tailscale port-53 sockets for DHCP/local-name duties and the existing project classic-DNS interception path. Pi-hole and dnsmasq both use Unbound on 127.0.0.1:53535 for ordinary external resolution.

The 2026-09-28 cutover did not by itself move the existing LAN/Tailscale interception redirects behind Pi-hole. Later 2026-10-06 work added source-scoped Pi-hole handling for selected classic-DNS Tailscale clients and separately validated the router-system-resolver -> Pi-hole path used by the tested Android LTE exit-node DNS flow after DNS Guard v3.1. Non-selected generic Tailscale classic-DNS interception still retains the dnsmasq -> Unbound fallback, and encrypted DNS remains outside the universal enforcement claim.

### System-resolver DNS Guard boundary

The router's own system resolver follows a two-phase policy managed by DNS
Guard v3.1:

- cold boot / local DNS failure / sticky break-glass -> independent WAN
  bootstrap DNS;
- healthy steady state -> dedicated Pi-hole alias -> Unbound.

This prevents the NTP -> DNS -> Pi-hole -> Unbound cold-boot dependency cycle
observed on 2026-10-06. The fail-open behavior intentionally prioritizes router
DNS availability over Pi-hole filtering while the local resolver stack is
unhealthy.

The complete incident narrative, including the user-visible symptom that normal
websites stopped opening while IP connectivity remained available, is documented
in the [DNS bootstrap deadlock incident case study](case-studies/dns-bootstrap-deadlock-dns-guard-v3.1.md).

### DNS analytics boundary

Issue #108 is a live-validated **off-router observability extension**, not a
change to the resolver datapath. Its source is the query history already written
by Pi-hole FTL for DHCP-managed main-LAN clients. The Fedora collector reads
that source incrementally and read-only; checkpoint/journal state, the private
NDJSON spool, Alloy, Loki, retention and Grafana processing stay off-router.

The resulting dataset is described as **Pi-hole-visible DNS activity**. It does
not automatically include firmware-dnsmasq interception paths or encrypted-DNS
bypasses. A controlled 2026-09-28 test specifically confirmed the Tailscale
classic-DNS boundary: the query was visible on `tailscale0` but absent from
Pi-hole history, matching the existing dnsmasq path. The hard-coded external
LAN interception path remains a separate correlation item.

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

Planned migration target: **ASUS RT-BE88U / compatible Asuswrt-Merlin 3006.x**. The current TUF-AX5400 remains the reference platform until that migration is separately validated.

Current architecture claims are anchored to dated evidence:

- **2026-09-23:** management negative test confirmed that tailnet membership alone does not grant TCP/8443 router management.
- **2026-09-23:** AUDIT-02 revalidated exit-node forwarding plus platform-owned WAN NAT on the current firmware.
- **2026-09-27:** AUDIT-03 revalidated the current-firmware Fedora classic-DNS datapath through tailscale0 → EDGE_TS_PREROUTING → dnsmasq → Unbound for both UDP and TCP 53.
- **2026-09-27:** #66 recorded 3/3 clean startup cycles after the reference pre-Entware swap-order correction.
- **2026-09-27:** #67 reconfirmed Android exit-node public-IP behavior after reboot with a clean router health check.
- **2026-09-27:** #65 accepted Diversion Large as the then-current filtering baseline after multi-day use, refresh, DNS-path and resource checks; that historical baseline was replaced on the main-LAN DHCP path the next day by #80.
- **2026-09-28:** #80 migrated the main-LAN DHCP filtering path to Pi-hole, retained Unbound and firmware local naming, removed duplicate filtering/statistics services, corrected a pre-Entware swap regression discovered during reboot, and passed the final swap/Tailscale/Pi-hole/Unbound reboot validation.
- **2026-10-06:** the reference Tailscale runtime was upgraded from the historical 1.102.3 checkpoint to checksum-verified official ARM 1.103.375 unstable/dev; controlled daemon restart and later full cold boot passed.
- **2026-10-06:** DNS Guard v3.1 was production-validated with fail-open bootstrap DNS, conditional Pi-hole promotion, sticky break-glass, watchdog recovery and full cold boot.
- **2026-10-06:** Android LTE with the ASUS selected as exit node resolved a fresh unique hostname through the router system resolver to the local Pi-hole alias and Unbound.
- **2026-10-07:** a multi-vantage port-exposure audit validated LAN/Tailscale trust boundaries, source-specific Fedora syslog access, a genuine mobile-Internet public-IPv4 TCP probe with all selected tested ports filtered/time-out, and native WAN IPv6 disabled with no WAN IPv6 address/default route. External WAN UDP remains explicitly untested.

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
