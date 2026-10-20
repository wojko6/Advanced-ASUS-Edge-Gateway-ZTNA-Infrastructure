# Issue #235 — trusted publisher evidence-gap review V2.4 (2026-10-20)

> **Type:** SOURCE/DOCUMENTATION REVIEW ONLY. No new lab, router read, file modification, privilege operation or production action. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Scope

Two *separately* confirmed nonroot-owned, owner-writable root-execution targets:
`/jffs/scripts/services-start` (the **full live hook**, not a generated wrapper), and `/jffs/addons/asus-edge/bin/dns-guard` (root-Cron plus other call sites). Existing [V1.4–V1.7 hook source/DAC](issue-235-services-start-trust-chain-v14-v17.md), [V1.8–V1.12 WAN](issue-235-wan-trigger-source-v18.md), [V2.0 reboot-gate analysis](issue-235-dual-target-quiescence-model-v20.md), [V2.1 abstract monotonic candidate](issue-235-monotonic-two-target-model-v21.md), [V2.2 real inode/FD](issue-235-rootless-file-inode-publish-v22.md) and [V2.3 adversarial basename swap](issue-235-fd-to-name-publication-race-v23.md) evidence are all independent **research checkpoints**, not authorizations.

## Reuse prior experiments without overstating their proof

Past Issue #235 conversation outputs described the following **isolated** exercises: separate UID/DAC role separation, three-role FD binding, same-FD handoff and copy-verify, signed offline receipts, and a trusted Stage B external importer. Historical reported pass counts included 17/17 same-FD tests and 9/9 Stage B importer tests. **The present GitHub source/doc audit did not locate a standalone source-controlled, reproducible artifact and immutable source pin for each of those specific exercises**, so treat their details as **historical operator-reported lab evidence requiring artifact/provenance cross-reference**, not as verified components of a future router publisher. Do not claim that prior role separation alone makes the actual JFFS2 publisher trusted.

## Gate-by-gate reconciliation

| Critical boundary | Evidence available | Missing acceptance proof |
| --- | --- | --- |
| Reviewed bytes | Both live target bytes matched separately pinned reviewed source at read time; private Fedora backup copies exist | Independent offline trust chain protected from malicious replacement; current at-publication byte binding |
| Parent directory baseline | Selected JFFS parent directories root:root 0755 / no group-or-other write at snapshot | Complete ACL/xattr/mount/privileged-writer and FD access analysis through the *entire* staging and active path |
| Separate roles | Historical isolated separate-UID, same-FD and Stage B tests passed by operator report | Reproducible exact source artifact, live target-specific UID/authority mapping and active firmware constraints |
| Stage object | V2.3 proves post-check **basename** swap under a writer with stage-dir write permission; root-owned parent observation limits that scenario for ordinary nonroot attackers | Root-exclusive new stage directory, trusted owner/mode, single-link/digest, no external writable FD, and no verified-name-to-different-inode gap |
| Publication | V2.2 observed single-path rename/inode behavior; V2.1 models per-target monotonic improvement | Firmware-compatible safe *root-owned* publication, object identity binding, JFFS2 failure semantics, no transient unreviewed root-executable bytes |
| Old target | Owner can write old file; old FD survives rename in synthetic Linux fixture | Drain/contain in-flight root executions and previously opened FDs; coordinate all root-Cron/WAN/manual/boot entrypoints |
| Interrupted transition | V2.0 red tests show residual untrusted script after partial publish; V2.1 counts conditional classes | Independently recoverable two-file inputs and tested JFFS2 power-cut/reboot behavior; root-owned recovery that never republishes nonroot-owned executables |
| DNS availability | WAN source/DAC inventory and break-glass bytes checked at read snapshots | Independent operator recovery and protected DNS service continuity during a blocked/interrupted publication |
| Authorization | Docs-only Draft PR #270 | Separate explicit staging, apply and reboot GO; absence of general installer or automatic Cron changes |

**Specific threat-model clarification:** a root-owned directory with no group/other write blocks ordinary nonroot *basename* swaps under standard DAC, unlike V2.3's deliberate same-UID writable fixture. However, **nonroot-owned old target contents remain owner-writable** even when their parent directory is root-owned, and an already-open writable FD may survive rename. Neither threat is solved solely by a pathname digest or repository-approved source pin.

## Decision and next test worth doing

**Do not repeat V2.3 or generic three-UID synthetic tests.** The next highest-value investigation is to **retrieve and pin the exact existing three-role/Stage B helper artifacts** and compare their trust-contract assumptions with the target ASUS/JFFS2 mount, old-writer FD behavior, and privileged publish authority. If those artifacts cannot be recovered, clearly mark provenance `UNVERIFIED` rather than inventing implementations.

Then separately review **protected off-router recovery availability** and GNUton/JFFS2 *single-target* failure behavior. Until those questions are concretely answered there is **no trusted production runbook** and no basis to authorize even a guard-first or hook-first publish.

No private paths, router owner IDs, keys, helper payloads or script contents have been published in this report.
