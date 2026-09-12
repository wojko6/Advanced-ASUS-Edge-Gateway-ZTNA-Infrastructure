# Evidence bundle — 2026-09-09

Generated: 20260909T152723Z

This directory combines a sanitized router snapshot with a separately reviewed live validation focused on encrypted-DNS bypass behavior. The report deliberately records both what the reference baseline intercepted and what it did not prevent.

## Included evidence

- `environment.md` — sanitized platform and installed service-version snapshot.
- `healthcheck.md` — point-in-time project health-check result.
- `dns-validation.md` — direct Unbound validation on loopback:53535.
- `firewall-counters.md` — sanitized managed-chain counters and policy shape at collection time.
- `live-validation.md` — manual DNS-bypass matrix covering plain DNS, Android Private DNS/DoT, a temporary TCP/853 enforcement test, and Brave Secure DNS over TCP/443.
- `SHA256SUMS` — integrity hashes for the automated published snapshot files.

## Observed live-test scope

The manual report records that plain client DNS used the local dnsmasq/resolver path, while Android Private DNS to `dns.google` used TCP/853 and bypassed local dnsmasq under the tested baseline. A temporary IPv4 TCP/853 reject rule then blocked the tested DoT path and received matching traffic counters.

The report also records that Brave Secure DNS could bypass local dnsmasq using encrypted traffic to Cloudflare over TCP/443. The encrypted payload was not decrypted, so the evidence demonstrates absence of the target query from the local dnsmasq path alongside the observed encrypted connection; it does not claim application-payload inspection.

## Claim boundaries

The temporary TCP/853 rule was a controlled validation mechanism, not part of the permanent baseline represented by this bundle. Do not cite this evidence as proof that the current deployment permanently blocks DoT.

The report explicitly states that the baseline did not comprehensively block DoH and that blocking UDP/443 alone is insufficient because TCP/443 fallback can remain available. It therefore supports the architectural conclusion that comprehensive encrypted-DNS control cannot be claimed from network-layer port filtering alone.

The deployed configuration revision was not independently verified during this validation. The report records a repository release baseline and a repository HEAD under audit separately; do not present either value as cryptographic proof of the exact live-router configuration at test time.

This bundle does not establish every DoT provider, DoQ/HTTP3 behavior, every browser/application resolver, IPv6 enforcement, endpoint-policy effectiveness, or a universal encrypted-DNS prevention result. Those require separate dated tests.

`SHA256SUMS` covers the automated published snapshot. The manually prepared `live-validation.md` report is reviewed separately and should not be described as if it were part of that automated checksum set unless its hash is explicitly present.

## Publication review

- Review every file manually before publishing.
- Do not add raw packet captures, public IP addresses, credentials, hostnames, email addresses, Tailscale node state, cookies, session tokens, or private key material.
- Preserve the bypass findings; negative security observations are evidence, not failures to hide.
- Keep temporary enforcement tests distinct from the deployed baseline.
- Do not infer decrypted DoH content from connection metadata.
- Preserve the distinction between repository revision metadata and independently verified live configuration.
