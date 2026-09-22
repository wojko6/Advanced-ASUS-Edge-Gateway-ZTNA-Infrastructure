# Firewall policy

## Managed chains

The project owns three IPv4 chains and two fail-closed IPv6 guard chains:

- `filter/EDGE_TS_INPUT`: traffic from `tailscale0` to the router.
- `filter/EDGE_TS_FORWARD`: traffic from `tailscale0` through the router.
- `nat/EDGE_TS_PREROUTING`: DNS redirection and source-scoped router HTTPS DNAT before routing.
- `filter/EDGE_TS6_INPUT` and `filter/EDGE_TS6_FORWARD`: block new IPv6 traffic from `tailscale0` until an equivalent granular IPv6 policy exists.

Tailscale netfilter management is intentionally disabled with `netfilter-mode=off`.
The project-owned `EDGE_TS_*` chains are therefore the enforcement point for
Tailscale traffic. Native `ts-input`, `ts-forward`, and `ts-postrouting` chains
are not expected during normal operation and their presence is reported by the
health check.

The firewall script does not flush Merlin or user-owned chains. Before attaching
each managed chain, it deletes duplicate project-owned jumps and inserts exactly
one interface-scoped jump.

Before the first iptables mutation, `firewall-start` validates the configured
booleans, ports, interface names, router IPv4 address, tailnet IPv4 CIDR, admin
and printer source addresses/CIDRs, allowed LAN destination addresses/CIDRs, and
optional printer IPv4 address. When exit-node mode is enabled, a configured WAN
interface is validated or dynamic WAN auto-detection is resolved and validated
at the same pre-mutation boundary. Malformed policy input or failure to determine
a valid WAN interface is therefore rejected before the temporary fail-closed
guards or managed chains are changed.

During the first migration, the script removes exact legacy `tailscale+` rules created by the earlier documented configuration: broad INPUT/FORWARD accepts, direct DNS accepts/DNAT, and the unrestricted router-HTTPS DNAT. It does not remove arbitrary third-party rules. Native Tailscale netfilter chains
left from an earlier configuration are treated as an invalid runtime state and
must be resolved before final validation. Router HTTPS DNAT is recreated inside
the managed NAT chain for `EDGE_ADMIN_TS_SOURCES` only.

During re-application, temporary interface-scoped IPv4 and IPv6 drop rules keep the transition fail-closed while managed chains are rebuilt. They are removed only after the corresponding policy and jump rules succeed. Apply from LAN because an error intentionally leaves these guards in place until firewall restart/recovery.

## Evaluation order

### Router input

1. Allow established/related return traffic.
2. Allow DNS from the CGNAT tailnet range when interception is enabled.
3. Allow HTTPS/SSH only from `EDGE_ADMIN_TS_SOURCES` and only when enabled.
4. Rate-limit security logging.
5. Drop everything else arriving from `tailscale0`.

### Forwarded traffic

1. Allow established/related return traffic.
2. Allow configured destination-host and destination-port combinations.
3. Optionally allow ICMP echo to those hosts.
4. Allow an optional printer policy only from configured Tailscale sources, through the configured LAN interface, to one printer and its required ports.
5. If exit-node mode is enabled, allow forwarding only to the detected/configured WAN interface.
6. Rate-limit security logging.
7. Drop all remaining forwarding from `tailscale0`.

### Exit-node NAT dependency

`EDGE_ENABLE_EXIT_NODE=1` creates the project-owned **filter** permission from
`tailscale0` to the selected WAN interface. It does not create a project-owned
`MASQUERADE` or `SNAT` rule. Because Tailscale runs with `netfilter-mode=off`,
this repository also does not rely on Tailscale's normal `ts-postrouting` NAT
chain.

A working IPv4 exit-node datapath therefore depends on the underlying Asuswrt /
Asuswrt-Merlin WAN NAT policy translating forwarded Tailscale client traffic as
it leaves the WAN interface.

That dependency was **live validated on 2026-09-22** on the reference router.
Read-only inspection confirmed IPv4 forwarding enabled, the project-owned WAN
forwarding rule in `EDGE_TS_FORWARD`, an Asuswrt-Merlin
`nat/POSTROUTING` WAN `MASQUERADE` rule, and a parent `FORWARD`
`RELATED,ESTABLISHED` accept rule for the return path. A controlled ICMP flow
with a fixed identifier was captured on `tailscale0` before NAT and on the WAN
interface after NAT with the same identifier and sequence numbers; replies were
observed in both views.

The validated ownership boundary is therefore:

- project-owned: Tailscale ingress/forward filtering and authorization;
- platform-owned: WAN source NAT and the parent established/related return path.

The project must not duplicate the firmware NAT merely to claim ownership.
Instead, when exit-node mode is enabled, health checking should treat the
platform WAN NAT/return-path rules and `net.ipv4.ip_forward=1` as explicit
runtime dependencies. A material firmware or firewall architecture change
requires the packet-level validation to be repeated.

Sanitized evidence: `evidence/2026-09-22/audit-02-exit-node-nat-validation.md`.

Useful read-only inspection commands remain:

```sh
iptables -t nat -S POSTROUTING
iptables -t nat -nvL POSTROUTING --line-numbers
iptables -S FORWARD
iptables -nvL FORWARD --line-numbers
```

Do not add or replace NAT rules merely to duplicate a working platform-owned
mechanism. If a future firmware state no longer provides the validated contract,
design and test the smallest explicit remediation in a disposable or planned
maintenance environment before changing the reference router.

## Source-scoped legacy printer access

Some legacy Android print plugins probe a printer over HTTP and SNMP before sending a job over IPP or raw TCP. Enable only the ports confirmed by packet capture:

```sh
EDGE_LAN_IF="br0"
EDGE_PRINTER_TS_SOURCES="192.0.2.95/32"
EDGE_PRINTER_LAN_IP="198.51.100.140"
EDGE_PRINTER_TCP_PORTS="80 631 9100"
EDGE_PRINTER_UDP_PORTS="161"
```

The sample uses RFC 5737 documentation ranges. Keep real device addresses in the router-local configuration. TCP rules accept only new connections; established/related traffic is handled by the first rule in the chain. The UDP printer rule intentionally has no conntrack-state restriction because repeated SNMP polls from legacy clients may not consistently appear as `NEW`.

### Android transport limitation

The source-scoped policy permits the configured flows, but it cannot make a
mobile print plugin support every Android network transport. A live test with a
Samsung legacy print plugin produced the following results over the same
Tailscale subnet route:

- cellular data: SNMP request/response traffic succeeded, but the plugin did not
  open an IPP or raw-TCP connection and no physical print completed;
- external Wi-Fi/hotspot: the plugin submitted the job and the page printed.

Treat cellular-only printing as client-dependent and unsupported unless it is
validated with the exact Android build and print service. Do not broaden the
firewall when packet capture shows no attempted print connection.

## Policy limitations

- iptables sees source IPs, not Tailscale user identities. Enforce identities with Grants.
- The granular service policy is IPv4. Where `ip6tables` is available, the installed IPv6 guard intentionally drops new Tailscale IPv6 input/forward traffic. If `ip6tables` is unavailable, the scripts warn and IPv6 must be independently verified disabled; fail-closed IPv6 enforcement is not claimed in that state. Do not relax the guard until an equivalent granular IPv6 policy is tested.
- `EDGE_ALLOWED_LAN_HOSTS` accepts IPv4 addresses/CIDRs, not hostnames, and combined with each listed port is a Cartesian product. Create separate chains if hosts need different service sets.
- Printer HTTP, SNMPv1/v2, IPP, and raw TCP are not encrypted on the LAN segment. Tailscale protects the remote path only as far as the subnet router; keep the printer policy source-restricted and never expose these ports to the WAN.
- Exit-node mode permits all protocols to the WAN interface; Tailscale Grants must restrict who may use `autogroup:internet`.
- REDIRECT of classic DNS port 53 requires dnsmasq to include `tailscale0`; it does not block encrypted DNS protocols.
- Optional `EDGE_ENFORCE_LAN_DNS=1` adds a separate managed `nat/EDGE_LAN_DNS_PREROUTING` chain on `EDGE_LAN_IF`. Traffic already addressed to the router's own DNS endpoint is returned unchanged; other TCP/UDP port-53 traffic is redirected to the router resolver.
- LAN DNS enforcement is intentionally limited to classic TCP/UDP 53. It does not claim control over DoH/HTTPS, DoT/853, DoQ/QUIC, VPN-carried DNS, or application-specific encrypted resolver transports.
- The feature is opt-in. Setting `EDGE_ENFORCE_LAN_DNS=0` and reapplying the managed firewall removes the LAN parent jump while keeping the managed chain empty for deterministic cleanup.
- With Tailscale netfilter ownership disabled, the parent `nat/PREROUTING` path should contain the single project-owned `$EDGE_TS_IF -> EDGE_TS_PREROUTING` jump rather than parallel direct NAT rules for the same interface. The health check treats exact-interface direct NAT rules outside the managed chain as runtime drift.
- Firmware-executed JFFS hooks relevant to this deployment (`firewall-start`, `services-start`, `wan-event`, and any residual `nat-start`) must not be symlinks or group/world writable. The health check reports these states as failures.

## Manual audit

The following commands are read-only and can be used to inspect the current policy without rebuilding it:

```sh
iptables-save | grep -E 'EDGE_TS_|tailscale0'
iptables -nvL EDGE_TS_INPUT --line-numbers
iptables -nvL EDGE_TS_FORWARD --line-numbers
iptables -t nat -nvL EDGE_TS_PREROUTING --line-numbers
ip6tables -nvL EDGE_TS6_INPUT --line-numbers
ip6tables -nvL EDGE_TS6_FORWARD --line-numbers
```

To verify idempotency during a planned deployment or maintenance window, re-run `/jffs/scripts/firewall-start` and confirm that each project-owned parent jump remains singular. The unchanged-state observation is now complete, but re-apply remains a deliberate maintenance action and should not be performed merely to satisfy documentation.
