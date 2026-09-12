# Evidence bundle — 2026-09-08

Generated: 20260908T160313Z

This directory combines a sanitized router-side snapshot with a separately documented remote-client validation. Do not infer remote/WAN or identity-policy behavior from the local snapshot files alone; those claims require the observations recorded in `live-validation.md`.

## Included evidence

- `environment.md` — sanitized platform, uptime, memory, and installed service-version snapshot.
- `healthcheck.md` — summarized project health-check result: 34 OK, 0 WARN, 0 FAIL, exit status 0.
- `dns-validation.md` — direct Unbound validation on loopback:53535 with `NOERROR` and DNSSEC `AD` flag.
- `firewall-counters.md` — sanitized IPv4/IPv6 managed-chain counters and policy shape at collection time.
- `live-validation.md` — dated Android LTE/5G and home-Wi-Fi validation, including the observed Tailscale DNS path and Diversion blocking result.
- `SHA256SUMS` — integrity hashes for the published bundle files present when the snapshot was generated.

## Claim boundaries

The local snapshot files establish only the router state they record at the collection point. `live-validation.md` adds the separately observed remote-client results and explicitly excludes exhaustive validation of every client platform, identity policy, exit-node scenario, or network environment.

The raw packet capture used for remote DNS verification is intentionally not published because it contained client/router addressing information. Its absence means the repository preserves the sanitized report of that observation rather than the raw capture itself.

Service/version presence in `environment.md` is not proof of end-to-end behavior for that service. In particular, a listed `syslog-ng` version does not by itself prove mTLS collector delivery, reliable-buffer recovery, or post-reboot logging continuity.

## Publication review

- Review every file manually before publishing.
- Do not add packet captures, public IP addresses, credentials, hostnames, email addresses, Tailscale node state, cookies, session tokens, or private key material.
- Keep local router observations and remote-client observations attached to the file that actually supports them.
- Treat packet counters as point-in-time evidence, not proof that every configured rule or path was exercised.
- Preserve negative, inconclusive, and not-tested results instead of converting them into PASS claims.
