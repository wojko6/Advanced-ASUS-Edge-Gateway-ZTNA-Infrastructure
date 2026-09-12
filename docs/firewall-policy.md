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
- The granular service policy is IPv4. The installed IPv6 guard intentionally drops new Tailscale IPv6 input/forward traffic; do not remove it until an equivalent policy is tested.
- `EDGE_ALLOWED_LAN_HOSTS` accepts IPv4 addresses/CIDRs, not hostnames, and combined with each listed port is a Cartesian product. Create separate chains if hosts need different service sets.
- Printer HTTP, SNMPv1/v2, IPP, and raw TCP are not encrypted on the LAN segment. Tailscale protects the remote path only as far as the subnet router; keep the printer policy source-restricted and never expose these ports to the WAN.
- Exit-node mode permits all protocols to the WAN interface; Tailscale Grants must restrict who may use `autogroup:internet`.
- REDIRECT of classic DNS port 53 requires dnsmasq to include `tailscale0`; it does not block encrypted DNS protocols.

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

To verify idempotency during a planned deployment or maintenance window, re-run `/jffs/scripts/firewall-start` and confirm that each project-owned parent jump remains singular. **Do not perform that re-apply merely for audit purposes during the reference router's unchanged-state observation window ending 2026-09-25.** During the active stability gate, use the read-only ruleset/counter inspection above instead. If recovery from an active fault or security incident requires firewall re-application, record the intervention and restart the stability baseline after the router returns to a known-good state.
