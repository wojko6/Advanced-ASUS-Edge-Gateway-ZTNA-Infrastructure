# Documentation map — current entry points and evidence boundaries

**Status:** CURRENT navigation only · **Reviewed:** 2026-11-04 (narrow corrections for published public worklogs and exact PR #364/#366 status; remaining PR table retains its stated 2026-11-03 snapshot and was **not** re-audited). **Not** a live deployment/security audit. This is a **finding aid, not a new authoritative source**. The [documentation model](documentation-model.md) defines evidence precedence; [PROJECT-STATUS](../PROJECT-STATUS.md) describes the accepted present state.

## Choose the right document

| Question | Start with | Then verify against |
| --- | --- | --- |
| What actually runs on the ASUS gateway? | [PROJECT-STATUS](../PROJECT-STATUS.md) | Applicable [dated evidence](../evidence/) and [operations](operations.md) |
| How is the network designed? | [Network-design index](network-design.md) | [Architecture](architecture.md), [security](security.md) and [firewall policy](firewall-policy.md) |
| How can the system be managed or recovered? | [Operations guide](operations.md) | [Recovery index](disaster-recovery-index.md), dated live acceptance and explicit rollback gates |
| What is tested, simulated or pending? | [Testing](testing.md) and [requirements](requirements.md) | [Evidence collection](evidence-collection.md), [project roadmap](roadmap.md), exact GitHub PR state |
| What happened on a particular date? | [Public worklog timeline](worklog/README.md) (retrospective Oct 30–31 summaries were merged by [#364](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/364); latest Nov 4 entry has its own [merged #366](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/366) and a newer documentation-only Draft) | Relevant dated [case study](CASE-STUDIES.md), audit and PR; do not promote historical status to current |
| Where are the Fedora monitoring/UI labs? | [Homelab Control Center experiment](../experiments/fedora/homelab-control-center-v0.1/README.md) | [HCC status](../PROJECT-STATUS.md) and the particular draft/merged PR; no assumed permanent deployment |
| How does the local supervised Qwen GUI differ from C.63? | [Fedora GUI boundary](design/local-qwen-supervised-gui-2026-11-03.md) | [C.63 lab README](../experiments/fedora/local-ai-agent-v0.21/c63/README.md) and [dated worklog](worklog/2026-11-03.md); scopes remain independent |
| Which material is written in Polish? | [Polish entry point](pl/START-HERE.md) and [Polish documentation index](pl/README.md) | [Language policy](language-policy.md) and canonical technical contract |
| What is historical or superseded? | [Documentation model](documentation-model.md) | Document's original date, lifecycle label and later accepted status; do not delete evidence to simplify navigation |

## How the three repositories relate

- **[Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure)** — current actively maintained public engineering source and sanitized evidence/status. Its `main` and merged PRs must be distinguished from operator-deployed state.
- **`work-log-private` (private)** — the operator's Polish daily engineering log. It can contain details not suitable for public publication; it is **not** automatically mirrored to this repository. Public worklogs are curated excerpts, not translations.
- **`ASUS-Edge-Gateway-ZTNA` (private)** — separately curated portfolio/migration repository with its own historical baseline and gate. Its dated notes are **not** evidence that it tracks every later change from the active public engineering repo.

**Full open-PR triage:** [22-PR inventory and safe review order (2026-11-03)](audits/2026-11-03-open-pr-backlog-reconciliation.md). This dated register separates CI, merge conflicts, branch ancestry, human approval and deployment safety; it does **not** change any PR state.

## PR status reconciliation — historical snapshot checked 2026-11-03

These are **source publication states**, not deployment or feature acceptance.

| Workstream | GitHub state at review | What it does **not** prove |
| --- | --- | --- |
| HCC V0.4 [#318](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/318), event model [#320](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/320), seven-series join [#322](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/322), fixed archive [#323](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/323) | **MERGED** | No permanent HCC service, unattended diagnosis or router DNS client continuity |
| HCC raw one-series preflight [#321](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/321) | **OPEN / DRAFT** | Do not infer this specific PR was merged just because related PRs were |
| HCC V0.14 lab [#338](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/338) and Oct 29 docs [#340](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/340) | **OPEN / DRAFT** | No independent production HCC rollout |
| C.63 agent [#347](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/347), [#348](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/348) | **MERGED** | No autonomous model action authority (`MODEL_ACTION_AUTHORITY=NONE`) or deployment |
| Earlier C.57/C.60/C.61/C.62 chain [#343–#346](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/343) | **OPEN / DRAFT** (separate ancestry) | No silent integration or independent security sign-off |
| DNS Guard Cron `dig` [#350](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/350), [#351](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/351) | **MERGED**; operator-reported limited live patch separately documented | No complete WAN/failover or Issue #287 resolution |
| Issue #287 J25–J27 docs [#361](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/361), Nov 2 addendum [#362](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/362) | **OPEN / DRAFT** | No candidate deployment; no new acceptance of unknown tests |
| Nov 3 Qwen GUI docs [#364](https://github.com/wojko6/Advanced-ASUS-Edge-Gateway-ZTNA-Infrastructure/pull/364) | **MERGED 2026-11-03** (updated review 04.11; was Draft at an earlier checkpoint) | The documentation merge did not publish GUI source or authorize autonomous agent rollout |

**November 4 reconciliation:** public `docs/worklog/2026-10-30.md` and `2026-10-31.md` are now on `main` (merged #364); the `2026-11-04.md` static-check worklog was published in #366. Subsequent Nov 4 USB/ACPI/TSC and Fedora 45 updates are proposed in a **separate Draft**, not yet published on `main`. The table above is otherwise a November 3 snapshot, not current verification of every PR.

**Interpretation:** a historical worklog may legitimately say “Draft” as of its own date. For the current source state, consult the actual PR and this **dated** snapshot; do not rewrite historical findings to pretend they occurred later. Source-merged ≠ on-router installed ≠ operator acceptance ≠ security audited.

## Lightweight maintenance checklist

1. Update [PROJECT-STATUS](../PROJECT-STATUS.md) with dated scope and verified independent live acceptance only.
2. Add a single dated [worklog](worklog/README.md) with evidence limits; preserve failed attempts and `HOLD` decisions.
3. For each current-facing document, verify linked PRs and label archived prose by **its historical as-of date**.
4. Validate internal links and check public redaction before a **docs-only Draft PR**; never auto-merge for documentation hygiene alone.
5. Revisit this index when navigation changes, rather than duplicating entire status narratives in READMEs.

[Documentation review (2026-11-03)](audits/2026-11-03-documentation-review.md)
