# ASUS Edge Gateway — complete-archive documentation review (2026-10-16)

**Status:** DOCUMENTATION AUDIT / SOURCE-ONLY. **Archive baseline:** `main` `1e293bcc1f6818280e15585c8f4ffdda99de8b29` (after merged PR #256). **Production:** untouched; [Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) OPEN, [PR #245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) DRAFT/UNMERGED; `DEPLOYMENT_GATE=HOLD`.

## Method and evidence limitations

- Inspected user-provided complete public-main ZIP: **446 files**, **240 Markdown documents (34,685 lines / about 246,845 whitespace-delimited words)**, **4 PDFs (64 pages)**, **1 dated plain-text evidence report**. Four HTML files are frontend source, not counted among the 245 documentation artifacts.
- Each Markdown file was individually indexed by path, scope, heading structure and evidence role; the complete text was processed for fenced-code/table/link structure. The 2026-10-16 local full-archive test returned **PASS** for `python3 tests/test-doc-links.py` and `python3 tests/test-doc-language-policy.py`. The structural scan detected **no unbalanced fences, table-width mismatches or missing local linked files**; it extracted **1,142 inline/reference local-link candidates** before filtering.
- All four PDF publications were text-extracted and their entire page contact sheets examined. **No text outside page boundaries** was found; the oldest historical 2026-10-08 PDF has many tiny-font passages, so improve legibility in future publications without rewriting this historic release.
- Targeted manual semantic comparison focused on current status, router safety/DR, DNS ownership, RouterCloud security, architecture versions, operator-facing procedures, the Polish guides and historical/production evidence boundaries. The entire corpus is **not independently certified sentence-by-sentence**: a file-level registry and automated checks cannot replace live service tests or exhaustive human re-execution of all dated evidence.
- The previously merged [2026-10-16 repository documentation review](2026-10-16-repository-documentation-review.md) and [Polish reconciliation](2026-10-16-polish-docs-and-current-state-reconciliation.md) retain their original baselines, as do historical worklogs and PDFs.

## Confirmed corrections in this PR

| ID | Finding | Outcome |
| --- | --- | --- |
| A-01 | `docs/routercloud-home-ajax-production-preflight-2026-10-12.md` opens by claiming no production activation and [PR #224](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/224) still DRAFT, although the same file later documents operator-reported activation/no-reload acceptance and GitHub marks the PR MERGED (2026-10-12). | Prominent **COMPLETED / HISTORICAL** label; initial “NOT DEPLOYED” explicitly scoped to its past checkpoint; **STOP** notice against replaying old mutating deployment/restart/rollback commands. Historical events preserved. |
| A-02 | `docs/asus-webui-polish-localization.md` labels production validation pending without distinguishing the original 2026-09-29 live-validated overlay, final 2026-10-02 isolated candidate and [PR #179](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/179) source merge (2026-10-06). | Separates these evidence levels; a source merge **does not prove** final candidate deployment or reboot persistence. |
| A-03 | Version “2.0” exists on the 2026-10-08 historical architecture cover and on the distinct 2026-10-15 Flint 4 future-design PDF; current production reference PDF is dated 2026-10-15 **v1.2**. | `docs/documentation-model.md` now requires publication **date, scope, and filename**, not simple cross-document numeric version ordering. |

## Cross-domain safety conclusion

- TUF-AX5400 remains the current WAN gateway; RT-BE88U migration was cancelled, while Flint 4 and OPNsense are conditional/unapproved future designs.
- DNS Guard v3.2 is accepted only as a dated **router system DNS** control; independent client DNS failover #212 is PAUSED. Shared ASUS Unbound is a single failure domain.
- Pi-hole-aware full blank-device DR #129 is **not proven**. Existing-router restart, separate optional BusyBox persistence and isolated ARMv7 package rebuild have separate evidence limits.
- RouterCloud UID0/origin risks and both ext4 SSD root mount modes remain open security work (#235). Native SSD Trust v1 synthetic `RC=2/HOLD` never authorizes permissions changes. The experimental post-mount PR #245 remains unmerged/uninstalled.
- Email/Telegram synthetic alerts, current 15 rules, and actual per-rule production notification coverage remain distinct evidence classes. RouterCloud resumable large-file transfer #254 is backlog research only.

**Non-actions:** no JFFS, mountpoint, filesystem permission, DNS, Dufs, firmware, Tailscale, secret, code or installed artifact changed by this documentation review. Do not present GitHub CI as a new router acceptance.

## Unverified outside this review

- HTTP health of every external hyperlink and actual rendered behavior of every GitHub Markdown anchor.
- Full human interpretation of every paragraph across the 240 Markdown documents and replay of all 99 evidence-file test environments.
- Production ASUS Linux 4.1.52 compatibility, continuous SSD-mount identity, power-loss rollback, or non-root RouterCloud service start.

**Decision:** publish the narrowly scoped documentary corrections and keep `DEPLOYMENT_GATE=HOLD`.
