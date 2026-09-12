# Evidence bundle — 2026-09-03

Generated: 20260903T084655Z

This directory contains the earliest published comprehensive live-security validation in the current evidence series. It combines an automated sanitized router snapshot with a separately reviewed manual report covering Tailscale management access, firewall behavior, DNSSEC, centralized logging, retention, and post-reboot recovery.

## Included evidence

- `environment.md` — sanitized platform, memory, and installed service-version snapshot.
- `healthcheck.md` — point-in-time project health-check observations.
- `dns-validation.md` — direct Unbound DNSSEC validation on loopback:53535.
- `firewall-counters.md` — sanitized managed IPv4/NAT/IPv6 chain counters and policy shape.
- `live-validation.md` — manual security and availability matrix performed across 2026-09-02 to 2026-09-03.
- `SHA256SUMS` — integrity hashes for the automated published snapshot files.

## Observed live-test scope

The manual report records PASS observations for:

- Tailscale reachability from an authorized administrator device;
- router HTTPS on TCP 8443 from the authorized administrator and policy denial of router SSH TCP 1122;
- presence of the managed firewall chains/jumps and absence of the legacy broad Tailscale rules checked by the project health check;
- DNS over UDP and TCP through the router, rejection of an invalid DNSSEC chain, and direct Unbound DNSSEC validation;
- rejection of a collector TLS connection without a client certificate and acceptance with the trusted router client certificate;
- end-to-end syslog-ng marker delivery over mTLS;
- disk-buffer recovery after a controlled collector outage;
- forwarding recovery after a controlled router reboot;
- the controlled collector retention test;
- post-reboot project health check with zero failures and zero warnings.

These are dated observations from the recorded deployment revision, not guarantees about later revisions or every possible network/client condition.

## Tests explicitly not executed

The manual report makes no result claim for management HTTPS from a non-administrator Tailscale identity, direct public-WAN management access, the complete subnet-route allow/deny matrix, unauthorized exit-node use, performance benchmarking, certificate revocation, or expired-certificate rejection.

Do not convert those untested scenarios into PASS claims based on configuration intent or neighboring tests.

## Evidence boundaries

`SHA256SUMS` covers the automated published snapshot. The manually prepared `live-validation.md` report is reviewed separately. The report also records that the original collector checksums were verified before non-semantic trailing padding was removed from `firewall-counters.md`, after which the published snapshot checksums were regenerated.

A successful mTLS marker proves delivery for the recorded validation event; it does not establish continuous delivery outside the observation. Likewise, successful buffer recovery proves the controlled outage scenario that was executed, not arbitrary outage duration or disk-failure recovery.

The firewall observations prove the tested administrator/service cases and recorded chain state. They do not establish identity-policy behavior for identities that were not exercised.

## Publication review

- Review every file manually before publishing.
- Do not add raw packet captures, public IP addresses, credentials, hostnames, email addresses, Tailscale node state, certificate private material, cookies, or session tokens.
- Preserve the original deployment/evidence-collector revisions when interpreting historical results.
- Keep automated snapshot evidence separate from the manually reviewed live matrix.
- Preserve not-tested scenarios as not tested.
- Do not generalize point-in-time PASS observations into long-term availability or universal policy claims.
