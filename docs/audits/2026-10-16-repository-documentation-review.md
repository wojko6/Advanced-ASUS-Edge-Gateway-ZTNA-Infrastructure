# ASUS Edge Gateway — repository documentation consistency review (2026-10-16)

**Classification:** source/repository review and documentation-only reconciliation. **Baseline:** public `main` commit `968dbb0c90c79a9ccba05ffac6cc19a01466dd32` prior to this PR. This is **not a fresh production audit**, full re-execution of historical test evidence, or validation of pending local-only worktrees.

## Scope and method

- GitHub repository tree: **510 elements**, including **237 Markdown (`.md`) files** in the public repository baseline. Included root docs, current `docs/` guides, architecture, case studies, historical worklogs, `evidence/`, router and monitoring Markdown.
- Automated inspection of **859 standard inline Markdown relative links** across all 237 Markdown files against the baseline Git tree: **0 missing local file/directory targets detected**. This parser does **not** prove anchor/heading validity, reference-style/HTML links, link target contents, external HTTP links, PDF links, build output or GitHub blob branch availability. A link can be syntactically valid yet stale as a *claim*.
- Targeted substantive reading of canonical current-state sources: `README.md`, `PROJECT-STATUS.md`, `docs/roadmap.md`, `docs/documentation-model.md`, `docs/architecture.md`, `docs/architecture/boot-service-dependency-flow.md`, `docs/security.md`, `docs/operations.md`, the 2026-10-15 architecture v1.2 snapshot and public worklog index. Compared claims to dated public code/CI, [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235), [Draft #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245), and [#254](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/254); use operator-pasted lab results with explicit provenance.
- Archive/date policy: **do not rewrite** 2026-10-08, 2026-10-15 v1.2 architecture, historical evidence or PDFs to imply a fresh live state. Mainline source of truth is `PROJECT-STATUS.md` plus date-scoped primary evidence, not the most recent experimental branch.

## Findings / documentation corrections

| Finding | Correct current classification |
| --- | --- |
| `main` lacked a public 2026-10-16 worklog and latest lab checkpoint; canonical status/roadmap stopped at 2026-10-15 | Add dated worklog; update current status, overview, roadmap and index; no historical claim rewrite |
| User-controlled file origin and RouterCloud process privilege required differentiated treatment | Process UID/GID 0 with broad caps **operator-observed**; browser/origin and PrivDrop work **not production accepted** |
| Both SSD mount roots returned to `0777` after boot, while Oct 14 bounded DAC Stage 1 had passed at time of change | Document reboot persistence **failure**, not erase Oct 14 acceptance or generalize protected subtree modes |
| Native SSD trust v1 published in branch with successful CI; no file in current `main` | Link to branch; read-only C snapshot behavior; 15 original tests and operator-reported ARMv7 `12/12` separated; valid result `RC=2/HOLD`, never authorization |
| Draft #245 shell mode-repair and native trust helper v1 are different approaches | Neither installed or merged; do not silently route `post-mount` to native v1 |
| Quiescence and DIRFD labs passed scoped checks but no continuous namespace ownership or power-loss acceptance | Preserve explicit missing gates and conditional wording |
| Current architecture v1.2 and future Flint 4/OPNsense studies have dated/evidence boundaries | Preserve versioned artifacts, link to current delta and retain no-purchase/no-migration decision |
| Issue #254 is an idea after a real large-transfer failure, not RouterCloud product functionality | Keep it BACKLOG/RESEARCH without claiming resumable transfers work |
| Broad link inventory and scoped current-state reading provide different assurance levels | Record scan method, exclusions and results accurately; do not claim exhaustive semantic validation of every historical document |

## Files updated in this documentation-only proposal

- `PROJECT-STATUS.md`, `README.md`, `docs/roadmap.md`: latest 2026-10-16 scoped project state and remaining gates.
- `docs/security.md` and `docs/operations.md`: confirmed UID0 observation, SSD mount-root 0777/reset issue, lab/production separation, no generic installer or unauthorized chmod.
- `docs/architecture.md`, `docs/architecture/boot-service-dependency-flow.md`: current pointer and firmware mount-mode step without implying the candidate fix is live.
- `docs/worklog/README.md`, `docs/worklog/2026-10-16.md`: indexed dated public report.
- `docs/documentation-model.md`: reviewed date and evidence/source-of-truth link.
- This audit document.

No source code, JFFS hooks, firmware image, CID/UUID mapping, secret, production server setting, test fixture or on-router data is changed by this documentation branch.

## Follow-up verification / limitations

- Run repository validation workflow and confirm Markdown link integrity after the branch changes. A green repository validation workflow does not validate real ASUS state, browser behavior or implied security of external links.
- Keep [#235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) **OPEN / `DEPLOYMENT_GATE=HOLD`** until an approved production security acceptance. [Draft #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) remains separate.
- The published private `work-log-private` 2026-10-16 entry is intentionally not copied verbatim into the public repository; this public record is sanitized and evidence-scoped.
