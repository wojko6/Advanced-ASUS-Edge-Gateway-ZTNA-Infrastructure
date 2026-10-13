# Repository-wide documentation consistency follow-up — 2026-10-13

**Status:** SOURCE-ONLY CLEANUP / current audit disposition (no production change)  
**Reviewed main baseline:** `1e866dba457dcbee17cace5eefb34d110e10096c` from merged PRs #228 and #231.  
**Inventory:** GitHub tree API: 422 blobs, 220 Markdown files, 62 directory entries; source, docs and dated evidence were compared on their appropriate evidence scopes. This was not an exhaustive execution test of all files or a new live ASUS/Fedora acceptance.

## Accepted state against which discrepancies were checked

- ASUS TUF-AX5400 / GNUton 388.11 remains production; RT-BE88U migration was **cancelled** on 2026-10-12; optional OPNsense remains undated isolated research, not installed.
- DNS Guard **v3.2** accepted on current reference router with bounded 2026-10-08 live evidence / 2026-10-09 existing-router reboot; DNS Guard v3.1 is historical.
- Both Pi-hole and firmware dnsmasq use **the same** router Unbound; DNS Guard affects router-system DNS only; no production LAN-client automatic DNS failover.
- Grafana YAML has 15 direct Email receiver rules. Operator-confirmed synthetic `Firing → Resolved` Gmail+Telegram delivery happened 2026-10-12. Issue #178 is **closed**, while provisioning parity, anti-flap/grouping, reload persistence and individual recovery-rule delivery remain unproven.
- Full clean-device Pi-hole-aware DR #129 and DNS client failover #212 remain open. RC13J lab results in **draft PR #227** are not deployed.
- The repository software `VERSION` is `2.1.4-dev`; **ASUS CORE v1.0** is an engineering stability milestone, not the same release numbering system.

## Confirmed/documented discrepancies and disposition

| ID | Scope / evidence | Disposition |
| --- | --- | --- |
| A-01 | `docs/operations.md` still called v3.2 an unaccepted candidate while current state/evidence confirm accepted PR #197 baseline | **Corrected** current operational section and acceptance limits |
| A-02 | `docs/dns-guard-v3.2-live-validation.md` was written before #192/#193 closure and contained commands that would alter DNS/WAN/reboot production | **Marked COMPLETED/HISTORICAL**, added unambiguous do-not-rerun warning and current accepted source |
| A-03 | `monitoring/README.md` said closed #178 was still responsible for Telegram escalation | **Corrected** with bounded Email+Telegram synthetic scope and remaining provisioning/anti-flap risks |
| A-04 | `docs/roadmap.md` listed explicitly closed #178 inside a “Still open” list | **Moved** to a clearly closed-status subsection and retained unresolved tests |
| A-05 | `docs/documentation-model.md` did not explain CORE v1.0 vs software package version | **Clarified** milestone/version distinction and mandatory safety header for old operational runbooks |
| A-06 | Canonical docs could drift back to outdated versions despite passing Markdown link checks | **Added** `tests/test-doc-current-state.py` and a CI step for narrow source contract checks; not a production test |
| A-07 | `monitoring/grafana/provisioning/alerting/asus-email-contact.yml` provisions Email while the operator-observed live Grafana point contains Email+Telegram | **OPEN** — no credentials or recipient IDs changed; needs separate safe provisioning and reload acceptance |
| A-08 | [Issue #229](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/229) original branch-cleanup inventory lists 119 remote branches; the 2026-10-13 GitHub branch listing has **14** after operator cleanup | **Metadata follow-up only**; do not delete more refs under the prior stop decision |
| A-09 | [Issue #194](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/194) points to an absent `docs/benchmarks/tuf-ax5400-vs-rt-be88u-benchmark-plan.md` on main, while PR #195 holds the unmerged draft | **Open benchmark methodology**; remove false main-path implication; no new hardware order |
| A-10 | [Issue #159](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/159) references the branch of now-merged PR #228 and preserves retired RT-BE88U candidate | **Historical**; retarget current decision link; do not silently reactivate migration |
| A-11 | PR #198 overlaps current `docs/worklog/2026-10-08.md`; old draft/interim status cannot replace current final record | **Retain as draft for selective reconciliation**: preserve unique dated Fedora Wi-Fi/RouterCloud observations but do not overwrite the updated final acceptance narrative; no branch deletion |
| A-12 | PR #230 has unique dated Mermaid development notes, not part of main and not evidence of an active production diagram redesign | **Retain for review**; history must not be silently dropped |
| A-13 | PR #227 research remains draft and current; conflicting design assumptions `NET_NS` / direct sidecar bypass not resolved by CI | **Keep draft / no deploy** |

## Related GitHub metadata reconciled on 2026-10-13

- [#159](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/159) now links directly to the merged strategy PR #228 and canonical platform decision on `main`; the historical RT-BE88U research content remains intact.
- [#178](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/178) stays **closed** with a current bounded acceptance notice before its dated historical phase body.
- [#194](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/194) now explicitly distinguishes the unmerged benchmarking draft PR #195 from a published file and the cancelled RT-BE88U hardware plan.
- [#229](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/229) now places the original **119-branch snapshot** in historical context and records the **14-branch** read-only observation before additional audit branches. Branch deletion remains **paused** at operator request.
- PRs [#195](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/195), [#198](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/198), and [#230](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/230) have explanatory review notices. **#198 was returned to DRAFT** to prevent unreviewed replacement of the final 2026-10-08 worklog; its unique Wi-Fi/RouterCloud observations are preserved for a later reconciliation. All existing PR head commits/branches remain available.

## CI and accuracy boundary

`tests/test-doc-links.py` checks Markdown paths, and `tests/test-doc-language-policy.py` checks EN/PL index references; neither proves semantic/current-state consistency. The new narrow status tripwires complement those checks. All new edits are documentation/test/CI only, with no production DNS/firewall/firmware/monitoring modifications and no live failure injection.

**Follow-up:** #129 DR, #176 exit-node source policy, #212/#216 DNS continuity/secondary resolver, #214 independent cron detection, and source-vs-live Grafana notification provisioning remain separate workstreams. The presence of a green CI check does not close them.

## Retrospective disposition — 2026-10-13 (after this audit snapshot)

The PR/issue states in the 2026-10-13 table above reflect the **original read-only audit checkpoint** and are intentionally not rewritten. Since that snapshot: PRs [#227](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/227) and [#230](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/230) have been **merged**; #212 client DNS failover is **OPEN / PAUSED awaiting independent hardware** (no production acceptance). PR #198's unique Fedora/RouterCloud notes have been **recovered as an addendum on a subsequent documentation branch** without replacing the final 2026-10-08 worklog. The RT-BE88U-only draft PR #195 is superseded in *planning* by a reusable ASUS-vs-future-OPNsense methodology; no benchmark hardware or results are claimed. See the newer documentation PR for review/merge state. These status updates do not assert new runtime tests.
