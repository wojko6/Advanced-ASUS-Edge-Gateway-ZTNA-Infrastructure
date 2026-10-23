# Repository-wide documentation consistency review — 2026-10-23

> **Publication boundary:** public technical documentation, English narrative. **Review target:** documentation-only [Draft PR #295](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/295) on top of the 2026-10-23 public `main` snapshot. No router/Fedora runtime commands were executed by this documentation audit; no code, permissions, configuration, backups or services were changed.

## Coverage and method

- Enumerated GitHub's complete, non-truncated recursive tree of public `main`: **472 tracked files, including 264 Markdown**. The PR review head before this audit contained **266 Markdown** (the two new 2026-10-23 documentation files) and includes all pre-existing content.
- Fetched and inspected **all 266 Markdown file bodies** from that review head, grouped as **124 general/current documentation files, 38 worklog files and 104 evidence files**.
- Parsed **1,102 relative inline Markdown links/image paths** with a conservative inline-link matcher; removed fragments and query strings; normalized `..` parent segments and compared to the repository tree, accepting actual files and present directories. **No missing local target path was found by this check.** The audit does *not* exhaustively validate reference-style links, GitHub-generated heading fragments, links within code blocks, outside websites, private repos, link redirects or historical external availability.
- Checked current/reference-version claims in general/current documents and selected important cross-document statuses. Compared primary issue statuses directly with GitHub on the review date: #129, #176, #212, #235, #278 and #287 remain OPEN; #276 is CLOSED after bounded code remediation. The paused scheduling of #212 remains a project decision, not an issue closure.
- Cross-checked the dated worklog-index links against actual dated `docs/worklog/YYYY-MM-DD.md` filenames. **37 dated worklogs existed**, but only **36 were indexed** before this patch.
- The private Polish daily journal was read only to check alignment of the 2026-10-23 scopes (#287 and Unbound); it was not copied into this public record. Historical evidence is retained as dated source material and was **not** globally rewritten into today's state.

## Findings and corrections in this PR

| Severity | Finding | Correction |
| --- | --- | --- |
| Navigation gap | `docs/worklog/README.md` on `main` ends on Oct 22; the Oct 23 entry is only in unmerged PR #295. | Keep the 2026-10-23 entry and its direct index link in PR #295; update `main` **by reviewing and merging this PR**, not by creating a parallel worklog. |
| Navigation gap | Worklog `docs/worklog/2026-09-30.md` existed but had no entry in the index (37 files, 36 indexed). | Added Sep 30 with the source-supported router-management split-DNS/HTTPS and Personal Cloud #136 topics, restoring 37/37 index coverage. |
| Stale current-state wording | `docs/architecture/tailscale-management-exit-node-flow.md` called 1.103.375 the current live Tailscale runtime. | Updated to the documented bounded Oct 21 1.104.2 live deployment; 1.103.375 remains historical; no cold-reboot acceptance inferred. |
| Stale current-state wording | `docs/roadmap.md` used `Current live Tailscale: 1.103.375` under its older Oct 10 snapshot. | Explicitly labeled the 10 Oct record historical and cross-linked the superseding 1.104.2 evidence from 21 Oct. |
| Inaccurate management-path generalization | Current Tailscale management flow said router SSH was disabled, while Oct 23 read-only operator access used ASUS SSH TCP/1122 from Fedora. | Distinguished the documented HTTPS Tailscale management DNAT from separately observed authorized SSH; no unverified WAN/tailnet SSH exposure claim. |
| Missing current roadmap release reference | `docs/roadmap.md` did not summarize the pending Unbound 1.26.2 maintenance staging. | Added a prominent 2026-10-23 Fedora-only checkpoint, rollback limits and `DEPLOYMENT_GATE=HOLD`; linked the detailed release-readiness report. |

## Key current-state contracts retained

1. **Unbound:** 1.26.1-1 remains on ASUS; 1.26.2-1 and rollback packages are **staged only on Fedora**. No router staging, package install, or service restart. QEMU forwarding tests cannot establish independent validation. Manager `S61unbound` is overwritten by `opkg` on upgrade **and** downgrade. DNS Guard continuity during maintenance unproven.
2. **Disaster recovery:** [Issue #276](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/276) closed only for the specific `post-mount` rollback-code defect. [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) remains open; no clean-device restoration or live `restore.sh --apply` was implied.
3. **Security research:** [#235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235), [#278](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/278), [#287](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/287), Draft #245 and separate RouterCloud/DUFS tests retain independent acceptance boundaries.
4. **Platform/networking:** TUF-AX5400 remains the reference router, Flint 4 is a conditional non-purchased plan, and [#212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212) remains open but paused pending independent suitable hardware. No automatic independent DNS continuity is advertised.
5. **Status language:** laboratory PASS, read-only live observation, staged candidate, merged documentation, and successfully deployed production state are **distinct**. A documentation PR must not change live runtime status simply because CI passes.
6. **Private/public separation:** no sensitive backup contents, full config, trust-anchor key bytes, private credentials or raw private worklog copied into public GitHub.

## Validation and limits

- The pre-audit PR #295 revision ran GitHub Actions *Validation suite* successfully with four passing jobs. New corrections in this audit require their own **fresh CI run** before merge.
- The entire relative-link check is a *static path-existence pass*, not full semantic certification of all 266 source documents. Historic sources may contain intentionally dated values. External references and in-document anchors were not revalidated.
- No automatic documentation merge should be mistaken for router service deployment. **ASUS production `DEPLOYMENT_GATE=HOLD`.**

## Review follow-up

Review the current PR diff, check that the date index covers all dated worklogs including **2026-09-30** and **2026-10-23**, await a successful CI conclusion on the final head and merge *documentation only* if approved. A maintenance decision for Unbound on October 24 is separate and requires explicit operator authorization, including acceptance of a possible DNS interruption.

**Review result:** local navigation/file-presence PASS within parser scope; three current-state text problems corrected; two index/coverage gaps corrected; no new production acceptance.
