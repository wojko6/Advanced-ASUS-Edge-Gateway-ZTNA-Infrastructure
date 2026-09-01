# Live validation report

> Template only — replace every placeholder with an observed result or remove the row.

## Test context

| Field | Value |
|---|---|
| Date (UTC) | `<YYYY-MM-DD HH:MM>` |
| Router model | `<model>` |
| Firmware | `<version>` |
| Tailscale | `<version>` |
| Unbound | `<version>` |
| Configuration revision | `<commit SHA>` |
| Tester/source role | `<admin/user/external>` |

## Security matrix

| ID | Source role | Destination/service | Expected | Command or method | Observed | Verdict |
|---|---|---|---|---|---|---|
| FW-01 | External/WAN | Router TCP 8443 | Denied | `<command>` | `<observation>` | `<PASS/FAIL>` |
| FW-02 | Tailscale admin device | Router TCP 8443 | Allowed | `<command>` | `<observation>` | `<PASS/FAIL>` |
| FW-03 | Tailscale non-admin device | Router TCP 8443 | Denied | `<command>` | `<observation>` | `<PASS/FAIL>` |
| FW-04 | Tailscale device | Router TCP 22 | Denied by default | `<command>` | `<observation>` | `<PASS/FAIL>` |
| FW-05 | Approved user | Approved LAN service | Allowed | `<command>` | `<observation>` | `<PASS/FAIL>` |
| FW-06 | Tailscale device | Unlisted LAN service | Denied | `<command>` | `<observation>` | `<PASS/FAIL>` |
| DNS-01 | Tailscale device | External resolver TCP/UDP 53 | Redirected locally | `<command/capture>` | `<observation>` | `<PASS/FAIL>` |
| DNS-02 | Router loopback | Unbound DNSSEC | AD flag present | `<command>` | `<observation>` | `<PASS/FAIL>` |
| TS-01 | Unauthorized exit user | Internet through exit node | Denied by Grants | `<method>` | `<observation>` | `<PASS/FAIL>` |

## Performance

| Flow | Median latency | p95 latency | Loss | Throughput | CPU peak | RAM peak |
|---|---:|---:|---:|---:|---:|---:|
| Direct WAN | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` |
| Tailscale subnet route | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` |
| Tailscale exit node | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` |

## Deviations and follow-up

- `<unexpected result, explanation, and linked issue/commit>`

## Publication review

- [ ] No credentials, keys, tokens, node state, or router exports.
- [ ] No public IP addresses or identifying hostnames.
- [ ] Internal addresses are anonymized consistently.
- [ ] Every PASS/FAIL represents an observed result.
- [ ] Relevant sanitized counters or extracts are linked.
