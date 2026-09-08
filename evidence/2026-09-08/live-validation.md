# Live validation report

## Test context

| Field | Value |
|---|---|
| Date | 2026-09-08 |
| Router model | ASUS TUF-AX5400 |
| Firmware | ASUSWRT-Merlin 3004.388.9_2-gnuton1 |
| Router Tailscale | 1.102.3 |
| Remote client | Android / Tailscale beta |
| Configuration revision | 4b9c196266921c67ca1d8a701831176bcc4f0442 |
| Validation stage | Remote-client DNS and final infrastructure validation |

## Observed validation

| ID | Check | Expected | Observed | Verdict |
|---|---|---|---|---|
| HC-01 | Project healthcheck | 0 failures, 0 warnings | 34 OK, 0 WARN, 0 FAIL; exit status 0 | PASS |
| DNS-01 | dnsmasq Tailscale listener | DNS service available to Tailscale clients | dnsmasq listening on the router Tailscale interface on TCP/UDP port 53 | PASS |
| DNS-02 | dnsmasq upstream | Queries forwarded to local Unbound | Active dnsmasq configuration uses `server=127.0.0.1#53535` with `no-resolv` | PASS |
| DNS-03 | Unbound recursive resolver | Local resolver operational | Unbound listening on loopback port 53535 and responding successfully | PASS |
| DNS-04 | DNSSEC validation | AD flag present | Healthcheck and direct validation confirmed AD flag | PASS |
| REMOTE-01 | Android over LTE/5G with Tailscale DNS enabled | Public Internet remains usable | Public website loaded successfully with Wi-Fi disabled and Tailscale DNS enabled | PASS |
| REMOTE-02 | Remote DNS transport | DNS queries traverse the Tailscale tunnel to the router | Packet capture on `tailscale0` observed remote-client DNS queries and router responses on port 53 | PASS |
| REMOTE-03 | Normal DNS resolution | Non-blocked domains resolve normally | Multiple public service domains returned valid DNS responses | PASS |
| BLOCK-01 | Diversion blocking over Tailscale | Blocked domain rejected by router DNS | Test advertising/tracking domain returned NXDOMAIN over the remote Tailscale DNS path | PASS |
| BLOCK-02 | Android browser blocking result | Blocked domain cannot resolve | Browser reported that the DNS address for the test domain could not be found | PASS |
| WIFI-01 | Home Wi-Fi with Tailscale DNS enabled | Internet and DNS remain functional | Public website loaded successfully with Tailscale and Tailscale DNS enabled | PASS |
| WIFI-02 | Diversion blocking on Wi-Fi | Test domain remains blocked | The same test domain failed DNS resolution on the home Wi-Fi path | PASS |

## Verified DNS path

The remote-client test demonstrated the following functional path:

`Android remote client -> Tailscale tunnel -> router dnsmasq/Diversion -> Unbound on loopback:53535 -> recursive DNS`

The packet capture used for live verification is intentionally not included in
the repository because it contained client and router addressing information.

## Android client note

The previously observed loss of Internet connectivity when Tailscale DNS was
enabled on the Android stable client was not reproduced with the beta client
used for this validation.

This report records only the observed beta-client behavior and does not claim
that the issue is fixed in a stable Android release.

## Evidence references

- `environment.md`
- `healthcheck.md`
- `firewall-counters.md`
- `dns-validation.md`

## Scope

The LTE/5G test represents an actual remote-client validation with Wi-Fi
disabled. The home Wi-Fi test was performed separately with Tailscale DNS
enabled.

This report does not claim exhaustive validation of every remote-client
platform, identity policy, exit-node scenario or network environment.

## Publication review

- [x] No credentials, keys or tokens included.
- [x] No public IP addresses included.
- [x] No Tailscale node addresses included.
- [x] No identifying hostnames or usernames included.
- [x] Raw packet capture intentionally excluded.
- [x] Every PASS above represents an observed result.
- [x] Sanitized supporting evidence is included in this directory.
