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

## Interpretation and next bounded diagnostic

The reviewed repository's `wan-event` is a short managed hook matching WAN unit 0, connected event and an `exec` handoff to the addon handler. The **live hook is not byte-identical** and lacks at least one expected lexical marker. This cannot yet be classified as a broken or compromised WAN recovery path: possible causes include a generated wrapper, older hook, a different implementation or a site-specific edit. **Do not infer that all independent DNS Guard paths have been mapped or that WAN recovery is currently broken.**

The source-confirmed addon handler contains a direct `dns-guard auto` path; the source-confirmed break-glass helper has deliberate DNS Guard calls. Whether the live WAN hook dispatches to its handler remains **NOT PROVEN**. Named Cron deletion by itself is therefore not a safe quiescence design.

Proposed **off-router V1.9 only**: compare the live WAN hook in memory against pinned source variants and report **only bounded structural markers, line counts, change-region counts and local POSIX syntax verdict**. No raw content publication, file editing, cron changes, service restarts or router commands beyond approved read-only `/bin/cat`. V1.9 is **prepared locally, not yet operator-run**; its synthetic self-test does not prove live behavior.

**Blocking decisions:** source drift is unresolved; preserve WAN fail-open and break-glass paths, keep both privileged-owner remediation targets and all production action on HOLD. Follow [design-only maintenance protocol](../../docs/operations/issue235-privileged-startup-trust-maintenance-design-2026-10-20.md).
