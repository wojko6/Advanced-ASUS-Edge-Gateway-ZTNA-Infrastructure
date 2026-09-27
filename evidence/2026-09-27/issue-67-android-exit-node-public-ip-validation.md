# Issue #67 — Android exit-node public-IP validation after reboot

Date: 2026-09-27  
Reference router: ASUS TUF-AX5400  
Reference firmware: GNUton / Asuswrt-Merlin `3004.388.11_1-gnuton1_tuf`

## Purpose

Validate Android client egress behavior after reboot by comparing the observed public IPv4 with the ASUS Tailscale exit node enabled and disabled.

This document intentionally sanitizes all public IP addresses, Tailscale addresses, node names and account identifiers.

## Test conditions

- Android client on mobile data with Wi-Fi disabled.
- Tailscale connected.
- ASUS selected as the exit node for the enabled measurement.
- Same browser endpoint used for both measurements: `https://api.ipify.org`.
- Exit-node use then disabled for the comparison measurement.

## Results

| State | Observed public IPv4 | Result |
|---|---|---|
| ASUS exit node enabled | `HOME_WAN_IP` | public IPv4 matched the home/router egress path |
| ASUS exit node disabled | `MOBILE_IP` | public IPv4 changed to the mobile-provider egress path |

The two observed public IPv4 values were different and changed consistently with the exit-node state.

Because the comparison endpoint was reached by hostname over HTTPS in both states, basic DNS resolution and HTTPS connectivity were also confirmed during the measurement.

## Post-test router validation

The router was checked after the Android comparison without any repair step.

Observed state:

- router uptime approximately 30 minutes;
- `tailscaled` running;
- dnsmasq running;
- Unbound running;
- Unbound listening on `127.0.0.1:53535` over TCP and UDP;
- project healthcheck completed successfully;
- healthcheck summary: `0 failure(s), 0 warning(s)`;
- healthcheck return code: `0`.

The healthcheck also confirmed:

- Tailscale connected and `tailscale0` present;
- Tailscale netfilter management disabled as designed;
- exit-node WAN interface resolved;
- IPv4 forwarding enabled;
- project exit-node forwarding rule present;
- platform WAN NAT present;
- DNS enforcement paths healthy;
- project firewall chains healthy;
- Unbound control interface reachable;
- DNSSEC validation healthy;
- syslog-ng running.

## Acceptance

Issue #67 acceptance criteria:

- [x] Exit-node state verified before measurement.
- [x] Public IPv4 changed consistently with exit-node enable/disable state.
- [x] Basic DNS and HTTPS continued to work.
- [x] No router health-check regression after the test.
- [x] Only sanitized evidence published.

Result: **PASS**.

This validates observed Android client egress behavior after reboot. It does not replace the separately completed router-side packet-correlation evidence.
