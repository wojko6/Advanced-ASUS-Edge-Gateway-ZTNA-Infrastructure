# Live validation report — 2026-09-03

## Test context

| Field | Value |
|---|---|
| Validation period | 2026-09-02 to 2026-09-03 UTC |
| Evidence collected | 2026-09-03 08:46:55 UTC |
| Router model | TUF-AX5400 |
| Firmware | 3.0.0.4 388.9 2-gnuton1 |
| Kernel | 4.1.52 |
| Router memory | 512188 kB |
| Tailscale | 1.102.3 |
| Unbound | 1.24.2 |
| Router syslog-ng | 4.10.2 |
| Collector syslog-ng | 4.3.1 |
| Router deployment revision | aeef824 |
| Evidence collector revision | 3ae8741 |
| Test source | Authorized Tailscale administrator device and router loopback |

All Tailscale addresses, public endpoints, usernames, hostnames, and certificate material are omitted or represented by descriptive placeholders.

## Security and availability validation

| ID | Source | Destination or function | Expected | Command or method | Observed | Verdict |
|---|---|---|---|---|---|---|
| TS-01 | Authorized Tailscale administrator | Router Tailscale endpoint | Reachable | `tailscale ping ROUTER_TS_IP` | Router replied over Tailscale | PASS |
| FW-01 | Authorized Tailscale administrator | Router HTTPS TCP 8443 | Allowed | `curl -kI https://ROUTER_TS_IP:8443/` | HTTP 200 returned | PASS |
| FW-02 | Tailscale administrator | Router SSH TCP 1122 | Denied by policy | `nmap -Pn -sT -p 53,1122,8443 ROUTER_TS_IP` | TCP 1122 reported as filtered; TCP 53 and 8443 were open | PASS |
| FW-03 | Router | Managed firewall chains | Present exactly once | Project health check and sanitized `iptables` counters | IPv4, NAT and IPv6 chains and jumps passed; legacy broad rules absent | PASS |
| DNS-01 | Tailscale administrator | Router DNS over UDP | Resolve through local DNS path | `dig +dnssec @ROUTER_TS_IP cloudflare.com A` | Status NOERROR and signed response returned | PASS |
| DNS-02 | Tailscale administrator | Router DNS over TCP | Resolve through local DNS path | `dig +tcp +dnssec @ROUTER_TS_IP cloudflare.com A` | Status NOERROR and signed response returned | PASS |
| DNS-03 | Tailscale administrator | Invalid DNSSEC domain | Reject invalid validation chain | `dig +dnssec @ROUTER_TS_IP dnssec-failed.org A` | Status SERVFAIL returned | PASS |
| DNS-04 | Router loopback | Unbound on TCP/UDP 53535 | DNSSEC validation active | Direct Unbound query with DNSSEC requested | Status NOERROR with AD flag | PASS |
| LOG-01 | Client without certificate | Collector TCP 6514 | TLS handshake rejected | `openssl s_client -tls1_2` without a client certificate | TLS handshake failed and returned non-zero status | PASS |
| LOG-02 | Router with trusted client certificate | Collector TCP 6514 | mTLS connection accepted | `openssl s_client -tls1_2` with the router certificate and key | TLS connection established and certificate verification succeeded | PASS |
| LOG-03 | Router syslog-ng | Central collector | Deliver logs over mTLS | Generated an `MTLS_ENFORCED_END_TO_END_OK` marker | Marker appeared in the collector log assigned to the router | PASS |
| LOG-04 | Router disk buffer | Temporarily unavailable collector | Preserve and resend queued events | Collector stopped, three markers generated, collector restarted | All three `BUFFER_RECOVERY` markers were delivered | PASS |
| LOG-05 | Router after reboot | Central collector | Automatically reconnect and resume forwarding | Router reboot followed by an `MTLS_REBOOT_FINAL_OK` marker | mTLS connection re-established and marker reached the collector | PASS |
| RET-01 | Collector | Centralized router logs | Compress after 24 hours and delete after 30 days | Controlled systemd retention test | Old test log compressed, expired archive deleted, active production log untouched | PASS |
| BOOT-01 | Router after reboot | Complete managed stack | Restore services and policy automatically | `/jffs/addons/asus-edge/bin/healthcheck.sh` | 0 failures and 0 warnings | PASS |

## Collected evidence

- [Environment snapshot](environment.md)
- [Post-reboot health check](healthcheck.md)
- [Sanitized firewall counters](firewall-counters.md)
- [Direct Unbound DNSSEC validation](dns-validation.md)
- [Snapshot checksums](SHA256SUMS)

`SHA256SUMS` covers the published snapshot files. The original collector checksums were verified before non-semantic trailing padding was removed from `firewall-counters.md`; checksums were then regenerated. This manually prepared live-validation report is reviewed separately.

## Tests not executed

The following scenarios were not tested and no PASS/FAIL result is claimed for them:

- access to TCP 8443 from a non-administrator Tailscale identity;
- access to the management interface directly from the public WAN;
- approved and unapproved services behind a Tailscale subnet route;
- exit-node use by an explicitly unauthorized identity;
- throughput, latency, packet-loss, CPU and memory benchmarks;
- certificate revocation and expired-certificate rejection.

These scenarios require additional test identities, an external network location, controlled ACL changes, or dedicated performance measurements.

## Publication review

- [x] No passwords, credentials, authentication keys or private keys.
- [x] No Tailscale node state or router configuration export.
- [x] No public IP addresses or identifying hostnames.
- [x] Internal source, destination and translated NAT addresses are anonymized.
- [x] Every reported PASS represents an observed result.
- [x] Tests that were not executed are explicitly identified.
- [x] Automated snapshot checksums have been verified.
- [x] Sanitized firewall, health-check and DNS evidence is linked.
