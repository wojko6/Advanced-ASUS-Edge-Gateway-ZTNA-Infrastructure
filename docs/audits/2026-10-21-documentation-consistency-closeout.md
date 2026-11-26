# Repository documentation consistency and day-close review — 2026-10-21

**Classification:** documentation-only review, evidence-bounded. **Review branch:** `docs/fedora-victoriametrics-1.154.1-20261021` / [Draft PR #274](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/274). Historical evidence is not rewritten into current deployment assertions. No tests on a router, service changes, package updates, file-mode changes or merges were triggered by this review.

## What was checked

- Enumerated the full GitHub tree of the review branch (not a live filesystem): **256 Markdown files at the time of the link audit**, comprising **114 general/current documents** and **142 dated worklogs, historical evidence and audit entries**. The newly written evidence document was included; this audit report was created afterwards, so the final count increases by one.
- Read each of these 256 Markdown bodies through the GitHub connector. A basic static relative-link check compared inline Markdown links and image targets with repository-tree paths, after removing anchors and normalizing relative parent segments: **no unresolved file paths found in the checked form**.
- Inspected the 114 general/current Markdown documents for explicit old-version-as-current wording, and reviewed key security, architecture, status, worklog-index and evidence-index passages for relevant 21 October updates. This is not a semantic certification of every paragraph or externally hosted URL.
- Verified current public documents already separate stable production ASUS, hypothetical Flint 4/OPNsense architectures, Fedora update check-only state, open Issue #235, and unmerged Draft PR #245.
- Verified the **private** worklog policy separately against `wojko6/work-log-private`: current `README.md`, `INDEKS.md` and `worklog-guidelines/WORKLOG_RULES.md` require **Polish for all new private prose**, including `ideas/` and `hardware/`. The private language audit records that **34 older daily reports** remain largely English as preserved evidence; the Polish index/guide is not a full translation.

## Specific gaps found and documentation corrections

| Finding | Correction / retained boundary |
| --- | --- |
| Public Oct 21 daily worklog contained only a brief #235 laboratory checkpoint | Extended existing date under Draft PR #274 with the real Firefox lab results, authorized production **read-only** V2.30R2 metadata, Fedora sealed-config/nonroot DUFS results, explicit **V2.30W NOT RUN** |
| No dated public record of the 21 October #235 read-only privilege and rootless FD results | Added [bounded evidence](../../evidence/2026-10-21/issue235-readonly-privileges-and-fedora-rootless-lab.md) with operator provenance and unresolved security gates |
| Security model did not yet incorporate production UID/capabilities and SSD-root permission sampling | Added a dated [RouterCloud security update](../security.md) without turning a laboratory finding into production exploit or remediation acceptance |
| Trust-boundary diagram still said the current router runs Tailscale 1.103.375 | Updated [high-level trust boundaries](../architecture/high-level-trust-boundaries.md) to the separately operator-confirmed **1.104.2** live runtime; cold reboot/soak not claimed |
| Oct 21 dated #235 evidence was not linked in public indexes | Updated [evidence timeline](../../evidence/README.md) and [worklog chronology](../worklog/README.md) |
| Separate Tailscale documentation Draft PR #273 exposed an exact dated private rollback path | Redacted the deployment-specific location in PR #273 `PROJECT-STATUS.md` and the associated dated evidence file; retained the fact of a private rollback snapshot and technical validation |
| Private daily Oct 21 #235 summary omitted V2.30M–V, ASUS R2 and the last not-run test | Extended the **existing** `work-log-private/daily/2026/10/2026-10-21.md` on private `main`, in **Polish**, with bounded results and **V2.30W NOT_RUN** |

## Open documentation/integration dependencies — do not silently mark complete

1. **Separate document PRs:** [#273](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/273) contains the current Tailscale 1.104.2 changes to `PROJECT-STATUS.md` and compatibility/evidence; [#274](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/274) contains the Oct 21 combined public worklog and this additional #235 documentary evidence; [#275](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/275) holds the independent Fedora router-management Wi-Fi incident case study. **No merge was performed during this closeout.**
2. **Shared index reconciliation:** both #273 and #274 touch `evidence/README.md`; merge these histories without dropping either dated entry. [Draft PR #268](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/268) and [Draft PR #272](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/272) contain the Oct 19 and Oct 20 worklogs and may conflict in `docs/worklog/README.md`. The apparent date gap on `main` is a **pending PR publication**, not evidence of an idle day.
3. **Private language archive:** the 34 historical reports are not fully translated. Preserve original historical output and only translate through a clearly marked, separately reviewed editorial revision. Current nondated private prose and the Oct 19–21 daily reports are Polish.
4. **Evidence limits:** V2.30P/P1 **SKIP**, V2.30W **NOT RUN**, ARMv7 nonroot DUFS **NOT TESTED**, publisher authority **NOT PROVEN**. Avoid presenting them as passed security gates.
5. **Source/code drift:** the review covers the available GitHub Markdown tree, not the user's uncommitted local Fedora worktrees, unreviewed draft branches other than referenced PRs, or the complete current private router runtime. A path check cannot validate local link fragments, external HTTP reachability, embedded media, executable commands or substantive completeness of all historical claims.
6. **Security/production:** Issue #235 remains OPEN; Draft #245 has no deployment approval and remains uninstalled; no ASUS SSD, JFFS, DUFS, firewall, DNS or Tailscale changes were made **as part of this documentation closeout**. Separately operator-approved Tailscale 1.104.2 and Fedora VictoriaMetrics 1.154.1 updates earlier on this date remain reported under their own evidence.

## Acceptance scope

- **PASS:** 256/256 Markdown files received for bounded GitHub-based structural/relative-file link analysis before this report was added; **0 unresolved links detected in the supported static inline-link pattern**; current high-priority docs supplemented and existing daily entries updated without duplicate date files.
- **NOT CLAIMED:** exhaustive linguistic translation of archived private records, verification of all remote URLs/heading anchors, formal source/link CI, current production rootless DUFS acceptance, PR merge conflict resolution, or live-router changes.
- **FINAL:** **documentation-only closeout**, `ISSUE_235=OPEN`, `V2.30W=NOT_RUN`, `DEPLOYMENT_GATE=HOLD`.
