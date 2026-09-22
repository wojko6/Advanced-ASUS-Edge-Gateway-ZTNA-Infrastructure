# Production DNS-over-TLS (DoT/853) blocking live validation — 2026-09-22

**Status:** PASS  
**Evidence class:** Router live + LAN client / controlled production deployment  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin  
**Client:** Fedora workstation on the reference LAN

## Purpose

Validate the production `EDGE_BLOCK_LAN_DOT` implementation added through PR #58 and confirm that direct IPv4 DNS-over-TLS on TCP/853 from the LAN is rejected by the managed project firewall policy.

## Pre-deployment state

The merged repository state was synchronized locally before deployment.

The new production scripts were staged on the router and matched the repository copies:

```text
firewall-start
3b51ab285605d379c28552853331921f4f2afa58562e97772866ec243ff60667

healthcheck.sh
e1b9436a8aed5e7f16e725c0769e3f6275198ca1e6f7ed1d8d51ef504304045d
```

Both staged scripts passed shell syntax validation.

The new health check was also executed against the pre-change router state and reported `0 failure(s), 0 warning(s)`, including confirmation that LAN DoT blocking was disabled without an active jump.

No temporary `EDGE_LAN_DOT_TEST` chain remained from the earlier prototype.

## Controlled deployment

The existing firewall script, health-check script, and router-local project configuration were backed up before replacement.

The new scripts were installed and the reference deployment was explicitly configured with:

```text
EDGE_BLOCK_LAN_DOT="1"
```

The managed firewall applied successfully.

The production `FORWARD` parent order began with:

```text
1  tailscale0 -> EDGE_TS_FORWARD
2  br0        -> EDGE_LAN_DOT_FORWARD
```

The managed production chain contained:

```text
REJECT tcp dpt:853 reject-with tcp-reset
```

## Live health check

The production health check reported explicit PASS results for:

- a single LAN DoT FORWARD jump;
- evaluation of the LAN DoT policy before platform FORWARD rules;
- the exact TCP/853 reject policy;
- the existing LAN classic-DNS enforcement;
- all previously established Tailscale, exit-node, DNSSEC, IPv6 guard, and runtime-drift checks.

Final result:

```text
Summary: 0 failure(s), 0 warning(s)
LIVE_HEALTHCHECK_RC=0
```

## Functional LAN validation

The Fedora client was verified to route the external resolver target through the normal LAN gateway:

```text
8.8.8.8 via 192.168.50.1 dev <LAN-Wi-Fi-interface> src <LAN-client-address>
```

A direct TLS connection to the Google Public DNS DoT endpoint was then attempted:

```text
openssl s_client -connect 8.8.8.8:853 -servername dns.google -brief
```

The production result was:

```text
Connection refused
connect:errno=111
```

The managed production chain immediately showed:

```text
1 packet / 60 bytes
REJECT tcp dpt:853 reject-with tcp-reset
```

This ties the client-side failure to the deployed `EDGE_LAN_DOT_FORWARD` policy.

A post-test health check remained:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

## Result

**PASS.** Production direct IPv4 DoT blocking on TCP/853 is deployed and live validated on the reference router.

## Claim boundary

This validation covers direct IPv4 TCP/853 only. It does not establish control over DoH/HTTPS, DoQ/QUIC, VPN-carried DNS, IPv6 resolver paths, or application-specific encrypted resolver transports.

It also does not imply that later repository revisions are automatically deployed.

Deployment-specific client addresses, credentials, private backup file names, and unrelated raw router output are intentionally omitted.
