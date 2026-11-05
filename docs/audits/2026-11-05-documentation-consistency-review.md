# 2026-11-05 — repository Markdown/navigation and scope-consistency review

> **Scope:** documentation-only, within existing Draft PR [#369](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/369); no separate issue or PR, no GitHub merge, no router/workstation runtime modifications. **This review does not certify entire historical content or production/security state.**

## Inventory and checks

- Inspected the **complete Git-tracked tree on `main`** as of this review: **699 entries** (**619 blobs / files**, **80 tree entries / directories**). The tree was not truncated.
- Fetched the Markdown documents for the initial PR-branch audit: **318 `.md` files on the base tree plus one new November 5 worklog = 319 files**. This additional audit note was created **after** that scan (therefore the completed PR now contains 320 Markdown documents). The original local-path check used the base tree plus the known PR worklog addition.
- Reviewed **1,425 inline relative Markdown link/image target occurrences** against tracked paths, after relative path normalization. **No missing target paths were found by this bounded check.**
- Also inspected the current entry-point and scope text in root `README.md`, `PROJECT-STATUS.md`, `CHANGELOG.md`, `docs/DOCUMENTATION-MAP.md`, English/Polish `START-HERE.md`, `docs/pl/README.md`, `docs/testing.md`, `docs/roadmap.md`, the November 3 GUI scope note, worklog chronology, and selected earlier audits/agent laboratory notes.
- Following the documentation additions, the **13 files changed in PR #369** were fetched again and their **576 inline relative target occurrences** checked against the base tracked tree plus the two added PR files; the only initial pattern matches without targets were two literal Markdown syntax examples *in this audit note*, which were removed before the final rerun.
- The 2026-11-03 PR inventory (22 Drafts then), older 2026-10/11 dated evidence, and state assertions in old worklogs are **point-in-time snapshots**, **not** a newly verified live count. Only the existing **#369 OPEN/DRAFT** state was explicitly confirmed for this addendum.

### Link-scanner limits

The local-path scan used an intentionally narrow Markdown pattern for inline Markdown links and images (not reference-style definitions) outside fenced code, stripped URL fragments/query strings and checked file/directory existence in the tree. It **did not** validate heading anchors, reference-style or dynamically generated links, URL escapes outside the supported pattern, external URLs, or whether the destination content supports the source claim. Passing this check is **not** a complete Markdown parser or an archive-level historical security audit.

## Findings and reconciliations

| Item | Finding | Documentation reconciliation within #369 |
| --- | --- | --- |
| Current-facing GUI navigation | Root/status/changelog/index still stopped at the November 3 v0.10.1 checkpoint while a separate November 5 source record described v0.12.29 | Add clearly dated, operator-reported November 5 pointers to current-facing navigation while retaining the November 3 historical facts |
| GUI versus Local AI Agent C.63/C.64 | The supervised KDE GUI can perform selected user-session actions; C.63/C.64 research agents declare `MODEL_ACTION_AUTHORITY=NONE` | Preserve separate privilege/approval boundaries; no conflation of source/lab acceptance with production permission |
| KWin/WindowsRunner | Empty-query search match counts, grouped opaque IDs and icon heuristics were sometimes misconstrued as counts or identities of windows | Explicitly say **NOT** verified windows/processes; no raw titles/IDs in user-facing reports, no window control |
| DNS / HTTPS | `ip route` is insufficient to establish Internet connectivity; fixed DNS and public HTTPS tests are bounded | Scope positive results to tested targets/time, note network-metadata exposure to external test providers |
| Loki HTTP readiness | Brief `INGESTER_NOT_READY` 503 samples occurred while /services reported 16 components Running; later 200 samples | Preserve **intermittent readiness, cause unproven, no reboot/config fix**; active systemd ≠ ready endpoint |
| Grafana manifest watcher | Repeated empty-discovery warnings and no loaded manifests coexist with operator-tested existing dashboard search | Keep component-specific warning and separate dashboard UI acceptance; neither infer DNS failure nor full Grafana health |
| Execution labels and test evidence | A command's exit code and sampled health estimate are different; 338/338 tests are creator-reported offline | Retain distinct labels and show screenshot/operator acceptance ≠ independent CI/security certification |
| Public/private source boundaries | Local Python GUI files, raw logs, identifying window text and sensitive workstation data are outside this public engineering repository | Do not add sources/private evidence as a side effect of documentation maintenance |

## Changes staged in the existing PR

Nov 5 [sanitized worklog](../worklog/2026-11-05.md) and [timeline](../worklog/README.md), current-facing [README](../../README.md), [PROJECT-STATUS](../../PROJECT-STATUS.md), [CHANGELOG](../../CHANGELOG.md), [documentation map](../DOCUMENTATION-MAP.md), [local GUI authority boundary](../design/local-qwen-supervised-gui-2026-11-03.md), [testing](../testing.md), [roadmap](../roadmap.md), English/Polish entry guides, Polish documentation index, and this scoped audit.

## Non-goals and pending review

- **No** merges, production upgrades, router/DNS/firewall writes, systemd changes, automatic Qwen tool execution beyond the reported local allowlist, or CI/security certification.
- Public redaction and evidence wording require human review before merging **Draft PR #369**.
- Unresolved: exact Loki ingester readiness cause and Grafana manifest watcher configuration/semantics; no unapproved remediation.
- Historical documents retain their original as-of date/status; this addendum does not replace them or import the private daily log.

**Final gate: `DEPLOYMENT_GATE=HOLD`.**
