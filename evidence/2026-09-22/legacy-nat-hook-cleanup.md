# Legacy NAT hook cleanup — 2026-09-22

**Status:** PASS  
**Evidence class:** Router live / controlled maintenance  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin

## Finding

A read-only inspection of the live `nat/PREROUTING` chain showed:

- one active project-owned jump from the Tailscale interface to `EDGE_TS_PREROUTING`;
- two additional direct TCP/UDP port-53 `REDIRECT` rules on the same interface;
- zero packets/bytes on both direct rules;
- active DNS counters inside `EDGE_TS_PREROUTING`.

The two direct rules were therefore redundant in the observed ordering.

The source was a legacy `/jffs/scripts/nat-start` hook containing only those two direct DNS redirect commands. Its pre-cleanup SHA-256 was:

```text
3ceb699bf99bb52000f55010db848f5bdd81a489b3aeefab7103d6381d525b14
```

The active hook had mode `0777`, which was broader than required for a firmware-executed JFFS hook.

## Controlled cleanup

The legacy hook was copied to the private ASUS Edge backup area before removal; the backup copy was restricted to mode `0600`.

The active legacy `nat-start` hook was then removed, followed by deletion of the two duplicate direct DNS redirect rules from the live parent `PREROUTING` chain.

After cleanup:

- the single project-owned Tailscale parent jump remained;
- the managed UDP/TCP DNS redirects inside `EDGE_TS_PREROUTING` remained;
- no direct duplicate Tailscale DNS redirects remained in the parent chain;
- the deployed health check completed successfully.

Final result:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

## Follow-up hardening

The repository health check was extended to detect:

1. exact-interface Tailscale NAT rules in parent `PREROUTING` that bypass the project-owned `EDGE_TS_PREROUTING` chain;
2. active JFFS hooks relevant to this deployment that are symlinks or group/world writable.

Focused regression coverage passed in CI. The hardened health-check revision was subsequently deployed to the reference router and live-validated with SHA-256 `5d96555bad141c40191855e2f121de0412635cb7e5fe14d41b5ec73842db6233`, zero failures, zero warnings, and `HEALTHCHECK_RC=0`.

See `healthcheck-drift-hardening-live-validation.md` for the separate deployment evidence.

## Claim boundary

This artifact records the observed stale hook/rules and their controlled removal. It does not claim that every possible third-party JFFS hook or NAT rule is unsafe, and it does not change the documented limitation that DoH/DoT/other encrypted DNS transports are outside classic port-53 interception.

Deployment-specific WAN addresses, Tailscale addresses, device identifiers, and unrelated raw firewall output are intentionally omitted.
