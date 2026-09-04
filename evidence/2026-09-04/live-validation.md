# Live validation report — 2026-09-04

## Test context

| Field | Value |
|---|---|
| Validation date | 2026-09-04 UTC |
| Evidence collected | 2026-09-04 09:29:25 UTC |
| Router model | TUF-AX5400 |
| Kernel | 4.1.52 |
| Router memory | 512188 kB |
| Tailscale | 1.102.3 |
| Router deployment revision | 8d7920b |
| Test source | Authorized Android Tailscale device, external Wi-Fi/hotspot, cellular data, and router loopback |

All Tailscale addresses, public endpoints, usernames, hostnames, printer serial
numbers, and real LAN addresses are omitted or represented by descriptive
placeholders.

## Startup and printer validation

| ID | Source | Destination or function | Expected | Command or method | Observed | Verdict |
|---|---|---|---|---|---|---|
| BOOT-01 | Router after reboot | Required USB-backed swap | Active before managed Tailscale startup | `/proc/swaps` and managed startup log | 2 GiB swap active; managed startup continued after Entware settled | PASS |
| BOOT-02 | Router after reboot | Tailscale daemon | Start and stabilize automatically | PID, Tailscale status, startup log and project health check | `tailscaled` stabilized on attempt 1; Tailscale connected; 0 failures and 0 warnings | PASS |
| FW-PRN-01 | Authorized Android Tailscale device | Configured printer HTTP, IPP/raw TCP and SNMP services | Only configured destination and ports allowed | Managed-chain counters and header-only packet capture | Printer SNMP requests and responses traversed `tailscale0` and the LAN bridge; printer-policy drops were absent | PASS |
| FW-PRN-02 | Authorized Android Tailscale device | Unlisted workstation TCP/1716 | Denied | Managed drop log | Attempts to an unrelated workstation service were denied by the final forward-chain policy | PASS |
| PRINT-01 | Android over external Wi-Fi/hotspot and Tailscale, no exit node | Source-scoped LAN printer | Submit and physically print one page | Samsung print service with the printer added by LAN address | Job submitted and the physical page printed | PASS |
| PRINT-02 | Android over cellular data and Tailscale, no exit node | Source-scoped LAN printer | No support claim; record actual client behavior | Samsung print service, managed counters and header-only capture | Bidirectional SNMP succeeded, but the client opened no IPP/raw-TCP print connection and no physical print completed | CLIENT LIMITATION |

The cellular result is not attributed to the firewall: no print connection was
attempted and no printer-policy drop occurred during the controlled capture.
The successful external-Wi-Fi test used the same Tailscale subnet route and
printer policy.

## Collected evidence

- [Environment snapshot](environment.md)
- [Post-reboot health check](healthcheck.md)
- [Sanitized firewall counters](firewall-counters.md)
- [Direct Unbound DNSSEC validation](dns-validation.md)
- [Snapshot checksums](SHA256SUMS)

`SHA256SUMS` covers the automated router snapshot. This manually prepared live
validation report is reviewed separately.

## Tests not executed

No result is claimed for:

- Android cellular printing with another vendor plugin or a dedicated remote-print application;
- direct Android IPP submission that bypasses the Samsung print service;
- printing through a dedicated CUPS or other authenticated print proxy;
- printer access from an unauthorized Tailscale identity;
- broad LAN access from the authorized phone outside the configured printer policy.

## Publication review

- [x] No passwords, credentials, authentication keys or private keys.
- [x] No Tailscale node state or router configuration export.
- [x] No public IP addresses or identifying hostnames.
- [x] Real Tailscale and LAN addresses are omitted from the manual report.
- [x] Every PASS represents an observed result.
- [x] The unsuccessful cellular test is retained as a client limitation.
- [x] Tests that were not executed are explicitly identified.
- [x] Automated snapshot checksums were verified before publication.
