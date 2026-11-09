# Documentation reconciliation — 2026-11-09

> **Documentation-only review** from GitHub `main` and sanitized operator results. No scripts, production router or Fedora services were run by this audit.

## Scope and coverage

- Repository tree inventoried: **701 entries**, including **320 Markdown files** across top-level docs, `docs/`, `evidence/`, `monitoring/`, experiments and historical worklogs.
- Reviewed source-of-truth policy, main-branch protection, project status/readme/changelog, documentation indexes/entry points, monitoring unit/configuration and guide, Fedora maintenance runbook, worklog/evidence registers and the prior VictoriaMetrics upgrade evidence.
- **Limitation:** this is a repository-wide structural inventory plus focused *current-facing documentation* reconciliation, **not** a line-by-line semantic review of all 320 Markdown documents, full internal-heading/external-link crawl, independent live deployment audit, or verification of every historical issue/PR status. Older records keep their as-of dates.

## Findings and resolutions

| Finding | Resolution | What remains unverified |
| --- | --- | --- |
| VM production version newer than 2026-10-27 docs | Added Nov 9 worklog/evidence and current monitoring/status links | Long soak, off-host recovery |
| Seven `up=1` Blackbox-related scrape results | Clarified `up` versus `probe_success` | Actual ICMP/DNS/HTTPS probe success |
| VM snapshot, old binary and 32M data copy | Recorded backup and same-host-only restoration boundary | Isolated rollback/DR test |
| Deployed systemd differs from repository template | Documented effective stop timeout and hardening without editing template | Full runtime/source parity |
| Fedora update happened without 615/620 NVIDIA upgrade | Added dated Fedora checkpoint, retained `libheif` issue and Fedora 45 HOLD | Future compatibility |
| Loki `/ready` 200 after transient delay | Documented bounded PASS without claiming earlier 503 fixed | Persistent readiness root cause |
| PR #369 described as Draft in current-facing docs | Reconciled with actual 2026-11-05 merge | Other historical PRs remain dated snapshots |
| Entry-point navigation absent for Nov 9 | Added cross-links from project status, worklog/evidence indexes, PL route and monitoring operations | Full external URL audit |

No changes to source-controlled production configurations, `monitoring/systemd`, firewall, router, CI pipelines or automation schedules are authorized or included. Publication and deployment remain distinct. A later full link/anchor audit can run separately without rewriting older evidence.
