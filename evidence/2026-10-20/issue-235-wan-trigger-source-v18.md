# Issue #235 — WAN / emergency DNS Guard trigger source V1.8 (2026-10-20)

> **Evidence class:** sanitized **operator-reported** two equal read-only SSH snapshots; no runtime WAN event trace, no proof of owner/DAC trust, no writes to ASUS or Cron.  
> **Result:** `TRIGGER_SOURCE_PREFLIGHT=SOURCE_DRIFT_OR_READ_HOLD`, audit exit `2`. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`, `DEPLOYMENT_GATE=HOLD`.

## Scope and verified source reference

The Fedora V1.8 reader restricted SSH to `/bin/cat` on three fixed ASUS paths, with two equal point-in-time reads per target and Git blob comparison to pinned commit `9a47c4eb384f770c91f15264dcc4079f2a03b12a`. Router scripts were **not executed**; no target file contents were printed or saved locally by the tool. No runtime event was induced or monitored.

| On-router file | Two read snapshots | Pinned source contents | Bounded lexical trigger check |
| --- | --- | --- | --- |
| `/jffs/scripts/wan-event` | Equal at observation points | **DIFFERS_HOLD** | **NOT_ALL_FOUND_HOLD** |
| `/jffs/addons/asus-edge/bin/wan-event-handler` | Equal at observation points | **EXACT_MATCH** | **PRESENT** |
| `/jffs/scripts/edge-dns-breakglass.sh` | Equal at observation points | **EXACT_MATCH** | **PRESENT** |

The two exact matches establish **source byte identity at read time only**, not actual invocation or owner trust.

## V1.9 operator-reported structural classification (same day)

Read-only follow-up V1.9 observed the production `/jffs/scripts/wan-event` as **324 bytes / 8 lines**, with an `#!/bin/sh` shebang and `ASUS_EDGE_MANAGED_HOOK` marker, local POSIX syntax PASS. The hook was classified as `OTHER_OR_LOCAL_VARIANT_NOT_VERIFIED` against the wrong full-script reference. It contained **no literal WAN-unit/connected markers, handler path or direct DNS Guard call**. The three source-diff regions and those missing literal markers must **not** be treated as proof of missing semantics or failed WAN recovery.

**New source-backed interpretation:** the pinned `scripts/install.sh` `install_hook wan-event` helper generates a short wrapper that sources the edge config, optionally runs a preserved legacy hook when `EDGE_RUN_LEGACY_HOOKS=1`, then `exec`s `/jffs/addons/asus-edge/bin/wan-event`. Reconstructing that canonical wrapper from the pinned installer with fixed production directories yields **exactly 324 bytes and 8 lines** — the same size as the V1.9 production hook. Expected wrapper SHA-256: `8ae4a6eaddd5fa2c1a6a2beb85f34a3ccaf9111bedac23bdd0827ca4ddc4212c`; this SHA has **not been compared to the live hook yet**. Exact full-script addon reference `router/scripts/wan-event` SHA-256: `bdb83a63a1e7fda35d313abca33f326580ea0219475472b32050b8649bd36f79` (382 bytes), **also not compared to live addon yet**.

**Consequence:** the likely chain is firmware wrapper → addon `wan-event` → previously byte-verified `wan-event-handler` → DNS Guard. V1.8 mistakenly skipped source attestation of the intermediate addon `wan-event`. Even if both hashes subsequently match, config-sourced legacy hooks, owner/parent trust, concurrent writer risk and live WAN invocation remain unresolved. **Do not claim production dispatch PASS before the missing hop is verified.**

**Next test:** two bounded read-only SSH `/bin/cat` streams with off-router SHA-256 comparison against these two pins; no source content printing and no router mutation. Do not probe or expose config content unless separately necessary. All gates **HOLD**.

## Interpretation and next bounded diagnostic

The reviewed repository's `wan-event` is a short managed hook matching WAN unit 0, connected event and an `exec` handoff to the addon handler. The **live hook is not byte-identical** and lacks at least one expected lexical marker. This cannot yet be classified as a broken or compromised WAN recovery path: possible causes include a generated wrapper, older hook, a different implementation or a site-specific edit. **Do not infer that all independent DNS Guard paths have been mapped or that WAN recovery is currently broken.**

The source-confirmed addon handler contains a direct `dns-guard auto` path; the source-confirmed break-glass helper has deliberate DNS Guard calls. Whether the live WAN hook dispatches to its handler remains **NOT PROVEN**. Named Cron deletion by itself is therefore not a safe quiescence design.

Proposed **off-router V1.9 only**: compare the live WAN hook in memory against pinned source variants and report **only bounded structural markers, line counts, change-region counts and local POSIX syntax verdict**. No raw content publication, file editing, cron changes, service restarts or router commands beyond approved read-only `/bin/cat`. V1.9 is **prepared locally, not yet operator-run**; its synthetic self-test does not prove live behavior.

**Blocking decisions:** source drift is unresolved; preserve WAN fail-open and break-glass paths, keep both privileged-owner remediation targets and all production action on HOLD. Follow [design-only maintenance protocol](../../docs/operations/issue235-privileged-startup-trust-maintenance-design-2026-10-20.md).
