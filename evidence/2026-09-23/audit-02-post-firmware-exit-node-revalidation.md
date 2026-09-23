# AUDIT-02 post-firmware live revalidation — exit-node NAT ownership

**Date:** 2026-09-23  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton `3004.388.11_1-gnuton1_tuf`  
**Scope:** controlled IPv4 Tailscale exit-node datapath after the firmware upgrade  
**Result:** LIVE REVALIDATED — project-owned forwarding plus platform-owned WAN NAT confirmed on the current firmware

## Claim boundary

This artifact records a sanitized summary of the current-firmware revalidation. Raw packet captures and deployment-specific Tailscale/WAN addresses are intentionally not published.

The validation establishes, for the tested IPv4 ICMP flow, that:

- IPv4 forwarding is enabled on the router;
- the project-owned `EDGE_TS_FORWARD` policy permits exit-node traffic toward the active WAN interface;
- Asuswrt-Merlin provides the effective WAN `POSTROUTING` `MASQUERADE`;
- the platform parent `FORWARD` chain provides the established/related return path before later WAN drops;
- the same controlled five-packet ICMP flow was observed on `tailscale0` before NAT and on `ppp0` after source translation;
- replies for the same identifier and sequence numbers were observed in the reverse direction on both interfaces;
- the final production health check remained clean.

This does not prove every protocol, every exit-node client, every WAN transport, or future firmware behavior. Revalidate after material firmware, firewall, routing, or Tailscale architecture changes.

## Preflight state

The live router reported:

- active gateway interface: `ppp0`;
- underlying WAN interface: `vlan35`;
- `net.ipv4.ip_forward = 1`;
- the first parent `FORWARD` rule jumps traffic arriving on `tailscale0` to `EDGE_TS_FORWARD`;
- `EDGE_TS_FORWARD` contains the current exit-node allow rule toward `ppp0`;
- the parent `FORWARD` chain contains a `RELATED,ESTABLISHED` accept path before the later WAN drop rules;
- the platform NAT `POSTROUTING` chain contains a `MASQUERADE` rule for `ppp0`;
- the project health check returned `0 failure(s), 0 warning(s)`.

## Client and controlled flow

The Fedora client showed the ASUS router as the active Tailscale exit node.

A controlled ICMP sequence then sent exactly five echo requests to `1.1.1.1` using fixed ICMP identifier `4244` and sequence numbers `1..5`.

Client result:

```text
5 packets transmitted, 5 received, 0% packet loss
```

## Packet-level correlation

### Pre-NAT view on tailscale0

A router-side capture filtered to the controlled destination and ICMP identifier observed:

```text
[TAILSCALE_CLIENT_IP_REDACTED] -> 1.1.1.1
ICMP echo request, id 4244, seq 1..5

1.1.1.1 -> [TAILSCALE_CLIENT_IP_REDACTED]
ICMP echo reply, id 4244, seq 1..5
```

Capture summary:

```text
10 packets captured
10 packets received by filter
0 packets dropped by kernel
```

### Post-NAT view on ppp0

A simultaneous capture on the active WAN interface observed the same identifier and sequence numbers after source translation:

```text
[WAN_PUBLIC_IP_REDACTED] -> 1.1.1.1
ICMP echo request, id 4244, seq 1..5

1.1.1.1 -> [WAN_PUBLIC_IP_REDACTED]
ICMP echo reply, id 4244, seq 1..5
```

Capture summary:

```text
10 packets captured
10 packets received by filter
0 packets dropped by kernel
```

The matching ICMP identifier, sequence numbers and near-identical timestamps correlate the pre-NAT and post-NAT observations of the same flow and demonstrate source translation on egress through `ppp0`.

## Counter observations

After the controlled flow, both the project exit-node forwarding rule and the platform `ppp0` `MASQUERADE` counters were higher than in the earlier preflight snapshot.

Those aggregate counter deltas are treated as supporting observations only. Other router traffic was present during the wider interval, so the complete counter increase is not attributed solely to the five controlled ICMP packets. The packet-level fixed-flow correlation is the primary evidence.

## Final production health

After the packet test, the live health check again reported:

```text
Summary: 0 failure(s), 0 warning(s)
```

Relevant checks explicitly passed for:

- exit-node WAN interface resolution to `ppp0`;
- IPv4 forwarding;
- the project exit-node forwarding rule;
- platform WAN NAT;
- the established/related return path;
- Tailscale connectivity and the managed firewall chains.

No temporary firewall instrumentation was required for this revalidation.

## Conclusion

AUDIT-02 remains closed and is now **post-firmware live revalidated** on GNUton `3004.388.11_1-gnuton1_tuf` for the tested IPv4 exit-node path.

The validated architecture remains:

```text
Tailscale client
    |
    v
tailscale0
    |
    v
project-owned EDGE_TS_FORWARD
    |
    v
Asuswrt-Merlin platform POSTROUTING/MASQUERADE
    |
    v
ppp0 / WAN
```

NAT ownership remains **platform-owned**, while Tailscale ingress/forwarding authorization remains **project-owned**.
