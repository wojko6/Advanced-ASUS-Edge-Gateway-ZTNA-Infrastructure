# ASUS Edge Gateway — repository-wide documentation review (2026-10-13, evening)

**Status:** DOCUMENTATION RECONCILIATION / SOURCE-ONLY.  
**Branch:** `audit/grafana-236-traceability-20261013`, draft [PR #237](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/237).  
**Scope:** current-state guides, canonical architecture and operations, documentation navigation, dated case studies/worklogs and sanitized evidence. **No router, DNS, firewall, Tailscale, Grafana, database or notification action was performed by this documentation review.**

## Inventory and verification method

- A full recursive **GitHub tree** inventory of the working branch **before these documentation edits** returned **495 entries**, **226 Markdown documents**, `truncated=false`. Of the Markdown, **120** were under `docs/`, **96** under `evidence/`, **5** at the repository root, **2** under `monitoring/`, **3** under `router/`.
- Checked **all 226 baseline Markdown files** for locally linked Markdown targets/reference definitions and compared them to the repository tree. The scan evaluated **780 relative references**; after excluding two temporary false positives for the newly created `docs/worklog/2026-10-13.md` (not present in the earlier immutable tree snapshot), **zero missing local targets** were identified at that snapshot. The current-state cross-file links and the new worklog/audit links also require/received a fresh HEAD verification.
- This programmatic pass is a **path-existence** check of conventional Markdown links, **not** a renderer-aware validation of every fragment identifier, HTML anchor, Mermaid diagram, image payload, generated PDF, externally hosted link or document contents. Automated tests and runtime operations were **not executed**. Major canonical guides were additionally inspected for state/status contradictions; dated evidence was not reinterpreted as fresh live testing.
- The canonical [documentation model](../documentation-model.md) distinguishes current operational source-of-truth pages from point-in-time worklogs, dated evidence and historical architecture snapshots. Older files that accurately describe their date were **left historical**, rather than overwritten to imply a new acceptance result.

## Findings and corrections

| Topic | Finding | Disposition |
|---|---|---|
| Platform direction | TUF-AX5400 remains production; RT-BE88U migration **cancelled** on 2026-10-12; OPNsense/x86 only undated potential research | Canonical [platform decision](../architecture/platform-direction-2026-10-12.md), architecture index and roadmap already consistent; preserved historical RT-BE88U plans instead of silently revising prior evidence |
| Fedora Grafana status | Top-level status, roadmap, monitoring, changelog and evidence index reflected at most 2026-10-12 Grafana Firing/Resolved despite actual **2026-10-13 V4** accepted migration | Updated [README](../../README.md), [project status](../../PROJECT-STATUS.md), [changelog](../../CHANGELOG.md), [roadmap](../roadmap.md), [monitoring](../../monitoring/README.md), [evidence index](../../evidence/README.md) |
| Chat ID and provisioning security | Active Fedora Chat ID is now `$GRAFANA_TELEGRAM_CHAT_ID` through a private root-owned `0600` systemd EnvironmentFile, with five additive environment sources and Grafana 13.2.3 stable after one planned restart; the public template still declares only Email | Added explicit **safe source/live boundary** to [monitoring](../../monitoring/README.md), [operations](../operations.md), [testing](../testing.md), [requirements](../requirements.md); **do not replace host Email+Telegram config with the repository Email-only template or commit local private values** |
| Real notification acceptance | Operator observed Firing delivery on Gmail (screenshot) and Telegram; operator confirmed Resolved on both; temporary `E2E-TEST-2026-10-13` deleted; UI count returned to **15** | Recorded as one **bounded post-migration dual-channel E2E PASS**, not individual 15-rule, grouping/repeat/anti-flap or clean-room restore PASS. See [traceability](../../evidence/2026-10-13/grafana-rule-traceability-matrix.md) |
| Failed deployment history | Early Stage 2/V3 false negative/early readiness and rollback attempts preceded success | Historical failures, two V3 restarts, protected SQLite snapshots, eventual V4 3-sample stable readiness and recovery gates remain documented in the [detailed runbook](../grafana-236-telegram-chatid-deployment-runbook.md), rather than erased |
| Navigation and dated worklog | 2026-10-13 engineering session not previously represented in `docs/worklog/` | Created [2026-10-13 worklog](../worklog/2026-10-13.md) and updated the [worklog index](../worklog/README.md); added cross-references in [network design](../network-design.md) and [documentation testing](../testing.md) |
| ASUS DNS and hardware | No new router-wide checkpoint beyond the documented 2026-10-09 Pi-hole-aware existing-router reboot; #212 client DNS failover paused and off-router; #129 blank-device DR not proven | Current statements preserved; no asserted client failover, OPNsense installation, RT-BE88U purchase or full clean-device restore |
| Other dated records | Several older reports contain historical statements like `RT-BE88U TARGET`, `Grafana drift open` or pre-V4 contact parity | Historical reports not mass-rewritten. Their own supersession notes and current document links define which status is authoritative now |

## Accepted production facts versus remaining work

**Accepted in its stated scope:**

- The ASUS TUF-AX5400 remains the production router; the Fedora Grafana **V4** migration was a **host-only** accepted change. Router wide live state has a different earlier evidence date.
- A 15-rule Grafana production baseline survived the host change; the temporary post-migration test returned to **15 UI-visible rules** after cleanup, with no independent latest rule-paused API requery claimed.
- A single synthetic Grafana alert automatically delivered real Firing and Resolved notifications to existing **Gmail and Telegram**, and was removed. No router/router-DNS failure injection was needed.
- The full local Email+Telegram contact file, credentials and three root-protected SQLite backups remain private and are **not** source-controlled artifacts.

**Not accepted/remaining:**

- [Grafana #236](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/236): independent notification lifecycle for all permanent rules, grouping/repeat, anti-flap, and clean-room alert-contact/policy recovery; full safe configuration-as-code parity for the Email+Telegram contact is **not** established by migrating a single Chat ID field.
- [Pi-hole-aware DR #129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129): full blank-router/SSD recovery, not merely a validated existing-device restart.
- [Client DNS failover #212](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/212): **paused** pending suitable separate hardware and explicit operator authorization, with direct-sidecar bypass still not accepted in production.
- Separate security, hardening and RouterCloud branches/issues remain subject to their own merge, deployment and evidence status; no live deployment is inferred from a GitHub branch or source-only test.

## Evidence model and review limitations

1. **Historical versus current:** `docs/architecture/ASUS-Edge-Gateway-Architecture-2026-10-08.md` and earlier worklogs preserve dated truth; the later [2026-10-12 decision](../architecture/platform-direction-2026-10-12.md) and [current project status](../../PROJECT-STATUS.md) supersede any historical RT-BE88U target language. A prior [2026-10-13 audit snapshot](2026-10-13-repository-documentation-consistency.md) is also retained unchanged as its own earlier review.
2. **Verification:** the Markdown target scan checks only files that exist in the branch tree and conventional Markdown reference syntax. It does not validate every anchor, external URL, diagram or binary PDF visually, and cannot replace local `tests/test-static.sh` / CI. No test pass is claimed for unexecuted local tests.
3. **Privacy:** do not add actual Chat IDs, Telegram tokens, Email recipients, local DNS query/client histories, private database snapshots or router secrets to GitHub, Markdown logs, screenshots or diagnostics.
4. **Release/CORE boundary:** repository package `VERSION` and the proposed ASUS **CORE v1.0** operational milestone remain independent; this documentation-only update is not a new release or a completed universal production-hardening certification.

**Disposition:** Update current-state documentation and cross-links in the review branch, preserve old evidence, keep **#236** OPEN for remaining gates and request review/CI before any PR merge. No claim is made that the entire repository's code, all external links or all diagrams were exhaustively runtime tested.
