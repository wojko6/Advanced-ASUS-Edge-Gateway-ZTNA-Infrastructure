# Repository documentation review — Fedora Homelab Update (2026-10-18)

> **Scope:** documentation-only review of the latest public `main` documentation baseline on 2026-10-18 (head `da0eb16e1c52d4beb3323a7a78e32861b1844dbd`) together with operator-supplied Fedora terminal results dated 2026-10-18. **Not** a new full-archive line-by-line audit, live ASUS acceptance, PR #245 review, or automatic-update deployment.

## Material reviewed

- Repository directory inventory on `main` (Git tree, not truncated); current project `README.md`, `PROJECT-STATUS.md`, `CHANGELOG.md`, `docs/operations.md`, `docs/roadmap.md`, `docs/documentation-model.md`, `docs/worklog/README.md`, latest worklog, monitoring README, Grafana #236 historical runbook, service architecture / requirements / testing references and the [2026-10-16 245-document register](2026-10-16-complete-archive-document-review.md).
- Direct comparison of the October 18 Grafana pilot, service gates and LAB v0.1–v0.9 with the current repository navigation and operations documentation.
- The previous [16 October archive audit](2026-10-16-complete-archive-document-review.md) was a separate, snapshot-time review of 245 documents. It is **not** being re-certified here; its historical PDF and older RouterCloud findings stay attributed to that earlier audit.

## Gaps found and corrections

| Finding | Correction / status |
| --- | --- |
| No dated Oct 18 worklog for the off-router updater work | Add [worklog](../worklog/2026-10-18.md) and index entry |
| No canonical documentation for Update Watch and Grafana manual pilot | Add [Fedora controlled-update operations page](../operations/fedora-homelab-automatic-updates.md) |
| Grafana historical #236 source references 13.2.3 without an explicit Oct 18 pointer | Add a clearly dated postscript, preserving the original historical migration evidence |
| No dedicated public, sanitized summary of today’s terminal gates | Add [operator validation evidence](../../evidence/2026-10-18/fedora-update-operator-validation.md) |
| Docs/status/monitoring navigation did not identify which unattended gates remain HOLD | Link from project status, operations, README and monitoring |
| Lock audit v0.6 initially missed systemd `%h` and v0.8/v0.9 found static `flock` similarity only | Explain fixed resolver, lifecycle limits, and prohibition on production co-operation claims |
| Potential confusion between existing `homelab-update-check.timer` and absent unattended installer | Distinguish `CHECK_ONLY` production component from `APPLY_IMPLEMENTED=NO` labs and operator-approved Grafana pilot |

## Safety and review limitations

- Only Markdown source/navigation and dated operator-evidence summaries are changed. No systemd unit, backup wrapper, live configuration, firmware, JFFS script, RouterCloud code, SSD permission or production service is altered by this PR.
- No test of all 15 alert deliveries, real Restic restore, Caddy HTTP transaction, actual ASUS sender identity, actual lock inode, or unattended deployment is claimed.
- Existing #235 / PR #245 remain separated, OPEN / DRAFT / HOLD. Nothing here is authorization to migrate to OPNsense or to change the ASUS router.
- The broad October 16 audit covered more documents than this targeted October 18 reconciliation. External URL reachability, complete semantic correctness of historical documents and full PDF render inspection have **not** been repeated.
- Any link/Markdown CI executed **after** opening this documentation PR should be reported by the actual CI result; do not infer a green build from a docs-only intent.

**Outcome:** documentation reconciliation for the newly observed Fedora Update workflow, with explicit HOLD status for unattended installation.

## Cross-PR reconciliation — Draft #264 and Draft #265 (2026-10-18)

The repository had **two distinct same-day documentation PRs**, both created against the same `main` baseline:

- [Draft PR #264](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/264) records **approved read-only ASUS DNS Guard root-Cron ownership investigations**, including a live SHA-256 comparison, and Fedora-only synthetic owner-repair V0.1–V0.3. The production trust gate remains HOLD.
- [Draft PR #265](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/265) records the **real manual Fedora Grafana 13.2.4 upgrade**, the check-only watcher, and independent Fedora updater/lock labs. Unattended installation remains HOLD.

**Resolution on the PR #265 branch (not on `main`):** retained PR #264 as a distinct Draft, added its commit as a second parent of a documentation-only merge commit, and reconciled four overlapping Markdown files in a single tree. The dated worklog now contains **both** independently scoped histories, the index has **one** October 18 link, `PROJECT-STATUS.md` carries **both** October 18 checkpoints, and `docs/operations.md` preserves both safety/maintenance sections. Git history is not force-rewritten. No PR was merged into `main` as part of this reconciliation.

**Merge order:** review/merge #264 first, then review #265 against the updated `main`; check the resulting diff and re-run documentation CI. If #264 is squash-merged, explicitly verify #265's effective diff after the new base rather than assume GitHub hides the reconciled work automatically. PR #245 remains an unrelated, uninstalled Draft.

**Provenance correction:** the global statement “ASUS not contacted on October 18” would be wrong, because #264 records separately approved **read-only** ASUS tests. “ASUS not contacted” is restricted to the **Fedora Homelab Update laboratory**. No claim of ASUS *mutation* or new router-wide acceptance is made.

**Safety:** documentation reconciliation only. No production Linux service, ASUS script, router permissions, root Cron, RouterCloud timer, Dufs code, JFFS mount/hook or backup lock was changed.

## Post-approval Git history checkpoint — PR #264 merged

After the two PRs were reviewed and the operator explicitly approved the documented merge sequence:

1. [PR #264](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/264) was marked ready and **merged into `main`**, preserving the reviewed DNS Guard owner-trust record. Merge commit: `b3dfc19ba170962ac5243f3052eff3b0f707c563`. That commit's tree matched the reviewed #264 head tree byte-for-byte.
2. GitHub automatically changed [PR #265](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/265)'s base from the #264 branch to `main`. The #265 branch carried the reconciled combined worklog and all remaining Fedora documentation.
3. To explicitly synchronize Git history without altering the approved #265 content, a new ancestry-only merge commit `02fa6cf8d3ccd814bcf00e3e247df280b2ce3c42` was created with the #265 head and new `main` as its two parents, retaining the existing #265 tree `d30102986367e15fedd7921725c1045a80901e1e`.
4. The current #265 PR must still pass its **fresh post-synchronization GitHub validation** and a checked, documentation-only diff before it can be approved for merging into `main`. This paragraph records the chronology, **not** a claim that #265 has already merged.

The previously documented Draft/merge-order sections above are **historical decisions at their respective checkpoints**. The public worklog continues to distinguish approved ASUS read-only checks from Fedora updater laboratory non-contact, and maintains all unrelated production HOLD gates.
