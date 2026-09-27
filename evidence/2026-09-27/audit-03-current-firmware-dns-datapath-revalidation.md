# AUDIT-03 current-firmware revalidation — Fedora classic DNS datapath

**Date:** 2026-09-27  
**Reference platform:** ASUS TUF-AX5400 / GNUton `3004.388.11_1-gnuton1_tuf`  
**Scope:** Classic IPv4 DNS over UDP/TCP port 53 from a Fedora Tailscale exit-node client  
**Tracking:** #64  
**Result:** LIVE REVALIDATED on the current reference firmware

## Claim boundary

This artifact refreshes the Fedora portion of the earlier AUDIT-03 classic-DNS validation on the current GNUton reference firmware and the post-Unbound-1.26.1 resolver baseline.

The validation establishes, for the controlled Fedora client and classic DNS over UDP/TCP port 53:

- the ASUS router was selected as the Fedora Tailscale exit node;
- controlled DNS traffic addressed to an arbitrary external resolver reached the router on `tailscale0`;
- the project-owned `EDGE_TS_PREROUTING` UDP/53 and TCP/53 REDIRECT rules intercepted the traffic;
- dnsmasq forwarded the intercepted traffic to local Unbound on `127.0.0.1:53535`;
- both UDP and TCP test queries received valid DNS responses;
- temporary packet-capture instrumentation was removed after the test;
- the final project health check returned `0 failure(s), 0 warning(s)`.

This does not claim enforcement of DoH, DoT, DoQ, VPN-carried DNS, IPv6 resolver paths, or every application-specific resolver implementation.

Raw captures are not committed because they contain deployment-specific addresses and node identifiers. This document uses sanitized role labels only.

## Pre-test baseline

The router health check was clean before the controlled test:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

The active DNS path was:

```text
dnsmasq :53
  -> server=127.0.0.1#53535
  -> Unbound 1.26.1
```

dnsmasq was listening on the router LAN and Tailscale addresses over both TCP/53 and UDP/53. Unbound was listening on `127.0.0.1:53535` over TCP and UDP and was running with:

```text
unbound -c /opt/var/lib/unbound/unbound.conf
Version 1.26.1
```

The managed Tailscale DNS interception chain contained:

```text
-A EDGE_TS_PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 53
-A EDGE_TS_PREROUTING -p tcp --dport 53 -j REDIRECT --to-ports 53
```

## Controlled Fedora test

The Fedora client selected the ASUS router as its Tailscale exit node before the accepted test window.

Two unique classic-DNS queries were generated:

```text
UDP/53: dns64udp-20260927.example.com
TCP/53: dns64tcp-20260927.example.com
```

Both were intentionally addressed to an external resolver IP so the interception path could be observed.

## Tailscale ingress correlation

A router-side capture on `tailscale0` observed the Fedora client sending:

```text
[FEDORA_TS_IP] -> [EXTERNAL_DNS_IP]:53/UDP
A? dns64udp-20260927.example.com

[FEDORA_TS_IP] -> [EXTERNAL_DNS_IP]:53/TCP
A? dns64tcp-20260927.example.com
```

Responses for both controlled queries were observed on the same Tailscale-side sessions.

## Managed REDIRECT counters

Immediately before the accepted controlled packet-correlation window, the managed counters were:

```text
UDP/53 REDIRECT: 765 packets
TCP/53 REDIRECT: 22 packets
```

After exactly one controlled UDP query and one controlled TCP query, the counters were:

```text
UDP/53 REDIRECT: 766 packets
TCP/53 REDIRECT: 23 packets
```

Therefore the controlled deltas were:

```text
UDP/53: +1
TCP/53: +1
```

The exact deltas match the two intentionally generated test queries.

## dnsmasq -> Unbound correlation

A simultaneous loopback capture on `127.0.0.1:53535` observed the corresponding dnsmasq-to-Unbound traffic.

For the controlled UDP query, the Tailscale-side DNS payload length was 70 bytes and the loopback request to Unbound was also 70 bytes. The corresponding response lengths were 120 bytes on both legs.

For the controlled TCP query, the Tailscale-side DNS payload was 72 bytes and the loopback TCP payload to Unbound was also 72 bytes. The corresponding response payload was 122 bytes on both legs.

Because the packet decoder does not automatically decode DNS names on the non-standard Unbound port 53535, the correlation is based on the synchronized controlled window, protocol, direction, and matching request/response payload lengths.

Together with the exact +1 UDP and +1 TCP managed REDIRECT deltas, this establishes the tested path:

```text
Fedora
  -> Tailscale exit-node path
  -> tailscale0
  -> EDGE_TS_PREROUTING
  -> REDIRECT :53
  -> dnsmasq :53
  -> Unbound 127.0.0.1:53535
```

## Cleanup and final health

The temporary `tcpdump` processes were terminated and their temporary files removed.

Cleanup verification:

```text
NO_TCPDUMP_PROCESSES
```

The final project health check reported:

```text
Summary: 0 failure(s), 0 warning(s)
```

Relevant checks included healthy Tailscale connectivity, managed filter/NAT chains, exit-node runtime dependencies, LAN DNS/DoT policy, Unbound availability, Unbound control reachability, DNSSEC AD validation, and syslog-ng.

## Result

Current-firmware Fedora classic-DNS revalidation:

- UDP/53 Tailscale ingress: **PASS**
- TCP/53 Tailscale ingress: **PASS**
- `EDGE_TS_PREROUTING` UDP REDIRECT: **PASS / exact +1**
- `EDGE_TS_PREROUTING` TCP REDIRECT: **PASS / exact +1**
- dnsmasq -> Unbound UDP forwarding: **PASS**
- dnsmasq -> Unbound TCP forwarding: **PASS**
- temporary instrumentation cleanup: **PASS**
- final project health check: **PASS / 0 failures, 0 warnings**

Issue #64 is therefore complete for its stated current-firmware classic IPv4 UDP/TCP port-53 scope.

## Remaining limits

- This revalidation used Fedora; it does not replace the separate Android-specific acceptance item tracked elsewhere.
- DoH/HTTPS, DoT/TCP 853, DoQ/QUIC, VPN-carried DNS, IPv6 resolver paths and application-specific encrypted DNS are outside this claim.
- A material firmware, firewall, dnsmasq, Unbound or Tailscale architecture change should trigger revalidation.
