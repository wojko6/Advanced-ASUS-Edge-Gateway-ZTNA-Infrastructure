# Live validation report

## Test context

| Field | Value |
|---|---|
| Date | 2026-09-05 |
| Router model | ASUS TUF-AX5400 |
| Firmware | ASUSWRT-Merlin 3004.388.9_2-gnuton1 |
| Tailscale | 1.102.3 |
| Configuration revision | c841073cdceea8012ebe053604813c72c8188500 |
| Validation stage | Post-deployment, post-reboot |

## Observed validation

| ID | Check | Expected | Observed | Verdict |
|---|---|---|---|---|
| POST-01 | Core services after reboot | tailscaled, Unbound and syslog-ng running | All three services running after reboot | PASS |
| POST-02 | Project healthcheck | 0 failures, 0 warnings | 0 failures, 0 warnings; exit status 0 | PASS |
| NF-01 | Tailscale netfilter ownership | Tailscale native netfilter disabled | NetfilterMode = 0 | PASS |
| NF-02 | Native Tailscale chains | ts-input, ts-forward and ts-postrouting absent | All three chains absent | PASS |
| NF-03 | Project firewall policy | EDGE_TS_* chains active and validated | Healthcheck confirmed managed IPv4/IPv6 chains and parent jumps | PASS |
| TS-01 | Tailscale control-plane health | Connected with no router health warning | Tailscale connected; previous ts-postrouting health warning absent | PASS |
| DNS-02 | Router loopback Unbound DNSSEC | AD flag present | Healthcheck confirmed DNSSEC validation with AD flag | PASS |

## Evidence references

- `environment.md`
- `healthcheck.md`
- `firewall-counters.md`
- `dns-validation.md`

## Scope

This validation records only checks actually observed during the final
post-reboot deployment validation.

The broader remote-client, WAN and identity-policy matrix is not represented
as completed in this snapshot unless separately tested and documented.

## Publication review

- [x] No credentials, keys, tokens or Tailscale node state included.
- [x] No public IP addresses included.
- [x] No identifying hostnames or usernames included.
- [x] Every PASS above represents an observed result.
- [x] Sanitized supporting evidence is included in this directory.
