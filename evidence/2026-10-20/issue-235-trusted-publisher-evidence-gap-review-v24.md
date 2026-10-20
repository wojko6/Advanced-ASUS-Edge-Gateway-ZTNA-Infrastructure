# Issue #235 — trusted publisher evidence-gap review V2.4 (2026-10-20)

> **Type:** SOURCE/DOCUMENTATION REVIEW ONLY. No new lab, router read, file modification, privilege operation or production action. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Scope

Two *separately* confirmed nonroot-owned, owner-writable root-execution targets:
`/jffs/scripts/services-start` (the **full live hook**, not a generated wrapper), and `/jffs/addons/asus-edge/bin/dns-guard` (root-Cron plus other call sites). Existing [V1.4–V1.7 hook source/DAC](issue-235-services-start-trust-chain-v14-v17.md), [V1.8–V1.12 WAN](issue-235-wan-trigger-source-v18.md), [V2.0 reboot-gate analysis](issue-235-dual-target-quiescence-model-v20.md), [V2.1 abstract monotonic candidate](issue-235-monotonic-two-target-model-v21.md), [V2.2 real inode/FD](issue-235-rootless-file-inode-publish-v22.md) and [V2.3 adversarial basename swap](issue-235-fd-to-name-publication-race-v23.md) evidence are all independent **research checkpoints**, not authorizations.

## Reuse prior experiments without overstating their proof

Past Issue #235 conversation outputs described the following **isolated** exercises: separate UID/DAC role separation, three-role FD binding, same-FD handoff and copy-verify, signed offline receipts, and a trusted Stage B external importer. Historical reported pass counts included 17/17 same-FD tests and 9/9 Stage B importer tests. **The earlier GitHub-only audit did not locate each source artifact; a follow-up Library retrieval did locate and byte-verify selected Stage B files (see below), but not the full validated original C/ZIP chain**, so treat their details as **historical operator-reported lab evidence requiring artifact/provenance cross-reference**, not as verified components of a future router publisher. Do not claim that prior role separation alone makes the actual JFFS2 publisher trusted.

## V2.4 follow-up — actual Stage B source artifacts recovered and hash-checked (2026-10-20)

**New evidence class:** previously created source files and design reports were located in the operator's ChatGPT file Library. Their raw bytes were copied only to a private ephemeral analysis directory, hash-checked with SHA-256, and *not executed, altered, re-published, or copied into the GitHub code tree*. This updates the earlier "not located" qualifier **for the recovered individual artifacts**. The *complete original C/ZIP prerequisite chain* and relevant operator Fedora testing were not re-executed in this checkpoint.

| Library artifact | Locally computed SHA-256 | Compared with reviewed V1.3–V1.5 report |
| --- | --- | --- |
| `issue235-stageb-c-authorizer-v1.3.c` | `d342582e297eb279ba8de00264a0af2078bbc393adf4346663e64e4b28db10ab` | MATCH |
| `issue235-stageb-streaming-regression-v1.3.py` | `f57eb26c5c1ba5a1b87230db8149d3f0ead5a0da1d0a6fa33aaba5867961e5ff` | MATCH |
| `issue235-stageb-c-authorizer-v1.4.c` | `d17438fee8b52f046e4c0cae66ce019d3b85b1b42a25c13f51345e42cc156da8` | MATCH |
| `issue235-stageb-independent-approval-handoff-v1.4.py` | `8a0bef29a9222dae00c4c4a217bc221a1c7e6fb72c3c1a1d53e24de8bd139b9b` | MATCH |
| `issue235-stageb-v15-offline-approval-policy-lab.py` | `c193166bf5672cca4609137219d195d382f714c0e9f2b2b6904d0f3c4a26d7f0` | MATCH |

The following *additional Library sources* were found and byte-hashed, but this checkpoint has **not** established a cross-checked independent pinned report for every one: `issue235-stageb-staging-fd-anchor-v1.1.py` (`ce05966237c54ee6576ef2f67bf9d7f54da01314a8080cfe7e3853ce7b4f6104`), `issue235-stageb-external-synthetic-importer-v1.py` (`c9375489ef8b11bd4777625f21a55dc908d948bea1a5cf356200864c99aafb2f`), `issue235-stageb-v16-authority-preflight.py` (`96450ae70d098e3d5da4dd12e821db57d63348d7d3d143a02e3bb0b0af78d269`).

**Critical scope separation:** the recovered Stage B trust contracts were authored for **Draft PR #245 SSD mount-root repair** and **three roles** (helper, ROUTER_DATA and ENTWARE synthetic UUID-like files), including an exact laboratory approval scope `pr245-ssd-mount-roots`. They are **not** a two-target privileged-script installer, and their existing approval/manifest policy **must not be reused as authorization for `services-start` or DNS Guard**. The reusable ideas are bounded streaming hashes, FD role binding, trusted launcher/authority separation, fail-closed state, and no-name-rebind staging. Each must be independently re-specified for a **different security goal** and reviewed before any implementation.

The V1.4 report explicitly notes that a valid FD and matching bytes do **not** prove provenance; its synthetic launcher pins a test fingerprint and is not an operator-managed root of trust. The V1.5 report records an intentional **same-UID policy/keyring bypass**, showing why a same-UID test fixture cannot establish independent authority. V1.6 remains a review proposal; it observes that a root-level adversary can in principle defeat discretionary file controls. No live ASUS effective-authority or verified production publisher follows from these labs.

**Remaining provenance:** the original `manifest-v1-lab.c` SHA-256 `76f6d4eb2adad3c61c87c86231af617f8bd71a4d1867d566657832c60afd3cc9` and associated archive were cited by these reports but **not independently retrieved and byte-checked here**. Several earlier short local Git commit prefixes were also not resolvable as commits in the currently available project repository. The Fedora-local original source/history may still exist; do not infer deletion or fabrication.

**Updated decision:** individual Stage B source artifacts **RECOVERED_AND_HASH_MATCHED**; end-to-end provenance/real three-role runtime execution and two-target production applicability **NOT VERIFIED**. No new synthetic rerun needed at this stage, and **no transfer** from SSD branch / PR #245 to active DNS Guard and startup hooks. Both issue gates **HOLD**.

## Gate-by-gate reconciliation### V2.5 original C/ZIP dependency attestation — operator Fedora pending

The [V2.5 original Canonical C/ZIP source preflight](issue-235-original-c-zip-provenance-v25.md) establishes the **exact expected original laboratory source path**, immutable 18,074-byte C SHA-256 and bounded companion ZIP content, derived from the recovered old pinned test harness. The source and ZIP themselves were not found in available Library files; a standalone nonroot read-only tool passed 10/10 **synthetic** self-tests, but the real source/ZIP attestation remains **PENDING** on the operator's Fedora. Do not infer that the original synthetic manifest is legitimate operator authorization for active privileged scripts.



| Critical boundary | Evidence available | Missing acceptance proof |
| --- | --- | --- |
| Reviewed bytes | Both live target bytes matched separately pinned reviewed source at read time; private Fedora backup copies exist | Independent offline trust chain protected from malicious replacement; current at-publication byte binding |
| Parent directory baseline | Selected JFFS parent directories root:root 0755 / no group-or-other write at snapshot | Complete ACL/xattr/mount/privileged-writer and FD access analysis through the *entire* staging and active path |
| Separate roles | Historical isolated separate-UID, same-FD and Stage B tests passed by operator report | Some exact Stage B source bytes recovered and SHA-checked; **distinct** live two-target UID/authority mapping and active firmware constraints are still missing |
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
