# Evidence bundle — 2026-09-04

Generated: 20260904T092926Z

This directory combines a sanitized router snapshot with a manually reviewed live printer/startup validation. The manual report contains both a successful remote-print case and an unsuccessful cellular case retained as a client limitation rather than rewritten as a firewall failure.

## Included evidence

- `environment.md` — sanitized platform, uptime, memory, and installed service-version snapshot.
- `healthcheck.md` — project health-check observations for Entware readiness, required swap, Tailscale, dnsmasq, managed IPv4/IPv6 firewall chains, Unbound/DNSSEC, and syslog-ng process state.
- `dns-validation.md` — direct Unbound validation on loopback:53535 with `NOERROR` and DNSSEC `AD` flag.
- `firewall-counters.md` — sanitized managed-chain counters and policy shape at collection time.
- `live-validation.md` — post-reboot startup and printer validation from an authorized Android Tailscale client over external Wi-Fi/hotspot and cellular data.
- `SHA256SUMS` — integrity hashes for the automated router snapshot files present when that snapshot was generated.

## Observed live-test boundary

The manual report records a successful physical print over external Wi-Fi/hotspot through Tailscale and the configured source-scoped printer policy. It also records successful bidirectional SNMP over cellular data but no physical cellular print because the Samsung print service did not open an IPP/raw-TCP print connection during that controlled test.

The cellular result is therefore preserved as **CLIENT LIMITATION**, not presented as a firewall denial. The report notes that no printer-policy drop occurred during the capture and that the same Tailscale subnet route and printer policy succeeded in the external-Wi-Fi case.

## Claim boundaries

This bundle does not establish results for every Android print plugin, direct IPP submission, CUPS/authenticated proxy designs, unauthorized Tailscale identities, broad LAN access, every WAN type, or every exit-node scenario. The not-executed cases remain explicitly listed in `live-validation.md`.

The health check and environment snapshot establish point-in-time router/service state. They do not independently prove end-to-end application behavior. Likewise, firewall counters show traffic already observed at collection time; they do not prove every allow/deny path was exercised.

`SHA256SUMS` covers the automated router snapshot. The manually prepared `live-validation.md` report is reviewed separately and should not be described as if it were included in that automated snapshot checksum set.

## Publication review

- Review every file manually before publishing.
- Do not add raw packet captures, public IP addresses, credentials, hostnames, email addresses, Tailscale node state, printer serial numbers, cookies, session tokens, or private key material.
- Preserve unsuccessful and not-tested outcomes; do not convert them into PASS results.
- Keep client behavior distinct from firewall behavior when packet/counter evidence shows that no denied connection was attempted.
- Keep router-state observations separate from remote-client functional tests.
