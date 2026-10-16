# ASUS Edge Gateway — Polish documentation and repository current-state review (2026-10-16)

**Classification:** documentation/source consistency review, **NOT a production audit**.  
**Baseline:** public `main` at `032b04f11bc7c0793d0e9345127b7ad036d00870` (merged PR #255).  
**Status:** proposed documentation-only changes; [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) still OPEN; post-mount [Draft PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) remains separate and uninstalled; `DEPLOYMENT_GATE=HOLD`.

## Scope and methodology

1. Fetched the complete GitHub recursive `main` tree: **512 tree entries**, **445 blob files**, including **239 Markdown documents** (the previous dated audit covered 237); GitHub reported `truncated=false`. `docs/pl/` itself contains **two Markdown files**, but Polish operator guides also reside at existing stable paths under `docs/`.
2. Checked the current versioned project status and guidance against `README.md`, `PROJECT-STATUS.md`, `docs/documentation-model.md`, `docs/language-policy.md`, `docs/pl/README.md`, `docs/pl/busybox-armv7.md`, `docs/custom-busybox-armv7.md`, `docs/network-design.md`, `docs/architecture.md`, the v1.2 production architecture and conditional Flint 4 design, `docs/architecture/` boot/DNS/topology/availability/platform documentation, `docs/security.md`, `docs/operations.md`, `docs/roadmap.md`, `docs/requirements.md`, `docs/testing.md`, `docs/compatibility.md`, `monitoring/README.md`, `CHANGELOG.md`, relevant DR/bare-metal/Pi-hole restore documents and the dated 2026-10-16 worklog/audit.
3. Reviewed `tests/test-doc-links.py` and `tests/test-doc-language-policy.py`. The former validates repository-local Markdown **target files/paths**, not heading anchors, external URLs or meaning; the latter validates the Polish index/required guide references, not quality of translation. The 2026-10-16 earlier repository audit recorded **859 checked local inline links across 237 Markdown files**, no missing targets. Re-run current CI after this change; **do not present that earlier scan as a fresh scan of all 239 files**.
4. Reviewed the role of the remaining dated `evidence/`, `docs/worklog/` and case studies through the full tree and current index/source-of-truth hierarchy. **Not every line of all 239 documents was re-read or semantically certified.** Original dated test evidence is retained instead of silently reclassified.
5. Cross-checked references to open Issue #235/Draft #245, the 2026-10-16 ARMv7/QEMU research branch, #129 DR and #212 pause, #254 transfer backlog, and the v1.2 architecture. No physical ASUS connection, fresh device telemetry, on-router test, live Dufs/PrivDrop deployment or modification occurred.

## Confirmed corrections

| File | Finding | Documentation-only change |
| --- | --- | --- |
| `docs/pl/README.md` | Polish index last updated 2026-10-09 and did not navigate to latest Issue #235 research, v1.2 architecture, #212 pause, #254 backlog and DR limits | Add dated 2026-10-16 references and explicit current-vs-proposed boundaries |
| `docs/pl/busybox-armv7.md` | Claimed optional BusyBox reboot persistence still unverified despite [2026-10-10 operator-reported read-only gate](../../evidence/2026-10-10/issue-129-custom-busybox-reboot-persistence.md) | Mark **existing-router latest-reboot persistence PASS**; keep empty-router restore and actual removal/rollback **NOT TESTED** |
| `docs/pl/busybox-armv7.md`, `docs/custom-busybox-armv7.md` | Pasted guard examples included bare `exit 1` that could close an interactive SSH terminal; unguarded later checks could mask failures | Wrap examples in subshells and enable `set -e` **inside subshells only**, preserving STOP on unexpected failures |
| `docs/documentation-model.md` | Still called historical architecture PDF v1.1 the latest; 2026-10-08 overview ambiguously described as current-derived | Point to dated v1.2 Markdown/PDF, explicitly classify v1.1 and v1.0/2026-10-08 snapshots as historical |
| `docs/requirements.md` | F-08–F-10 were split from their four-column acceptance table by a blank line; N-05/N-06 had four data cells under three-column header | Restore continuous table, normalize N-05/N-06 and record #235 as not production-accepted (N-07) |
| `docs/network-design.md` | Latest dated network-design index had only 2026-10-15 #235 link | Add 2026-10-16 lab worklog link while preserving 2026-10-15 live findings and v1.2 architecture |

## Security and production truth reconciled

- **SSD/JFFS:** both physical SSD mount roots were observed as `0777` after the 2026-10-15 boot, despite the Oct 14 scoped Stage 1 hardening result. Source for the installed GNUton release contains a mount-time `chmod(mountpoint, 0777)`; no safe persistence fix is production-accepted. Draft #245 is shell post-mount **research only**. Native SSD Trust v1 is a **separate read-only** C prototype: synthetic `RC=2/HOLD` or `RC=3/REJECT`, local ARMv7/QEMU 12/12 negative matrix PASS, **no RC=0, no UUID binding, no fchmod, no router deployment**.
- **RouterCloud least privilege:** most recent dated sampling in project status found the live Dufs process as UID 0 with broad capabilities. PrivDrop and asset-origin protections remain laboratory/review work, not a claim of installed production mitigations. Stable DUFS-only policy retained.
- **Disaster recovery #129:** partial archives, reboot of existing router and isolated ARMv7 65-package `opkg` rebuilding do **not** constitute a successful empty-router/full-SSD restoration; planned DR guide remains conditional. Optional BusyBox latest-reboot persistence is independently PASS on the existing router, but its CORE backup coverage, full restoration and removal/rollback are still open.
- **DNS #212:** DNS Guard v3.2 is accepted for the router-*system* resolver within dated testing limits. Independent LAN-client DNS failover is **PAUSED**, and two co-resident DNS frontends sharing Unbound are not high availability. No extra router/kernel deployment implied.
- **Architecture:** current gateway is still the ASUS TUF-AX5400; v1.2 is a dated 2026-10-15 production *snapshot*, not a new on-router acceptance. GL.iNet Flint 4 and OPNsense are research/conditional future alternatives, with no approved purchase or migration and no dedicated VLAN segmentation currently deployed.
- **Monitoring:** 15 Grafana rules and the dated Gmail/Telegram synthetic E2E evidence are distinct from individual per-rule delivery assurance. Source/live provisioning parity, repeatability and grouping have their own outstanding gates. A published YAML/rule does not by itself prove notification delivery.
- **Transfers #254:** reliable, resumable SHA-256-verified RouterCloud transfer is BACKLOG, not a deployed or benchmarked feature.

## Deliberately not rewritten

- Dated 2026-09 and 2026-10 case studies, original output/evidence and previous architecture PDFs: historical provenance takes precedence over making every date read `2026-10-16`.
- Stable operator paths `docs/deployment-pl.md`, `docs/router-bare-metal-recovery-pl.md` and printer `*-pl.md` are not moved; the Polish index links to them. No parallel PL technical source of truth is created.
- Firmware scripts, JFFS post-mount, production ownership, SSD root modes, DNS Guard, RouterCloud service/DUFS and secrets are outside this documentation PR.
- Experimental native SSD C code/documentation on its separate branch is not merged into `main` by a Polish-docs update.

## Validation and remaining scope

- The repository CI should run `tests/test-doc-links.py`, `tests/test-doc-language-policy.py`, standard static/recovery/evidence validation and the existing ARMv7 build checks against this PR HEAD. Passing those tests means **source/doc structure validated only**; no live deployment proof.
- Checks of **external web links, Markdown heading-anchor correctness, full translation equivalence, every historical statement and the behavior of the actual router** are not established by these static checks. Treat any new operational instructions that affect JFFS/SSD/swap/DNS as STOP until independently reviewed against current production state.
- [Previous 2026-10-16 repository audit](2026-10-16-repository-documentation-review.md) retains its own method and baseline; this is a supplemental targeted semantic reconciliation after merged PR #255, not a replacement for its original snapshot.
