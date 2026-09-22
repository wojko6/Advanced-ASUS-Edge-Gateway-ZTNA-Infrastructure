# Production LAN classic-DNS enforcement live validation — 2026-09-22

**Status:** PASS  
**Evidence class:** Router live + LAN client / controlled production deployment  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin  
**Client:** Fedora workstation on the reference LAN

## Purpose

Validate the production `EDGE_ENFORCE_LAN_DNS` implementation added through PR #57 and confirm that classic IPv4 DNS traffic from the LAN cannot bypass the router by explicitly targeting an external TCP/UDP port-53 resolver.

## Repository and deployed revisions

The local repository was synchronized to the merged PR #57 state before deployment.

The deployed production scripts matched the staged/tested copies:

```text
firewall-start
ae7f1e5794cbbcf6e1e9fc828bba1cdabe43a021ca518d6466cc44bec5997d6a

healthcheck.sh
ba78afe34ba27b582d6bbeb399d97e89e51f6199d11220805bbe2a71d791a9a1
```

Before activation, both staged scripts passed `sh -n`, and the new health check executed successfully against the then-current state with LAN DNS enforcement still disabled.

## Controlled deployment

The previous deployed firewall script, health-check script, and router-local project configuration were backed up before replacement.

The new scripts were installed and the reference deployment was explicitly configured with:

```text
EDGE_ENFORCE_LAN_DNS=1
```

The managed firewall was applied once.

The resulting production NAT policy contained:

```text
-A PREROUTING -i br0 -j EDGE_LAN_DNS_PREROUTING
-A EDGE_LAN_DNS_PREROUTING -d 192.168.50.1/32 -p udp --dport 53 -j RETURN
-A EDGE_LAN_DNS_PREROUTING -d 192.168.50.1/32 -p tcp --dport 53 -j RETURN
-A EDGE_LAN_DNS_PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 53
-A EDGE_LAN_DNS_PREROUTING -p tcp --dport 53 -j REDIRECT --to-ports 53
```

## Live health check

The production health check reported explicit PASS results for:

- dnsmasq listening on the configured LAN interface;
- absence of direct LAN DNS NAT rules outside the managed chain;
- a single LAN DNS `PREROUTING` jump;
- the exact managed classic-DNS enforcement policy.

Final result:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

## Functional LAN validation

Fedora was verified to route the external resolver target through the normal LAN gateway rather than through Tailscale:

```text
8.8.8.8 via 192.168.50.1 dev <LAN-Wi-Fi-interface> src <LAN-client-address>
```

Controlled queries were then sent to `8.8.8.8:53` over both UDP and TCP.

The production managed-chain counters subsequently showed:

```text
router-return UDP/53: 71 packets / 4791 bytes
router-return TCP/53: 0 packets / 0 bytes
external UDP/53 REDIRECT: 6 packets / 480 bytes
external TCP/53 REDIRECT: 6 packets / 360 bytes
```

The external redirect counters demonstrate that both controlled classic-DNS transport variants were intercepted by the production LAN enforcement chain.

## Result

**PASS.** Production classic IPv4 LAN DNS enforcement is deployed and live validated on the reference router for TCP/UDP port 53.

## Claim boundary

This validation does not establish control over DoH/HTTPS, DoT/853, DoQ/QUIC, VPN-carried DNS, IPv6 resolver paths, or application-specific encrypted resolver transports.

It also does not imply that later repository revisions are automatically deployed.

Deployment-specific client addresses, credentials, private backup paths, and unrelated raw router output are intentionally omitted.
