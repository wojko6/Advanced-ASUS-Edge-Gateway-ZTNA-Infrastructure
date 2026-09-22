# AUDIT-03 live validation — Fedora/Android classic DNS datapath

**Date:** 2026-09-22  
**Scope:** Classic IPv4 DNS over UDP/TCP port 53 from Tailscale exit-node clients on Fedora and Android  
**Result:** LIVE VALIDATED — router DNS interception and dnsmasq -> Unbound datapath confirmed

## Claim boundary

This artifact records a sanitized summary of controlled live tests on the reference deployment.

The validation establishes, for classic DNS over UDP/TCP port 53:

- a Fedora exit-node client can send a query to an arbitrary external resolver address and the traffic arrives on router `tailscale0`;
- the project `EDGE_TS_PREROUTING` DNS `REDIRECT` rules intercept UDP/53 and TCP/53;
- dnsmasq forwards the intercepted query to local Unbound on `127.0.0.1:53535`;
- Unbound performs recursive resolution rather than the client reaching the requested external recursive resolver directly;
- an Android client on cellular data, with Wi-Fi disabled and the ASUS selected as Tailscale exit node, follows the same classic DNS interception path for UDP/53 and TCP/53.

This does **not** prove interception of encrypted DNS such as DoH or DoT, application-specific resolver transports, QUIC-based encrypted DNS, or every operating-system/application resolver path. Those remain outside the classic-port-53 claim.

Raw captures are not committed because they contained deployment-specific Tailscale and WAN addresses. All addresses below are sanitized role labels.

## Test conditions

- Reference router: ASUS TUF-AX5400 / Asuswrt-Merlin.
- Tailscale: active, router selected as exit node.
- Router DNS interception: project-owned `EDGE_TS_PREROUTING`.
- dnsmasq: router-local port 53 listener.
- Unbound: `127.0.0.1:53535`.
- Fedora endpoint filtering/proxy layer: disabled for the controlled baseline.
- Android transport: cellular LTE/5G, Wi-Fi disabled.
- Test destination: `8.8.8.8:53` used intentionally as an external classic-DNS target to test transparent interception.
- Unique `example.com` labels were used to avoid ambiguity and cache confusion.

## Fedora UDP/53

Controlled query:

```text
audit03-20260922-01.example.com
```

Observed:

1. `tailscale0` saw `[FEDORA_TS_IP] -> 8.8.8.8:53/UDP`.
2. The UDP/53 counter in `EDGE_TS_PREROUTING` increased by exactly one for the controlled query.
3. The router loopback showed dnsmasq forwarding to `127.0.0.1:53535/UDP`.
4. WAN capture showed recursive DNS activity toward authoritative infrastructure for the queried zone rather than a direct forwarded query to `8.8.8.8`.
5. The client received a valid DNS response.

Conclusion: Fedora classic UDP/53 was transparently intercepted and resolved through dnsmasq -> Unbound.

## Fedora TCP/53

Controlled query:

```text
audit03-tcp2-20260922-01.example.com
```

Observed:

1. `tailscale0` showed the TCP/53 connection and the unique query sent to `8.8.8.8:53`.
2. The TCP/53 `EDGE_TS_PREROUTING` REDIRECT counter increased by one in the controlled test.
3. Within milliseconds, loopback capture showed a TCP connection from dnsmasq to `127.0.0.1:53535` carrying the corresponding DNS payload length and response.
4. The client received the answer over its original TCP/53 session.

Conclusion: Fedora classic TCP/53 was transparently intercepted and forwarded to Unbound over TCP.

## Android UDP/53

Controlled Android queries used unique names including:

```text
audit03-android-20260922-01.example.com
audit03-poco-20260922.example.com
```

Observed in controlled runs under the same router/client state:

1. Router `tailscale0` captured the Android Tailscale client sending classic UDP/53 to `8.8.8.8`.
2. A repeated unique Android query was visible on router loopback as dnsmasq -> `127.0.0.1:53535/UDP`, with the matching query name visible in the payload.
3. The Android client received a valid DNS response while on cellular data through the selected exit node.

The ingress and loopback legs were captured in separate repeated controlled runs rather than one simultaneous dual-interface capture. Both observations used the same unchanged DNS/Tailscale policy state.

Conclusion: Android classic UDP/53 follows the intended Tailscale -> REDIRECT -> dnsmasq -> Unbound path on the validated reference state.

## Android TCP/53

Controlled Android queries used unique names including:

```text
audit03-poco-tcp2-20260922.example.com
audit03-poco-tcp3-20260922.example.com
```

Observed in controlled runs under the same router/client state:

1. Router `tailscale0` captured the Android Tailscale client establishing TCP/53 to `8.8.8.8` and carrying the unique DNS query.
2. A repeated unique Android TCP query was visible on router loopback as dnsmasq -> `127.0.0.1:53535/TCP`.
3. Unbound returned the DNS response on the same loopback TCP connection and the Android client received a valid response.

As with the Android UDP test, the ingress and loopback legs were captured in separate immediately repeated controlled runs, not a single synchronized dual-interface capture.

Conclusion: Android classic TCP/53 follows the intended Tailscale -> REDIRECT -> dnsmasq -> Unbound path on the validated reference state.

## Validated classic-DNS architecture

```text
Fedora / Android client
        |
        | Tailscale exit-node traffic
        v
router tailscale0
        |
        | EDGE_TS_PREROUTING REDIRECT
        v
router-local dnsmasq :53
        |
        v
Unbound 127.0.0.1:53535
        |
        v
recursive / authoritative DNS path
```

## Result

For the reference state tested on 2026-09-22:

- Fedora UDP/53: PASS / LIVE VALIDATED
- Fedora TCP/53: PASS / LIVE VALIDATED
- Android UDP/53: PASS / LIVE VALIDATED
- Android TCP/53: PASS / LIVE VALIDATED
- dnsmasq -> Unbound loopback forwarding: PASS / LIVE VALIDATED

AUDIT-03 is therefore closed for the documented **classic DNS TCP/UDP port 53** scope.

## Remaining limitations

- DoH/DoT and other encrypted DNS transports are not covered by the port-53 REDIRECT and are not claimed as enforced by this validation.
- Application-specific resolver stacks may use encrypted transports and require separate testing.
- The Android tests validate controlled classic-DNS traffic generated from the device; they are not proof that every Android application uses classic DNS.
- A material firmware, firewall, dnsmasq, Unbound, or Tailscale architecture change should trigger revalidation.
