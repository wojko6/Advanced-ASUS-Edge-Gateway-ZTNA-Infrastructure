# Updated health-check deployment validation — 2026-09-22

**Status:** PASS  
**Evidence class:** Router live / controlled maintenance  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin  
**Observed time:** 2026-09-22 18:07:17 CEST

## Purpose

Validate that the current repository version of `scripts/healthcheck.sh`, including the post-AUDIT-02 exit-node runtime checks, is deployed on the reference router and executes successfully against the live deployment.

## Deployment safety

The candidate script was first transferred to a temporary router path and checked independently before replacing the deployed copy. The existing deployed health-check script was backed up before replacement. The deployment did not intentionally restart the firewall, bounce WAN, change Tailscale configuration, or modify DNS policy.

## Integrity

Repository/deployed SHA-256:

```text
e03d6abd7a740524ba5a2c6799a47559ef187b22bb1a3209eb94ffc4a30a7e47
```

The active deployed file at `/jffs/addons/asus-edge/bin/healthcheck.sh` matched that digest.

## Live result

The live health check reported successful checks for the deployed service and policy areas, including:

- configuration readability and Entware readiness;
- required swap;
- Tailscale process/connectivity, `tailscale0`, and intentional `netfilter-mode=off`;
- absence of competing Tailscale-managed netfilter chains;
- dnsmasq integration with `tailscale0`;
- project IPv4 chains, ordering, default-deny endings, and duplicate-jump guards;
- source-scoped printer policy and disabled ASUS USB print services;
- fail-closed IPv6 guards and chain ordering;
- absence of legacy broad Tailscale accept/NAT rules;
- Unbound availability and DNSSEC validation on port 53535;
- syslog-ng availability;
- the exit-node runtime prerequisites encoded after AUDIT-02.

Final result:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

## Claim boundary

This artifact demonstrates that this exact health-check revision was present on the reference router at the documented time and that all checks executed by that revision passed at that point in time.

It does not prove indefinite future health, replace the separate packet-correlation evidence for AUDIT-02/AUDIT-03, or imply that later repository changes are automatically deployed.

Deployment-specific addresses, node identities, credentials, storage identifiers, and unrelated raw logs are intentionally omitted.
