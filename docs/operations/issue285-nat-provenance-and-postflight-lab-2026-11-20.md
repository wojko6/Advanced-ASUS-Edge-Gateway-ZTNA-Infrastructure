# Issue #285 — NAT uninstall provenance and diagnostic postflight lab

**Date:** 2026-11-20  
**State:** Source/evidence reconciliation + Fedora/CI disposable mock candidate; **NOT a production fix**  
**Deployment gate:** `HOLD`  
**Issue:** [#285](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/285)  
**Lab-only Draft PR:** [#383](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/383)

## 1. Verified historical provenance and limits

The [2026-09-22 production evidence](../../evidence/2026-09-22/legacy-nat-hook-cleanup.md) records a legacy `/jffs/scripts/nat-start` hook containing **two interface-qualified, direct TCP/UDP DNS/53 REDIRECT rules**. These were distinct from the correctly scoped project-owned `tailscale0 -> EDGE_TS_PREROUTING` parent jump. The two direct rules were backed up/removed under controlled maintenance, and health checks were successful afterward.

The current [firewall-start](../../router/scripts/firewall-start) uses an explicitly interface-scoped `single_jump nat PREROUTING "$EDGE_TS_IF" EDGE_TS_PREROUTING`. The current [uninstaller](../../scripts/uninstall.sh) deletes exactly that scoped jump, flushes the managed chain, and ignores `-X` failure.

**No reviewed repository history or cited production evidence establishes that an interface-*unqualified* `-j EDGE_TS_PREROUTING` jump was ever installed by this project on the router.** The unqualified-jump case in this lab is synthetic, not confirmed historical project-owned state. It is unsafe to infer ownership from the destination chain name alone. Do not add an unconditional unqualified-jump delete.

Historical evidence does establish the different class of leftover **direct REDIRECT** rules. Those were addressed separately in September; this lab is not a retroactive assertion that they remain live.

## 2. Phase 0 baseline — observed test-only failure

The stateful fake `iptables` data lives in a temporary JSON fixture. The **unchanged production uninstaller** is copied into a disposable root, with its pre-existing test-only UID substitution; real `iptables`, router services, SSD, JFFS and firewall are never involved.

Original behavior with synthetic inputs:

| Scenario | Observation | Classification |
| --- | --- | --- |
| Current interface-scoped NAT jump | Managed jump/chain removed; unrelated foreign rule preserved | PASS |
| Duplicate scoped jumps / second run | Duplicate removal and no new state changes on repeat | PASS |
| Hypothetical unqualified jump | Jump remains, `-X EDGE_TS_PREROUTING` fails silently, uninstaller reports completion | **EXPECTED_RED** |
| Injected failure deleting the scoped jump | Reference remains, `-X` fails silently, uninstaller reports completion | **EXPECTED_RED** |
| DNS Guard fallback failure | No synthetic IPv4/IPv6 firewall operations | PASS |

The existing `ip6tables` mock checks **invocation**, not complete stateful IPv6 rule removal.

## 3. Phase 1 candidate — diagnosis only, in the copied test fixture

The test fixture optionally inserts a small **postflight** immediately after this existing NAT cleanup call:

```sh
remove_jump_and_chain nat PREROUTING "$EDGE_TS_IF" EDGE_TS_PREROUTING
```

The copied fixture then:
1. Uses read-only `iptables -t nat -S PREROUTING`; if it cannot inspect the parent, exits nonzero and reports **UNKNOWN**.
2. Checks `iptables -t nat -S EDGE_TS_PREROUTING`. If the managed chain still exists (even empty), exits nonzero with **INCOMPLETE** rather than claiming success.
3. If the managed chain is absent and the parent was inspectable, continues the current cleanup flow.

This candidate **does not delete any unqualified jump** and does not broaden the existing deletion syntax. It is a narrowly scoped failure-reporting design experiment, not a standalone recovery or security fix.

### Candidate synthetic acceptance matrix

| Scenario | Intended result |
| --- | --- |
| Valid current scoped rule | EXIT 0, managed NAT chain absent, foreign rule preserved |
| Repeat execution with no managed chain | EXIT 0, no new changes |
| Hypothetical unqualified jump | EXIT nonzero + explicit incomplete status; preserve ambiguous jump |
| Injected scoped `-D` failure | EXIT nonzero + explicit incomplete status |
| Parent NAT `-S` not inspectable | EXIT nonzero + explicit unknown status |
| IPv6 and DNS Guard | Preserve previous bounded checks; no new live behavior |

### Important limitations

- **Partial mutation precedes postflight.** DNS fallback/watchdog handling and some IPv4 chain operations may already have occurred. A nonzero verdict is not an atomic rollback. An operator recovery procedure would be needed before considering deployment.
- The initial candidate uses `-S` return values. Failure of the chain query cannot always distinguish a missing chain from a different inspection error; parent inspectability reduces but does **not eliminate** this ambiguity. It must not be called an unconditional fail-closed guarantee.
- Synthetic success does not prove compatibility with the exact ASUS GNUton/iptables/kernel combination or with all NAT chains.
- This test does not establish real historical ownership of hypothetical unqualified rules. It is explicitly **not** an authorization to delete them.
- No production source, on-router firewall rule, live service, hook, network interface, DNS resolver or file permission was changed.

## 4. How to reproduce (isolated Fedora or CI checkout)

```sh
sh -n scripts/uninstall.sh
sh -n tests/test-uninstall.sh
sh tests/test-uninstall.sh
```

The single test script runs the original baseline first, then the optional candidate against disposable mocks. It prints distinct `EXPECTED_RED`, `ISSUE285_CANDIDATE`, and `ISSUE285_LAB` verdicts; no shell command in this workflow invokes actual `iptables`.

**Verification status:** GitHub Actions exact-head result to be recorded in PR #383. No direct router test or Fed​ora-operator run is claimed.

## 5. Next gates — still HOLD

1. Obtain strong evidence for a real unqualified jump and its owner, if one exists (pinned source, exact CLI syntax, verified sanitized runtime inspection). **If not proven, exclude compatibility deletion.**
2. Decide whether non-atomic, post-operation failure reporting is acceptable or whether an explicit preflight and recoverable rollback contract is needed.
3. Establish reliable differentiation between an absent managed chain and an unexpected `-S` error in the supported router iptables version.
4. Extend stateful and negative cases to IPv6, and test unknown/read failures and recovery semantics for all managed chains.
5. Run exact-target BusyBox/kernel-compatible isolated tests and approve an explicit recovery plan.
6. Only after a separate review and operator authorization may a production source change or live maintenance be proposed.

**Current decision:** remain on the test-only Draft PR, leave Issue #285 **OPEN**, preserve `DEPLOYMENT_GATE=HOLD`.
