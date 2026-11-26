# Public repository current-navigation and status closeout — 2026-10-24

> **Scope:** documentation-only reconciliation on a dedicated review branch based on the October 24 merged repository snapshot. **No ASUS router, Fedora host, production configuration, package, installer, cron, firewall, backup, private worklog or runtime change was made.** This audit does not merge or replace existing security/research Draft PRs.

## Source and bounded checks

- Read GitHub's non-truncated recursive `main` tree: **480 tracked files, 272 Markdown files** at this checkpoint.
- Compared dated worklog filenames against `docs/worklog/README.md`: **38/38 dated entries indexed**, no duplicate or missing daily file target. The October 23 [earlier full-documentation review](2026-10-23-full-documentation-consistency-review.md) remains a dated historical audit; its then-current file counts and Unbound 1.26.1 runtime were correct for October 23, not for October 24.
- Cross-checked the October 24 [Unbound R2 production report](../operations/unbound-1.26.2-production-deployment-2026-10-24.md), [incident worklog](../worklog/2026-10-24.md), [current project status](../../PROJECT-STATUS.md) and related case-study navigation.
- Verified [PR #297](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/297) is **MERGED**, and both [#298](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/298) and [#299](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/299) remain **OPEN**. At this checkpoint four separate PRs (#202, #226, #245 and #270) remained **OPEN / DRAFT** and were not modified by this review.
- Inspected the current README, case-study index, Polish index, dated worklog header and chronology, worklog navigation, and documentation precedence model for the inconsistencies corrected here. This is **targeted document review**, not a re-read of all 272 Markdown bodies.

## Corrections

| Document | Problem | Action |
| --- | --- | --- |
| `README.md` | October 24 R2 passage stopped at pre-reboot acceptance; later actual reboot and file-mode exception were not surfaced in the entry point. | Add the bounded one-reboot functional PASS, `root.key 0666` observation, and separate uninstalled #298/#299 gates. |
| `docs/CASE-STUDIES.md` | Unbound item sat after the reading guide and described already-merged PR #297 as under review; it incorrectly implied no router reboot persistence had been checked. | Make it numbered case 17 before the reading guide, mark PR as merged, distinguish one observed functional reboot from untested power-loss cold boot/continuous startup. |
| `docs/pl/README.md` | Current section still claimed 18 October as the latest checkpoint and sent readers to Oct 17–18 daily records. | Link Oct 24 production/incident reports and current limits; retain the older dated findings explicitly as history. |
| `docs/worklog/README.md` | Oct 24 index shorthand conflated untested controlled failover/cold boot with later observed unplanned failover and actual reboot. | Clarify evidence boundary and #298/#299; keep all 38 dated entries and their original chronology. |
| `docs/worklog/2026-10-24.md` | Opening summary claimed DNS Guard live failover untested without distinguishing later real, unplanned fail-open/failback evidence. | Clarify observed spontaneous behavior, bounded reboot PASS and separate HOLD, without rewriting incident steps. |
| `docs/documentation-model.md` | Audit/navigation pointer predated latest status and index update. | Link this dated reconciliation; preserve existing source-of-truth precedence. |

## Accepted current-state boundary

- **ASUS production:** Unbound **1.26.2-1 (five packages)** following the successful separately authorized R2 attempt. Direct UDP/TCP DNSSEC valid AD/bogus SERVFAIL and router/Pi-hole client paths PASS in their recorded scope; one later actual reboot passed bounded functional checks.
- **Historical first attempt:** its failed 1.26.2 start, package-only rollback failure and targeted 1.26.1 recovery remain in chronological records. The October 23 Fedora-only HOLD is historical, not a reversal of successful October 24 R2.
- **Separate exceptions:** post-reboot RFC 5011 `root.key` was `0666` in a service-owned `0700` directory; actual production daemon umask was not measured. #298/#299 remain OPEN/HOLD. Fedora V1–V6 and QEMU findings are not production rollout authority.
- **DNS Guard:** unplanned system-resolver fail-open/failback **OBSERVED**; controlled fault injection **NOT TESTED**, uninterrupted LAN/Tailscale client DNS and independent alert-transport DNS **NOT PROVEN**. Do not equate functional single reboot with cold power-loss resilience.
- **Security and plans:** #235/#278/#287 and the Dufs/RouterCloud worktrees remain independent; neither Flint 4 nor independent client DNS failover #212 is a deployed architecture.

## Validation not claimed

No exhaustive fresh all-Markdown semantic audit, external URL reachability check, GitHub-generated anchor validation, live-router operation, full power-loss reboot, independent client failover, or private-worklog translation was performed. A green repository CI check is a code/static gate, **not** proof of production acceptance. The documentation branch should be reviewed and its head validated before any merge.
