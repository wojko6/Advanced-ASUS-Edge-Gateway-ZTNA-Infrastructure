# ASUS Edge — cross-repository documentation reconciliation (2026-11-15)

> **Scope:** main-branch source and GitHub PR metadata for selected current-facing
> ASUS Edge documents, compared with Fedora workstation evidence. No router
> access, service command, package change, fresh uptime measurement, live
> security verification or restore drill.
>
> **Evidence rule:** publication in `main` is separate from an on-router
> deployment, a Fedora runtime test, and operator acceptance. Historical
> worklogs remain intact, with their original as-of date.

## Reviewed status boundaries

| Area | Correct interpretation as of repository review | Source |
| --- | --- | --- |
| Physical Fedora host | The Nov 9 **Fedora 44/NVIDIA 610.57.04** monitoring snapshot is historical. The physical host was reported upgraded to **Fedora 45 / KDE Plasma 6.8.2 / NVIDIA 620.70.06** on **2026-11-10**; no new Nov 15 live check is claimed. | [Fedora PROJECT-STATUS](https://github.com/wojko6/fedora-workstation-setup/blob/main/PROJECT-STATUS.md), [Nov 10 worklog](https://github.com/wojko6/fedora-workstation-setup/blob/main/docs/WORKLOG-2026-11-10.md) |
| Fedora monitoring evidence | VictoriaMetrics v1.156.0 was confirmed in the bounded **2026-11-09** operator record, with seven `up=1` scrapes; this is not Blackbox, alert delivery, or off-host recovery acceptance. | [Nov 9 worklog](../worklog/2026-11-09.md), [VM evidence](../../evidence/2026-11-09/fedora-victoriametrics-v1.156.0-live-upgrade.md) |
| ASUS gateway production | The latest **documented operator-reported** ASUS production change found in this review remains the scoped DNS Guard `dig` repair of **2026-11-02**. Later GitHub documentation merges are **not** router deployments. | [Nov 2 worklog](../worklog/2026-11-02.md), [PROJECT-STATUS](../../PROJECT-STATUS.md) |
| Supervised Qwen GUI | Nov 5 v0.12.29 checkpoint is historical; Nov 6 v0.12.30–v0.12.34 was subsequently documented and published by [merged PR #370](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/370). Loki intermittent 503 root cause is still **unproven**. | [Nov 5](../worklog/2026-11-05.md), [Nov 6](../worklog/2026-11-06.md) |
| Security/recovery backlog | [Audit follow-ups #372](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/372) published **3 High / 8 Medium / 1 Low** investigation priorities on 2026-11-15. These are **unremediated hypotheses/gates**, not verified exploits or approved ASUS fixes. | [Nov 13 audit register](2026-11-13-codex-engineering-followup-register.md), [security Issue #235](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/235), [recovery Issue #129](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/issues/129) |
| Older HCC source drafts | Historical Oct 28 descriptions of #318/#320/#322/#323 as Draft are not current PR state: those four PRs are **merged** at review time; [#321](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/321) remains open Draft. | GitHub PR metadata; none establishes permanent HCC deployment |
| Pending ASUS docs | [PR #365](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/365) remains an **open Draft** and retains a dated Nov 3 queue snapshot, not a current queue count. | GitHub PR metadata |

## Reconciliation actions

1. Add a **Nov 15 source-review note** before the historical Nov 9 Fedora
   checkpoint in `PROJECT-STATUS.md`, preserving the original monitor and
   gateway timelines without inventing live evidence.
2. Update `docs/DOCUMENTATION-MAP.md` with the Nov 6 GUI worklog, the Nov 13
   security register, and the corrected current PR-source boundary.
3. Add a dated current-status summary to `docs/roadmap.md`; correct the
   undated statement that merged PR #369 is still Draft. Explicitly label
   October 28 HCC PR status statements as **historical** rather than deleting
   that record.
4. Preserve the `DEPLOYMENT_GATE=HOLD`, `MODEL_ACTION_AUTHORITY=NONE`,
   recovery and privileged owner/trust approval gates.

## Review/validation limits

- Reviewed current-facing documents, recent PR states and key source references.
  This is **not** another exhaustive full-repository Markdown or external-link
  crawl; the separate Nov 9 inventory keeps its own dated scope.
- No healthcheck, router access, DNS failover test, restores, installer writes
  or local GUI launches were made by this review.
- Do not publish host identifiers, secret/config values, private worklogs,
  browser/session data, network captures or on-device file paths.
- If a new live ASUS update or a later PR merge changes the evidence, revise
  the current-facing summary with a **new date**, leaving old observations
  attributable to their original records.

**Outcome:** `DOCS_RECONCILED=SOURCE_ONLY` · `LIVE_ASUS_VALIDATION=NOT_RUN` ·
`SOURCE_PUBLICATION_NOT_DEPLOYMENT=YES` · `DEPLOYMENT_GATE=HOLD` ·
`HUMAN_REVIEW_BEFORE_MERGE=YES`.
