# Open pull request inventory and safe review sequence — 2026-11-03

**Status:** dated GitHub inventory / planning note, **not** merge authorization, CI security certification, live ASUS acceptance or production deployment evidence. Snapshot of **22 OPEN/DRAFT PRs** in [the active engineering repository](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pulls), reviewed **2026-11-03**. Re-check GitHub status whenever a branch or `main` changes.

## Summary and counting rules

| Dimension | Observed count | Interpretation |
| --- | ---: | --- |
| Open / Draft | **22 / 22** | None was marked Ready for review |
| HEAD check suites | **22 PR heads with completed green checks** in the preceding same-day CI audit | Green CI does **not** verify source review, privacy, branch integration or deployment |
| `mergeable_state=clean` | **9** | GitHub sees no current base conflict, **not** an approval |
| `mergeable_state=behind` | **8** | No current conflict, but branch is behind its target base |
| `mergeable_state=dirty` | **5** | Actual merge conflicts with current base; resolve in a controlled branch-specific review |

**Conflict set:** [#270](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/270), [#338](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/338), [#340](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/340), [#343](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/343) and [#346](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/346). These are `dirty` in the GitHub merge API, not just stale status labels. The inventory is a **point-in-time snapshot**; it does not assert that all CI checks will remain green after rebases or merges.

## PR-by-PR decision register

Action labels: **REVIEW** = read human diff/evidence before any merge; **RECONCILE** = compare scope and resolve overlap/ancestry; **HOLD** = intentionally not ready for production or feature integration. All entries remain **Draft** in this snapshot.

| PR | Workstream and exact scope | GitHub merge state | Next safe action |
| --- | --- | --- | --- |
| [#364](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/364) | Sanitized 30/31 Oct + 3 Nov logs, Qwen UI boundary, document navigation | clean | **REVIEW FIRST:** public-redaction, date/citation and Markdown diff, rerun exact-head CI; docs-only merge only after explicit owner decision |
| [#362](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/362) | Nov 2 Unbound AAAA/DNSSEC recovery and C.64 Codex audit addendum | clean | REVIEW evidence, check duplication against dated Nov 2 record; docs-only review after #364 |
| [#361](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/361) | Issue #287 J25–J27 timer and ARMv7 lifetime evidence, dated docs | clean | REVIEW source/test scope; keep Issue #287 **HOLD**; reconcile with any later Nov 2 publications |
| [#346](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/346) | C.62 incident/evidence docs and Oct 31 public timeline | **dirty** | **RECONCILE:** compare unique technical evidence against #364's sanitized Oct 31 summary; preserve unique facts; no forced merge |
| [#340](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/340) | Original Oct 29 HCC worklog correction | **dirty** | RECONCILE historical-only details with already accepted Oct 29 record and updated worklog index |
| [#270](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/270) | Issue #235 Oct 19–20 startup-script trust evidence, many historical commits | **dirty** | RECONCILE only unique source-scoped evidence; independent security/privacy audit and privileged trust gate before any implementation |
| [#353](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/353) | C.63 unified synthetic-only diagnostic CLI | behind | REVIEW new CLI contract as independent C.64 companion, no executable host authority by inference |
| [#354](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/354) | C.64.0 synthetic VictoriaMetrics envelope | behind | C.64 candidate **base**; source review and offline checks before stacked PRs |
| [#355](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/355) | C.64.1 mocked VM transport | clean, **base=#354 branch** | Review after #354, preserve parentage; compare C.64.1 alternate #356 |
| [#356](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/356) | Separate C.64.1 fake loopback HTTP lab | behind | Review as **parallel** test/design, not silently treated as ancestor of #355 |
| [#357](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/357) | Separate C.64.2 manual read-only operator gate | behind | Independent review of manual approval and no-network boundary; not automatically identical to stacked #358 |
| [#358](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/358) | C.64.2 no-HTTP listener identity preflight | clean, **base=#355 branch** | Review only after #354→#355; no live HTTP implicit permission |
| [#359](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/359) | C.64.3 synthetic independent-source/operator gate | clean, **base=#358 branch** | Review last in #354→#355→#358→#359 stack; preserve `HOLD` |
| [#343](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/343) | Historical C.57–C.59.1 source and Oct 30 dated log | **dirty** | RECONCILE against already merged C.63; avoid duplicate/outdated code and overwrite of #364's curated Oct 30 timeline |
| [#344](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/344) | C.60/C.60.1 strict completion contract | clean, **base=#343 branch** | Review after resolving ancestor #343; no direct merge to `main` by assumption |
| [#345](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/345) | C.61 synthetic multi-incident/historical bridge | clean, **base=#344 branch** | Review after #343→#344; avoid duplicate Oct 31 log and stale tests |
| [#321](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/321) | One-series fixed-window raw VM history preflight, independently operator-tested | behind | Compare with already merged seven-series HCC source; merge only unique retained value after source review |
| [#338](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/338) | HCC V0.14.5 A–K synthetic spool/replay, large lab diff | **dirty** | **HIGH REVIEW COST**: split/test retained source scope, preserve FAIL history; separate static/SELinux/privacy sign-off |
| [#342](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/342) | HCC V0.14.6 A–C disposable import/journal envelope | clean, **base=#338 branch** | Review only after #338 ancestry and HCC scope resolution; no production reader/writer |
| [#245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) | Issue #235 privileged SSD post-mount candidate | behind | **SECURITY HOLD:** privileged writes / boot hooks require separate trust/race/rollback review and operator authorization |
| [#226](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/226) | RouterCloud Metro File View UX isolated preview | behind | Product/UX review and relevant isolated tests; do not assume production-enabled File View |
| [#202](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/202) | Legacy Unbound ARMv7 1.26.1-1 recovery build recipe | behind | **Historical compatibility review:** deployed Unbound 1.26.2 does not mean old 1.26.1 recipe is a current upgrade candidate |

## Dependency structure and overlap

These are actual GitHub base branches, **not** suggested invented dependencies:

- C.57–C.61 historical agent: **#343 → #344 → #345**. Conflict is at parent #343; child `clean` does **not** remove it.
- HCC: **#338 → #342**. Parent #338 is `dirty`; do not individually promote child #342 to an independent `main` PR.
- C.64 stacked: **#354 → #355 → #358 → #359**. The #356 fake HTTP and #357 operator-gate branches target `main` separately. They need an integration comparison; do not double-merge overlapping functionality by title.
- Documentation overlap: #364 adds curated `docs/worklog/2026-10-30.md` and `2026-10-31.md` plus the index; #343, #344, #345, #338, #342, #346 and #340 also touch those date/index paths. That is not merely a file path conflict — **evidence scope and authorship** differ.
- #364, #362 and #361 currently target `main` as standalone clean documentation drafts. #362 adds a separate Nov 2 addendum while #361 updates the Nov 2 main worklog; inspect both for inconsistent claims even if Git sees no overlapping filename.

## Proposed review order (not an unattended merge plan)

1. **P0: close documentation quality gate:** inspect #364 branch contents and privacy, re-check latest CI and link targets; operator decides if/when to mark Ready and merge. Then inspect #362 and #361 individually against updated `main`.
2. **P1: reconcile historic docs without rewriting evidence:** #340, #346, #270. Resolve branches manually or extract only unique materials into a new docs-only proposal; do **not** discard conflicting evidence automatically.
3. **P2: agent C.64 source provenance/security:** independent review #353, #354; follow stacked #355→#358→#359. Separately compare #356 and #357 and explicitly decide whether they are complementary, replaceable, or remain research.
4. **P3: old agent and HCC source debt:** #343→#344→#345 and #338→#342; plus #321. Refactor/rebase only after documenting original test scopes and any unsafe historical code, repeat CI at **new exact heads**.
5. **P4: dormant privileged/UX/build candidates:** review #245 and #202 under security and current-version compatibility; #226 under isolated product scope. Keep Draft/HOLD until independent approval.

## Safety and review checklist

- No source merges, PR closures, branch deletions, retargeting, rewrite/force-push, live service changes or production rollout were performed in this triage.
- Before merge: verify **exact current head SHA**, target base, integration diff, branch-specific check runs, privacy review and owner approval. A passing 2026-11-03 CI result expires as evidence for a changed commit.
- For HCC and autonomous agent, **`DEPLOYMENT_GATE=HOLD`** remains. The separate workstation Qwen GUI has its own limited user-session allowlist and is not the C.63/C.64 agent.
- `dirty` requires intentional conflict resolution; `behind` is a signal to review rebase/merge-base freshness, not a blanket authorization to update every branch.
- Source merge ≠ tested deploy ≠ verified backup/restore ≠ permission to access real telemetry or modify ASUS.

[Documentation map](../DOCUMENTATION-MAP.md) · [Public worklog 2026-11-03](../worklog/2026-11-03.md) · [Documentation consistency audit](2026-11-03-documentation-review.md)
