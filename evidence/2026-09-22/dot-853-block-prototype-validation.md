# DNS-over-TLS (DoT/853) blocking prototype validation — 2026-09-22

**Status:** PASS  
**Evidence class:** Router live + LAN client / temporary controlled policy  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin  
**Client:** Fedora workstation on the reference LAN

## Purpose

Determine whether direct DNS-over-TLS on TCP/853 can bypass the production classic-DNS port-53 enforcement and validate a reversible router-side blocking mechanism.

## Baseline

The Fedora client was on the normal LAN path through the ASUS gateway.

A direct TLS connection to the Google Public DNS DoT endpoint succeeded:

```text
Connecting to 8.8.8.8
CONNECTION ESTABLISHED
Protocol version: TLSv1.3
Peer certificate: CN=dns.google
Verification: OK
```

This demonstrated a working direct TCP/853 path outside the classic TCP/UDP 53 enforcement.

## Temporary block

A non-persistent `EDGE_LAN_DOT_TEST` filter chain was attached to `FORWARD` for `br0` with:

```text
-p tcp --dport 853 -j REJECT --reject-with tcp-reset
```

During the blocked phase the client TLS connection failed immediately with `Connection refused`.

A controlled retry was correlated with the router counter:

```text
1 packet / 60 bytes
REJECT tcp dpt:853 reject-with tcp-reset
```

This ties the observed client failure to the temporary router policy.

## Rollback

The temporary parent jump and test chain were removed.

The same direct TLS connection to `8.8.8.8:853` then succeeded again with TLS 1.3 and a verified `dns.google` certificate.

The test therefore produced an A/B/A sequence:

```text
A: direct DoT reachable
B: TCP/853 rejected by the temporary LAN policy
A: direct DoT reachable again after rollback
```

## Result

**PASS.** Direct IPv4 DoT over TCP/853 is a real bypass of classic port-53 enforcement on the tested LAN path, and a source-interface-scoped TCP-reset reject can block it reversibly.

## Claim boundary

This validation covers direct IPv4 TCP/853 only. It does not establish control over DoH/HTTPS, DoQ/QUIC, VPN-carried DNS, IPv6 resolver paths, or application-specific encrypted resolver transports.

The production repository implementation was subsequently deployed and live-validated as a separate controlled change. See `dot-853-block-production-validation.md`. This prototype artifact remains bounded to the temporary-chain A/B/A test described above.
