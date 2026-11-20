# Codex engineering audit — actionable follow-up register (2026-11-13)

> **Status:** REVIEW BACKLOG / NO FIX DEPLOYED / OPERATOR APPROVAL REQUIRED
>
> **Source snapshot:** Codex read-only engineering review of the repository's `main` at commit `442f5bb4e1c17c07cad47b9ebcd6365e8e41d72a` (reviewed 2026-11-13). Severity labels reproduce the **Codex review priorities**, not an independently demonstrated exploitability rating.
>
> **Evidence boundaries:** Repository code inspection, limited synthetic/offline tests, publicly tracked historical operator observations. **No live ASUS router action, current root ownership measurement, actual credential disclosure, internet exposure, complete restore or power-loss simulation was performed.** An older production observation must not be silently promoted to a verified present-day state.
>
> **Tracking policy:** One dated, sanitized register. Reuse [security Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) and [recovery Issue #129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) where applicable; no new GitHub Issue and no merge/deployment approval. Existing Draft PRs [#245](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/245) and [#270](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/270) are distinct historical/laboratory work, **not** accepted remediations for all of these findings.

## Executive triage

**12 follow-ups: 3 High, 8 Medium, 1 Low (the last groups several documentation drifts).** All are **OPEN FOR REVIEW** in this register. Static/synthetic PASS does not prove a hardened production deployment.

| ID | Codex priority | Finding / impact hypothesis | Source anchor | Existing coordination |
| --- | --- | --- | --- | --- |
| H1 | High | Privileged installation/publish boundary: copied executable is chmod'd but its final owner/group and trusted writable ancestors are not explicitly guaranteed; a root-run DNS Guard Cron target makes provenance critical | [installer](../../scripts/install.sh), [services hook](../../router/scripts/services-start), [healthcheck](../../scripts/healthcheck.sh) | [#235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235) |
| H2 | High | Backup-created restrictive directory modes may be applied by recursive restore to pre-existing live parent directories, potentially preventing service traversal | [backup](../../scripts/backup.sh), [restore](../../scripts/restore.sh), [clean-room test](../../tests/test-cleanroom-restore.sh) | [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) |
| H3 | High | Restore rollback snapshot is stored in the same temporary tree removed by the EXIT/HUP/INT/TERM trap; interruption or rollback failure may destroy recovery material | [restore](../../scripts/restore.sh) | [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) |
| M1 | Medium | Services-start lock creation, owner record and stale-lock removal leave a concurrency race | [services hook](../../router/scripts/services-start) | #235 / this register |
| M2 | Medium | Pi-hole API collector uses a session header with a default redirect-following HTTP client; response bodies are unbounded | [collector](../../monitoring/pihole-dns-collector.py) | This register; security review |
| M3 | Medium | RouterCloud login return-location sanitization may accept slash-backslash input that the browser resolves as another origin (open-redirect risk) | [login](../../router/routercloud/webui/metro/login.js) | This register; RouterCloud security |
| M4 | Medium | RouterCloud backup network-wait loop contains a shell arithmetic typo, affecting retry logic when reachability is delayed | [backup](../../scripts/routercloud-backup.sh) | This register; Fedora backup |
| M5 | Medium | Firewall script can log missing `ip6tables` and return success without proving that IPv6 is disabled or equivalent rules are enforced | [firewall](../../router/scripts/firewall-start) | This register; firewall validation |
| M6 | Medium | Required aggregate CI job does not cover every separate C.63/HCC and RouterCloud behavioral test; some checks are source-string rather than behavior assertions | [validation workflow](../../.github/workflows/shellcheck.yml) | This register; CI policy |
| M7 | Medium | Five September evidence `SHA256SUMS` manifests have stale/mismatched README entries; other entries and two C.63 manifests were reported matching | [evidence index](../../evidence/README.md) | This register; evidence provenance |
| M8 | Medium | Offline reproducibility depends on mutable/unpinned packages, external artifacts and private state; a clean-device recovery has not been demonstrated | [recovery index](../disaster-recovery-index.md) | [#129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) |
| L1 | Low | Historical and current documentation drift (Tailscale version prose, C.63 README/Draft labels, job-count descriptions) | [status](../../PROJECT-STATUS.md), [documentation map](../DOCUMENTATION-MAP.md) | This register; docs-only |

## Required verification and acceptance gates

### H1 — privileged script origin and ownership

- Compare final installed executable identity (UID/GID, mode, path) and every writable ancestor against the intended root-execution policy in a **disposable filesystem fixture** first.
- Design a safe **atomic root-owned publication**, exact owner/ancestor trust preflight, refusal and rollback; do not assume `chmod` alone establishes ownership.
- Reconcile the **historical** non-root-owned owner-writable script evidence in #235 with a separately authorized, read-only current ASUS inventory, if later approved.
- Add negative tests for untrusted owner, writable ancestor and symlink/rename behavior, compatible with Asuswrt-Merlin/GNUton/BusyBox/Entware.
- **No deployment, Cron replacement, JFFS permission repair or privilege change approved.**

### H2 — backup-to-restore metadata safety

- Produce a **real `backup.sh` → `restore.sh` round trip** in a disposable alternate-root fixture, not only a synthetic hand-crafted archive.
- Record before/after owner/mode/traversal of pre-existing parent directories, including `opt` and `jffs`-equivalent parents; assert no unintended metadata replacement and that service users can traverse required paths.
- Test malformed archives and interrupted copy without touching live `/opt` or `/jffs`.

### H3 — durable rollback on failure and signals

- Keep pre-restore rollback material **outside** ephemeral cleanup scope until success is committed or operator-approved recovery is complete.
- Fault-inject extraction, copy, restore and signal interruptions; verify recovery material survives failures and can be restored independently.
- Do not claim a recovery guarantee until alternate-root tests and failure modes are exercised. Current full Pi-hole-aware DR remains **OPEN** under #129.

### Medium-priority follow-up checklists

- **M1 lock race:** design lock ownership/atomic acquisition and owner-verified release, then test concurrent invocation, stale-lock cases and crash recovery in an isolated fixture.
- **M2 collector HTTP:** prevent credential/session-header propagation across redirects, bound response size, require trusted same-origin behavior and add mocked redirect/oversize negative tests. The original offline redirect reproduction is **not** proof of an on-router credential leak.
- **M3 login redirect:** canonicalize/validate destination URLs against same-origin constraints; test slash, backslash, encoded forms, protocol-relative paths and benign local return paths without weakening login flow.
- **M4 network retry:** correct the arithmetic expansion in a narrowly scoped patch and test initial success, unreachable router, later recovery and bounded timeout using mocked commands; no real backup run during the unit test.
- **M5 IPv6:** require proof that IPv6 is disabled or enforce validated IPv6 policy, with an explicit fail-safe status when rules cannot be applied; check on supported firmware without changing production firewall.
- **M6 CI:** enumerate required workflow jobs versus security-critical C.63/HCC/RouterCloud suites; gate the selected behavioral tests with pinned tools/versions and add negative cases, distinguishing GitHub merge requirements from production acceptance.
- **M7 evidence hashes:** inspect the five dated manifests and historical commits; **do not silently rewrite provenance**. Document whether the README or manifest is stale and supply additive correction/evidence if warranted.
- **M8 reproducibility:** inventory exact artifact hashes, private/offline dependencies and toolchain bootstrap requirements; retain the clean-room/blank-device HOLD until a fully authorized restore drill.

### L1 — maintenance documentation

- Replace undated `now/current` statements only after checking their operational source of truth; retain old versions as historical evidence.
- Refresh C.63 README, merged-versus-Draft labels and GitHub validation job descriptions **without implying an application rollout**.

## Suggested sequencing

1. **Phase 1 — the three High risks:** H1 privileged publication and trust, H2 live-parent metadata preservation, H3 durable rollback. Prepare one **reviewable isolated Draft PR** with separate commits/fixtures only if implementation is explicitly authorized; coordinate with #235/#129 and avoid conflicts with existing Draft PR #245. Do not deploy.
2. **Phase 2 — bounded Medium fixes:** M4 is a small independently testable arithmetic correction; then M2/M3 security boundaries, M1/M5 runtime guards, M6 CI behavioral coverage.
3. **Phase 3 — evidence and recovery:** M7 provenance notes, M8 reproducible blank-device DR, then L1 dated documentation reconciliation. These can run in parallel only when they do not alter production state.

## Reproduction / evidence scope from Codex (not rerun here)

- Reported repository checks: **89** shell syntax passes; **68** Python and **26** JavaScript parse passes; **5** JSON parse passes; C supervisor syntax pass; **658** C.63 offline self-tests; **55** HCC Node tests; one mocked RouterCloud AJAX check.
- **Two** reviewed manifests passed and **five** dated September README entries were inconsistent. Read-only checked main workflow success was reported on 2026-11-09.
- These checks do **not** exercise the current ASUS firmware runtime, alternative-root round-trip, root ownership trust, WAN/client DNS continuity, IPv6 enforcement or deployment safety.

**Exit gate:** `AUDIT_REGISTER=RECORDED`; `HIGH_FIXES=NOT_IMPLEMENTED`; `PRODUCTION_ROUTER=UNCHANGED`; `DEPLOYMENT_GATE=HOLD`. Every implementation phase requires a fresh code review, isolated tests, preservation of current operator evidence and explicit approval.
