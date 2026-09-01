# Firewall policy

## Managed chains

The project owns three IPv4 chains and two fail-closed IPv6 guard chains:

- `filter/EDGE_TS_INPUT`: traffic from `tailscale0` to the router.
- `filter/EDGE_TS_FORWARD`: traffic from `tailscale0` through the router.
- `nat/EDGE_TS_PREROUTING`: DNS redirection before routing.
- `filter/EDGE_TS6_INPUT` and `filter/EDGE_TS6_FORWARD`: block new IPv6 traffic from `tailscale0` until an equivalent granular IPv6 policy exists.

It does not flush Merlin, Tailscale, or user-owned chains. Before attaching each managed chain, it deletes duplicate jumps and inserts exactly one interface-scoped jump.

During re-application, temporary interface-scoped drop rules keep the transition fail-closed while managed chains are rebuilt. They are removed only after the complete IPv4 and IPv6 policy succeeds. Apply from LAN because an error intentionally leaves these guards in place until firewall restart/recovery.

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
4. If exit-node mode is enabled, allow forwarding only to the detected/configured WAN interface.
5. Rate-limit security logging.
6. Drop all remaining forwarding from `tailscale0`.

## Policy limitations

- iptables sees source IPs, not Tailscale user identities. Enforce identities with Grants.
- The granular service policy is IPv4. The installed IPv6 guard intentionally drops new Tailscale IPv6 input/forward traffic; do not remove it until an equivalent policy is tested.
- `EDGE_ALLOWED_LAN_HOSTS` combined with each listed port is a Cartesian product. Create separate chains if hosts need different service sets.
- Exit-node mode permits all protocols to the WAN interface; Tailscale Grants must restrict who may use `autogroup:internet`.
- DNAT of port 53 does not block encrypted DNS protocols.

## Manual audit

```sh
iptables-save | grep -E 'EDGE_TS_|tailscale0'
iptables -nvL EDGE_TS_INPUT --line-numbers
iptables -nvL EDGE_TS_FORWARD --line-numbers
iptables -t nat -nvL EDGE_TS_PREROUTING --line-numbers
```

Re-run `/jffs/scripts/firewall-start` and confirm jump counts remain one.
