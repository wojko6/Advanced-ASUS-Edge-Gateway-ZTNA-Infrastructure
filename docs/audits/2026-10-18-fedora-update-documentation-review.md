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
