# AUDIT-02 live validation — exit-node NAT ownership

**Date:** 2026-09-22  
**Scope:** IPv4 Tailscale exit-node datapath on the reference ASUS TUF-AX5400 / Asuswrt-Merlin deployment  
**Result:** LIVE VALIDATED — platform-owned WAN NAT dependency confirmed

## Claim boundary

This artifact records a sanitized summary of the live validation. Raw packet-capture output is intentionally not committed because it contained deployment-specific Tailscale and WAN addresses.

The validation establishes that:

- the project-owned `EDGE_TS_FORWARD` policy admits authorized Tailscale exit-node traffic toward the active WAN interface;
- IPv4 forwarding is enabled;
- Asuswrt-Merlin provides the effective WAN `POSTROUTING` `MASQUERADE` rule;
- the platform parent `FORWARD` chain provides the established/related return path;
- the same controlled ICMP flow was observed before NAT on `tailscale0` and after NAT on the WAN interface.

It does not claim that future firmware versions will preserve the same platform rules. The runtime dependency should therefore remain health-checked.

## Read-only observations

- `net.ipv4.ip_forward = 1`.
- The first parent `FORWARD` rule sends traffic arriving on `tailscale0` to `EDGE_TS_FORWARD`.
- `EDGE_TS_FORWARD` contains the exit-node allow rule for the active WAN interface.
- During controlled client traffic, the WAN-forward rule counter increased.
- The platform `nat/POSTROUTING` chain contains a WAN-interface `MASQUERADE` rule broad enough to translate forwarded Tailscale client traffic.
- During the same controlled client activity, the platform WAN `MASQUERADE` counter increased.
- The parent `FORWARD` chain contains an `ACCEPT` rule for `RELATED,ESTABLISHED` traffic before its later WAN/terminal drop rules.

## Packet-level correlation

A controlled five-packet ICMP sequence used a fixed ICMP identifier.

On `tailscale0`, the requests were observed as:

```text
[TAILSCALE_CLIENT_IP] -> 1.1.1.1
ICMP id 4243, seq 1..5
```

On the WAN interface, the same flow was observed as:

```text
[WAN_IP_REDACTED] -> 1.1.1.1
ICMP id 4243, seq 1..5
```

Replies for the same identifier and sequence numbers were observed in the reverse direction on both interfaces.

The matching identifier, sequence numbers and timestamps correlate the pre-NAT and post-NAT views of the same flow and demonstrate source translation on egress.

## Conclusion

AUDIT-02 is closed for the validated reference state.

The architecture is:

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
WAN
```

NAT ownership is therefore **platform-owned**, while Tailscale ingress/forwarding authorization remains **project-owned**.

A second project-owned `MASQUERADE` rule is not required for the validated reference state and should not be added merely to duplicate the firmware NAT policy.

## Remaining operational requirement

Because exit-node availability now has an explicit dependency on the Asuswrt-Merlin WAN NAT and return-path policy, the project health check should verify the prerequisites when `EDGE_ENABLE_EXIT_NODE=1`:

1. IPv4 forwarding enabled;
2. project exit-node WAN forwarding rule present;
3. effective WAN `MASQUERADE` or `SNAT` rule present;
4. parent `FORWARD` established/related return path present.

These checks validate the runtime contract; they do not replace packet-level live validation after a material firmware/firewall architecture change.
