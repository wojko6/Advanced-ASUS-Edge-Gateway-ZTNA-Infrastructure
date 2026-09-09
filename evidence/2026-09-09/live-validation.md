# Live validation report

## Test context

| Field | Value |
|---|---|
| Date (UTC) | 2026-09-09 |
| Router model | TUF-AX5400 |
| Firmware | 3.0.0.4 388.9 2-gnuton1 |
| Tailscale | 1.102.3 |
| Unbound | 1.24.2 |
| Deployed configuration revision | Not independently verified during this validation |
| Repository release baseline | d7de54b43b93f43adc48081182cd22246ed3ef27 (v2.1.2) |
| Repository HEAD under audit | c3286e1004561ed3a734f90325fffae2aa85c7a6 |
| Tester/source role | Local admin / Tailscale client / Android client |

## DNS bypass validation

| ID | Source role | Destination/service | Expected | Command or method | Observed | Verdict |
|---|---|---|---|---|---|---|
| DNS-BYPASS-01 | LAN client | Router DNS TCP/UDP 53 | Local resolver path used | dnsmasq query log and client lookup | Client queries were observed by dnsmasq and resolved through the local DNS path | PASS |
| DNS-BYPASS-02 | Android client | Google Private DNS / TCP 853 | Current baseline does not enforce DoT blocking | Android Private DNS set to `dns.google`; router-side traffic observation | DNS traffic used TCP 853 and bypassed local dnsmasq | PASS |
| DNS-BYPASS-03 | Android and Linux clients | External DoT / TCP 853 | Temporary enforcement rule should block DoT | Temporary IPv4 egress reject rule with counter verification | DoT stopped while the temporary rule was active and rule counters increased | PASS |
| DNS-BYPASS-04 | Brave Secure DNS client | Cloudflare encrypted DNS over 443 | Current baseline does not comprehensively block DoH | Brave Secure DNS enabled; dnsmasq and encrypted traffic observation | Target DNS query was absent from dnsmasq while encrypted traffic to Cloudflare over port 443 was observed | PASS |

## Security observations

- Plain DNS is intercepted and handled by the local resolver path.
- Android Private DNS using DNS-over-TLS can bypass the current baseline through TCP 853.
- A temporary IPv4 TCP 853 blocking rule successfully prevented the tested DoT path.
- Brave Secure DNS can bypass the local DNS resolver using encrypted traffic over port 443.
- The encrypted DNS payload was not decrypted; the observation demonstrates bypass of the local dnsmasq path, not inspection of DoH application data.
- Blocking UDP 443 alone is not sufficient to claim DoH prevention because TCP 443 fallback remains possible.
- Permanent DoT/DoQ enforcement is not part of the deployed baseline represented by this report.

## Follow-up

- Add optional IPv4 and IPv6 enforcement for DNS-over-TLS and DNS-over-QUIC on port 853 in a later release.
- Treat DoH over port 443 as best-effort unless endpoint controls, application policy, or TLS inspection are introduced.
- Do not claim comprehensive encrypted-DNS prevention from network-layer port filtering alone.

## Evidence links

- [Environment snapshot](environment.md)
- [Health check](healthcheck.md)
- [Firewall counters](firewall-counters.md)
- [Direct Unbound validation](dns-validation.md)
- [Snapshot checksums](SHA256SUMS)

## Publication review

- [x] No credentials, keys, tokens, node state, or router exports.
- [x] No public IP addresses or identifying hostnames.
- [x] Internal addresses are not published.
- [x] Every PASS represents an observed result.
- [x] Relevant sanitized router-side evidence is included.
