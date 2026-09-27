# Firewall temporary-guard cleanup — live validation

**Date:** 2026-09-27  
**Reference platform:** ASUS TUF-AX5400 / Asuswrt-Merlin GNUton `3004.388.11_1-gnuton1_tuf`  
**Issue:** #91  
**Related PRs:** #92, #93  
**Result:** LIVE VALIDATED

## Summary

Post-Unbound validation exposed a false-positive exit-node healthcheck failure and a stale fail-closed firewall guard left in the parent INPUT/FORWARD chains.

The healthcheck false positive was fixed in PR #92 by ignoring an ingress-scoped Tailscale DROP when evaluating the platform WAN return path. Live validation then confirmed that the project healthcheck returned:

```text
Summary: 0 failure(s), 0 warning(s)
```

The first stale-guard cleanup implementation in PR #92 used an awk expression that passed CI on Ubuntu but failed on the router BusyBox awk implementation. The router emitted:

```text
awk: cmd. line:2: Unexpected end of string
[: bad number
```

The stale guards therefore remained after that first deployment attempt.

PR #93 replaced the cleanup logic with BusyBox-safe shell/grep exact-rule matching and added a stateful regression test for duplicate temporary guards.

## Live state before the corrected cleanup

The reference router contained stale exact project fail-closed guards:

```text
-A INPUT -i tailscale0 -j DROP
-A FORWARD -i tailscale0 -j DROP
```

The platform return path itself was healthy. The parent FORWARD chain contained the platform `RELATED,ESTABLISHED` ACCEPT before the real WAN egress DROP rules, and the patched healthcheck correctly reported the return path as healthy.

A backup of the active firewall-start script plus the pre-change filter/NAT state was created on persistent router storage before deploying the corrected script.

## Corrected deployment

The PR #93 `router/scripts/firewall-start` was staged, syntax-checked, installed over the active JFFS hook and executed once through the normal project firewall apply path.

The corrected cleanup removed the stale exact guards:

```text
INPUT_GUARDS=0
FORWARD_GUARDS=0
```

No BusyBox awk errors were produced by the corrected implementation.

## Final healthcheck

The final project healthcheck reported all checks healthy, including:

- exit-node WAN interface resolved to the active WAN interface;
- IPv4 forwarding enabled;
- project exit-node forwarding rule present;
- platform WAN NAT present;
- platform established/related return path present before WAN drop;
- managed Tailscale filter/NAT chains present and ordered correctly;
- no legacy broad Tailscale ACCEPT rules;
- no legacy direct Tailscale NAT rules outside the managed chain;
- LAN DNS and LAN DoT enforcement healthy;
- Unbound running and DNSSEC validation healthy;
- syslog-ng running.

Final result:

```text
Summary: 0 failure(s), 0 warning(s)
HEALTHCHECK_RC=0
```

## Root cause

Two separate defects were involved:

1. **Healthcheck classification bug** — an ingress-scoped Tailscale fail-closed DROP was treated as though it could block WAN return traffic. It cannot match packets arriving from the WAN and therefore should not invalidate the platform return-path check.
2. **Stale temporary guard cleanup bug** — a previous failed/interrupted firewall apply could leave an exact temporary Tailscale DROP guard behind. The first cleanup fix used a BusyBox-incompatible awk expression, so it did not remove the stale guard on the router.

The final implementation removes the current temporary guard and any older exact duplicates using portable shell/grep matching while preserving unrelated DROP rules.

## Conclusion

Issue #91 is live validated on the reference router.

The stale INPUT/FORWARD Tailscale fail-closed guards are removed, the exit-node return-path healthcheck no longer produces the observed false positive, and the full project healthcheck is clean at `0 failure(s), 0 warning(s)`.
