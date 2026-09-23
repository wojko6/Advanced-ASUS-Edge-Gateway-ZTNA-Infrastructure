# Documentation model and source of truth

**Status:** CURRENT

**Last reviewed:** 2026-09-23

**Applies to:** `main`

This project deliberately separates current state, implementation, live evidence, plans and historical engineering records. When documents disagree, use the precedence below instead of merging claims from different evidence classes.

## Source-of-truth precedence

1. **`PROJECT-STATUS.md`** — current project phase, accepted baseline, open/closed findings and explicit deployment boundaries.
2. **Dated `evidence/` artifacts** — proof for specific observed claims under the documented date, device, method and limitations. Evidence proves only the claim it records; it does not automatically mean the same code/configuration is still deployed.
3. **Current operational documentation** — `docs/operations.md`, `docs/deployment-pl.md`, `docs/requirements.md`, security/firewall/testing documentation and current architecture documentation. The requirements map records test ownership and limits; it must follow current status and dated observations when deployment state changes.
4. **`README.md`** — public summary derived from the current status and supporting evidence.
5. **`docs/roadmap.md`** — planned or candidate work; a roadmap item is not implemented or validated unless another current source says so.
6. **`docs/worklog/`** — dated public engineering chronology. A worklog explains what happened; it is not a substitute for evidence.
7. **Dated audit/remediation/planning documents** — historical decision records. Completed or superseded documents must say so explicitly at the top.
8. **`CHANGELOG.md`** — release/unreleased change history; it must be synchronized with the current status before a release is cut.

## Document lifecycle labels

Use one of these labels for documents whose lifecycle could be ambiguous:

- **CURRENT** — active instructions or status.
- **PLANNED / DRAFT** — proposed work that is not yet an accepted implementation.
- **COMPLETED / HISTORICAL** — retained for traceability after the described work has finished.
- **SUPERSEDED** — replaced by another named document or design.

A historical document may intentionally contain old dates or open findings when it is clearly marked as historical. Do not rewrite historical records merely to make them look current.

## Repository vs live-deployment boundary

Always distinguish:

- code/configuration present in the Git repository;
- behavior validated by CI/static/mock tests;
- behavior deployed on the reference router;
- behavior observed live on the router or a defined client.

A merged PR or green CI run does **not** prove that the same revision is installed on the reference ASUS. Promotion into the live validated baseline requires dated live evidence when the claim depends on deployment state.

## Architecture asset rule

`docs/images/Architecture.png` is the canonical current-deployment diagram. Active documentation should reference only that file unless a document explicitly presents a historical or future-state architecture.

Retired diagrams should be removed from the active public tree after their provenance/recovery reference is preserved. This avoids presenting two competing diagrams as equally current.
